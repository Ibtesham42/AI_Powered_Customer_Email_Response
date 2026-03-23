from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.database import get_db
from backend.auth.dependencies import get_current_user
from backend.models.email import Email

router = APIRouter()


@router.get("/stats")
def get_dashboard(user=Depends(get_current_user), db: Session = Depends(get_db)):

    company_id = user["company_id"]

    total_emails = db.query(func.count(Email.id)).filter(
        Email.company_id == company_id
    ).scalar()

    replied = db.query(func.count(Email.id)).filter(
        Email.company_id == company_id,
        Email.status == "replied"
    ).scalar()

    pending = db.query(func.count(Email.id)).filter(
        Email.company_id == company_id,
        Email.status == "pending"
    ).scalar()

    return {
        "total_emails": total_emails,
        "replied": replied,
        "pending": pending
    }