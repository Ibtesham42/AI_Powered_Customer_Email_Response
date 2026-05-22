from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.email.mailbox_connector import MailboxError
from backend.auth.dependencies import get_current_user, require_owner
from backend.database import get_db
from backend.logging_config import get_logger
from backend.models.schemas import MailboxConnectRequest
from backend.serializers import mailbox_dict
from backend.services import audit_service, mailbox_service

router = APIRouter()
logger = get_logger(__name__)


@router.post("/connect")
def connect_mailbox(
    payload: MailboxConnectRequest,
    request: Request,
    user=Depends(require_owner),
    db: Session = Depends(get_db),
):
    """Verify a support mailbox's IMAP + SMTP login, then store it for the
    Company (App Password encrypted at rest). Owner-only."""
    try:
        mailbox = mailbox_service.connect_mailbox(
            db,
            user["company_id"],
            email_address=payload.email_address,
            app_password=payload.app_password,
            imap_host=payload.imap_host,
            smtp_host=payload.smtp_host,
        )
    except MailboxError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    audit_service.record(
        db,
        action="mailbox_connected",
        request=request,
        company_id=user["company_id"],
        user_id=user["id"],
        entity_type="mailbox",
        entity_id=mailbox.id,
        metadata={"email_address": mailbox.email_address},
    )
    logger.info(
        "Mailbox connected for company %s: %s",
        user["company_id"],
        mailbox.email_address,
    )
    return mailbox_dict(mailbox)


@router.get("")
def get_mailbox(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the Company's connected mailbox, or 404 if none is connected."""
    mailbox = mailbox_service.get_mailbox(db, user["company_id"])
    if mailbox is None:
        raise HTTPException(status_code=404, detail="No mailbox connected")
    return mailbox_dict(mailbox)
