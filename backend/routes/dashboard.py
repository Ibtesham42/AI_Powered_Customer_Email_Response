
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.auth.dependencies import get_current_user
from backend.models.email import Email

router = APIRouter()


@router.get("/stats")
def get_dashboard(user=Depends(get_current_user), db: Session = Depends(get_db)):

    company_id = user["company_id"]

    base = db.query(Email).filter(Email.company_id == company_id)

    return {
        "total_emails": base.count(),
        "new": base.filter(Email.status == "NEW").count(),
        "ai_generated": base.filter(Email.status == "AI_GENERATED").count(),
        "reviewed": base.filter(Email.status == "HUMAN_REVIEWED").count(),
        "sent": base.filter(Email.status == "SENT").count()
    }

