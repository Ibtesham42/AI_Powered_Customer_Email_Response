from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.auth.hashing import hash_password, verify_password
from backend.auth.jwt_handler import create_access_token
from backend.database import get_db
from backend.models.company import Company
from backend.models.schemas import LoginRequest, SignupRequest
from backend.models.user import User

router = APIRouter()


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
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()

    # One generic message for both cases — no account enumeration.
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid email or password")

    token = create_access_token(
        {
            "user_id": user.id,
            "company_id": user.company_id,
            "sub": user.email,
        }
    )

    return {"access_token": token, "token_type": "bearer"}
