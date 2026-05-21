from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.database import get_db
from backend.serializers import message_dict, ticket_dict
from backend.services import ticket_service

router = APIRouter()


@router.get("/queue")
def review_queue(user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Inbound Messages awaiting review — DRAFTED, on non-escalated Tickets,
    lowest confidence first. Each item is enriched with Ticket/Customer context."""
    items = []
    for message in ticket_service.list_review_queue(db, user["company_id"]):
        ticket = ticket_service.get_ticket(
            db, user["company_id"], message.ticket_id
        )
        customer = (
            ticket_service.get_customer(
                db, user["company_id"], ticket.customer_id
            )
            if ticket
            else None
        )
        items.append(
            {
                **message_dict(message),
                "ticket_subject": ticket.subject if ticket else None,
                "customer_email": customer.email if customer else None,
            }
        )
    return items


@router.get("")
def list_tickets(
    status: str | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List the Company's Tickets, optionally filtered by status."""
    tickets = ticket_service.list_tickets(db, user["company_id"], status)
    return [ticket_dict(t) for t in tickets]


@router.get("/{ticket_id}")
def get_ticket(
    ticket_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """A Ticket with its Customer and full Message thread."""
    ticket = ticket_service.get_ticket(db, user["company_id"], ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    customer = ticket_service.get_customer(
        db, user["company_id"], ticket.customer_id
    )
    messages = ticket_service.list_ticket_messages(
        db, user["company_id"], ticket_id
    )
    return {
        "ticket": ticket_dict(ticket),
        "customer": (
            {"id": customer.id, "email": customer.email, "name": customer.name}
            if customer
            else None
        ),
        "messages": [message_dict(m) for m in messages],
    }
