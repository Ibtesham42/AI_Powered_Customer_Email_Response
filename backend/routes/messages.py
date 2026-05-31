from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.database import get_db
from backend.logging_config import get_logger
from backend.models.enums import MessageDirection, ReviewStatus, TicketStatus
from backend.models.schemas import DraftUpdate, RejectRequest
from backend.serializers import message_dict
from backend.services import (
    ai_service,
    audit_service,
    escalation_service,
    mailbox_service,
    ticket_service,
)

router = APIRouter()
logger = get_logger(__name__)


def _require_message(db: Session, company_id: int, message_id: int):
    message = ticket_service.get_message(db, company_id, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    return message


@router.post("/{message_id}/regenerate")
def regenerate_draft(
    message_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Re-run the AI draft for an inbound Message."""
    message = _require_message(db, user["company_id"], message_id)
    result = ai_service.generate_draft(db, message)
    ticket_service.record_ai_draft(
        db, message, result["reply"], result["confidence"], result["intent"]
    )
    ticket = ticket_service.get_ticket(db, user["company_id"], message.ticket_id)
    if ticket is not None:
        escalation_service.apply_draft_escalation(db, ticket, result)
    return message_dict(message)


@router.put("/{message_id}/draft")
def edit_draft(
    message_id: int,
    payload: DraftUpdate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Edit/rewrite the draft, then mark the Message reviewed."""
    message = _require_message(db, user["company_id"], message_id)
    message.final_reply = payload.text
    ticket_service.transition_message(db, message, ReviewStatus.REVIEWED)
    return message_dict(message)


@router.post("/{message_id}/approve")
def approve_draft(
    message_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Accept the AI draft unchanged, then mark the Message reviewed."""
    message = _require_message(db, user["company_id"], message_id)
    message.final_reply = message.ai_draft
    ticket_service.transition_message(db, message, ReviewStatus.REVIEWED)
    return message_dict(message)


@router.post("/{message_id}/reject")
def reject_draft(
    message_id: int,
    payload: RejectRequest,
    request: Request,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reject the draft — escalate the Ticket for manual handling."""
    message = _require_message(db, user["company_id"], message_id)
    ticket = ticket_service.get_ticket(db, user["company_id"], message.ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    reason = payload.reason or "agent_rejected"
    ticket_service.escalate_ticket(db, ticket, reason)
    audit_service.record(
        db,
        action="draft_rejected",
        request=request,
        company_id=user["company_id"],
        user_id=user["id"],
        entity_type="ticket",
        entity_id=ticket.id,
        metadata={"message_id": message.id, "reason": reason},
    )
    return {"message": "Draft rejected; ticket escalated", "ticket_id": ticket.id}


@router.post("/{message_id}/send")
def send_reply(
    message_id: int,
    request: Request,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send the reviewed reply to the Customer over SMTP."""
    message = _require_message(db, user["company_id"], message_id)
    if message.review_status != ReviewStatus.REVIEWED:
        raise HTTPException(
            status_code=409, detail="Message must be reviewed before sending"
        )

    ticket = ticket_service.get_ticket(db, user["company_id"], message.ticket_id)
    customer = (
        ticket_service.get_customer(db, user["company_id"], ticket.customer_id)
        if ticket
        else None
    )
    if ticket is None or customer is None:
        raise HTTPException(status_code=404, detail="Ticket or customer not found")

    reply_text = message.final_reply
    if not reply_text:
        raise HTTPException(status_code=400, detail="No reply content")

    # Send from the Company's own connected mailbox.
    mailbox = mailbox_service.get_mailbox(db, user["company_id"])
    if mailbox is None:
        raise HTTPException(
            status_code=400,
            detail="No mailbox connected — connect one at /mailbox/connect",
        )

    subject = f"Re: {ticket.subject}" if ticket.subject else "Re: your enquiry"
    mailbox_service.build_connector(mailbox).send(
        to_email=customer.email,
        subject=subject,
        body=reply_text,
        in_reply_to=message.message_id,
    )

    # The sent reply becomes an outbound Message on the Ticket.
    ticket_service.add_message(
        db,
        company_id=user["company_id"],
        ticket_id=ticket.id,
        direction=MessageDirection.OUTBOUND,
        body=reply_text,
        subject=subject,
        recipient_email=customer.email,
    )
    ticket_service.transition_message(db, message, ReviewStatus.SENT)
    if ticket.status == TicketStatus.OPEN:
        ticket_service.transition_ticket(db, ticket, TicketStatus.PENDING)

    audit_service.record(
        db,
        action="message_sent",
        request=request,
        company_id=user["company_id"],
        user_id=user["id"],
        entity_type="message",
        entity_id=message.id,
        metadata={"ticket_id": ticket.id, "customer_email": customer.email},
    )

    logger.info("Sent reply for message %s to %s", message.id, customer.email)
    return {"message": "Reply sent", "message_id": message.id}
