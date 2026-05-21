
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.auth.jwt_handler import verify_token
from backend.database import get_db
from backend.models.user import User

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials

    payload = verify_token(token)

    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    # ---------- GET EMAIL FROM TOKEN ----------
    email = payload.get("sub") or payload.get("email")

    if not email:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    # ---------- FETCH USER FROM DB ----------
    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # ---------- RETURN FULL USER CONTEXT ----------
    return {
        "id": user.id,
        "email": user.email,
        "company_id": user.company_id,
        "role": user.role   # system
    }
