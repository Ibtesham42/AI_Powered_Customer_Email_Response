from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.user import User
from backend.models.company import Company
from backend.auth.hashing import hash_password
from backend.models.schemas import SignupRequest
from backend.models.schemas import LoginRequest
from backend.auth.hashing import verify_password
from backend.auth.jwt_handler import create_access_token

router = APIRouter()


@router.post("/signup")
def signup(request: SignupRequest, db: Session = Depends(get_db)):

    # Check if user exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Check or create company
    company = db.query(Company).filter(Company.name == request.company_name).first()

    if not company:
        company = Company(name=request.company_name)
        db.add(company)
        db.commit()
        db.refresh(company)

    # Create user
    user = User(
        name=request.name,
        email=request.email,
        password_hash=hash_password(request.password),
        company_id=company.id
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {"message": "User created successfully "}



@router.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == request.email).first()

    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid password")

    token = create_access_token({
        "user_id": user.id,
        "company_id": user.company_id,
        "sub": user.email 
    })

    return {
        "access_token": token,
        "token_type": "bearer"
    }