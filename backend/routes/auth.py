from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.auth.hashing import hash_password, verify_password
from backend.auth.jwt_handler import create_access_token
from backend.config import settings
from backend.database import get_db
from backend.logging_config import get_logger
from backend.models.company import Company
from backend.models.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    ResetPasswordRequest,
    SignupRequest,
)
from backend.models.user import User
from backend.rate_limit import limiter
from backend.services import audit_service, email_service, password_reset_service
from backend.services.auth_service import (
    get_active_refresh_token,
    issue_refresh_token,
    revoke_all_refresh_tokens,
    revoke_refresh_token,
)

router = APIRouter()
logger = get_logger(__name__)


def _issue_tokens(db: Session, user: User, request: Request) -> dict:
    """Build an access token and a stored refresh token for a user."""
    access_token = create_access_token(
        {
            "user_id": user.id,
            "company_id": user.company_id,
            "sub": user.email,
        }
    )
    refresh_token = issue_refresh_token(
        db,
        user.id,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/signup")
@limiter.limit("5/minute")
def signup(payload: SignupRequest, request: Request, db: Session = Depends(get_db)):
    # Email is globally unique across all Companies.
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Every signup creates a NEW Company; the signer becomes its Owner.
    # (There is no join-by-name — that was a tenant-isolation hole.)
    company = Company(
        name=payload.company_name,
        address_line=payload.address,
        city=payload.city,
        state=payload.state,
        country=payload.country,
        postal_code=payload.postal_code,
    )
    db.add(company)
    db.commit()
    db.refresh(company)

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        company_id=company.id,
        role="owner",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    audit_service.record(
        db,
        action="signup",
        request=request,
        company_id=company.id,
        user_id=user.id,
        entity_type="user",
        entity_id=user.id,
        metadata={"email": user.email, "company_name": company.name},
    )

    return {
        "message": "Account created successfully",
        "company_id": company.id,
        "user_id": user.id,
    }


@router.post("/login")
@limiter.limit("10/minute")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()

    # One generic message for both cases — no account enumeration.
    if not user or not verify_password(payload.password, user.password_hash):
        audit_service.record(
            db,
            action="login_failed",
            request=request,
            company_id=user.company_id if user else None,
            user_id=user.id if user else None,
            entity_type="user",
            entity_id=user.id if user else None,
            metadata={"email": payload.email},
        )
        raise HTTPException(status_code=400, detail="Invalid email or password")

    tokens = _issue_tokens(db, user, request)
    audit_service.record(
        db,
        action="login",
        request=request,
        company_id=user.company_id,
        user_id=user.id,
        entity_type="user",
        entity_id=user.id,
        metadata={"email": user.email},
    )
    return tokens


@router.post("/refresh")
def refresh(
    payload: RefreshTokenRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    row = get_active_refresh_token(db, payload.refresh_token)
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = db.query(User).filter(User.id == row.user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Rotate: revoke the presented token and issue a fresh pair.
    revoke_refresh_token(db, row)
    return _issue_tokens(db, user, request)


@router.post("/logout")
def logout(
    payload: RefreshTokenRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    # Idempotent — always succeeds, whether or not the token was valid.
    row = get_active_refresh_token(db, payload.refresh_token)
    if row is not None:
        revoke_refresh_token(db, row)
        # Audit only a real session ending; an invalid token is a no-op.
        user = db.query(User).filter(User.id == row.user_id).first()
        audit_service.record(
            db,
            action="logout",
            request=request,
            company_id=user.company_id if user else None,
            user_id=row.user_id,
            entity_type="user",
            entity_id=row.user_id,
        )
    return {"message": "Logged out"}


@router.post("/forgot-password")
@limiter.limit("5/minute")
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Send a password-reset link. Always returns 200 — a mismatched email
    must be indistinguishable from a match (no account enumeration)."""
    user = db.query(User).filter(User.email == payload.email).first()
    if user is not None:
        raw = password_reset_service.issue_reset_token(db, user.id)
        reset_url = f"{settings.APP_BASE_URL}/reset-password?token={raw}"
        try:
            email_service.send_password_reset_email(user.email, reset_url)
        except Exception:
            # Never leak a send failure to the caller — log it and still 200.
            logger.exception(
                "Failed to send password-reset email to %s", user.email
            )
        audit_service.record(
            db,
            action="password_reset_requested",
            request=request,
            company_id=user.company_id,
            user_id=user.id,
            entity_type="user",
            entity_id=user.id,
            metadata={"email": user.email},
        )
    return {
        "message": "If that email is registered, a reset link has been sent."
    }


@router.post("/reset-password")
@limiter.limit("10/minute")
def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Complete a password reset: set the new password, consume the token, and
    revoke every existing session."""
    row = password_reset_service.get_valid_reset_token(db, payload.token)
    user = (
        db.query(User).filter(User.id == row.user_id).first()
        if row is not None
        else None
    )
    if row is None or user is None:
        raise HTTPException(
            status_code=400, detail="Invalid or expired reset token"
        )

    user.password_hash = hash_password(payload.new_password)
    # consume_reset_token commits — persisting the new hash in the same session.
    password_reset_service.consume_reset_token(db, row)
    revoked = revoke_all_refresh_tokens(db, user.id)

    audit_service.record(
        db,
        action="password_reset_completed",
        request=request,
        company_id=user.company_id,
        user_id=user.id,
        entity_type="user",
        entity_id=user.id,
        metadata={"sessions_revoked": revoked},
    )
    logger.info("Password reset completed for user %s", user.id)
    return {"message": "Password updated. Please log in again."}
