from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.database import get_db
from backend.services import ticket_service

router = APIRouter()


@router.get("/stats")
def dashboard_stats(
    user=Depends(get_current_user), db: Session = Depends(get_db)
):
    """Ticket counts for the dashboard overview, scoped to the Company."""
    return ticket_service.company_stats(db, user["company_id"])
