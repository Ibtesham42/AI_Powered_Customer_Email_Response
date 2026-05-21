from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.auth.hashing import hash_password, verify_password
from backend.auth.jwt_handler import create_access_token
from backend.database import get_db
from backend.models.company import Company
from backend.models.schemas import LoginRequest, RefreshTokenRequest, SignupRequest
from backend.models.user import User
from backend.services.auth_service import (
    get_active_refresh_token,
    issue_refresh_token,
    revoke_refresh_token,
)

router = APIRouter()


def _issue_tokens(db: Session, user: User, http_request: Request) -> dict:
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
        user_agent=http_request.headers.get("user-agent"),
        ip_address=http_request.client.host if http_request.client else None,
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/signup")
def signup(request: SignupRequest, db: Session = Depends(get_db)):
    # Email is globally unique across all Companies.
    if db.query(User).filter(User.email == request.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Every signup creates a NEW Company; the signer becomes its Owner.
    # (There is no join-by-name — that was a tenant-isolation hole.)
    company = Company(
        name=request.company_name,
        address_line=request.address,
        city=request.city,
        state=request.state,
        country=request.country,
        postal_code=request.postal_code,
    )
    db.add(company)
    db.commit()
    db.refresh(company)

    user = User(
        full_name=request.full_name,
        email=request.email,
        phone=request.phone,
        password_hash=hash_password(request.password),
        company_id=company.id,
        role="owner",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "message": "Account created successfully",
        "company_id": company.id,
        "user_id": user.id,
    }


@router.post("/login")
def login(request: LoginRequest, http_request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()

    # One generic message for both cases — no account enumeration.
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid email or password")

    return _issue_tokens(db, user, http_request)


@router.post("/refresh")
def refresh(
    request: RefreshTokenRequest,
    http_request: Request,
    db: Session = Depends(get_db),
):
    row = get_active_refresh_token(db, request.refresh_token)
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = db.query(User).filter(User.id == row.user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Rotate: revoke the presented token and issue a fresh pair.
    revoke_refresh_token(db, row)
    return _issue_tokens(db, user, http_request)


@router.post("/logout")
def logout(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    # Idempotent — always succeeds, whether or not the token was valid.
    row = get_active_refresh_token(db, request.refresh_token)
    if row is not None:
        revoke_refresh_token(db, row)
    return {"message": "Logged out"}
