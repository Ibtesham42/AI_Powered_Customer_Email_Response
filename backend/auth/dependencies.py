from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.auth.jwt_handler import verify_token
from backend.database import get_db
from backend.models.user import User

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> dict:
    """Decode the bearer token and return the authenticated User context."""
    payload = verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    email = payload.get("sub") or payload.get("email")
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": user.id,
        "email": user.email,
        "company_id": user.company_id,
        "role": user.role,
    }


def require_owner(user: dict = Depends(get_current_user)) -> dict:
    """Dependency that allows only Company Owners through."""
    if user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Owner role required")
    return user
