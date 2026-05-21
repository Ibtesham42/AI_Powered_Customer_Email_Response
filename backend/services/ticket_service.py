"""Tenant-scoped domain operations for Customers, Tickets and Messages.

Every function takes a ``company_id`` and scopes all queries by it — tenant
isolation is enforced here, not in route handlers. Status changes go through
the state machine.
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models.customer import Customer
from backend.models.enums import MessageDirection, ReviewStatus, TicketStatus
from backend.models.message import Message
from backend.models.ticket import Ticket
from backend.services.state_machine import (
    assert_review_transition,
    assert_ticket_transition,
)


# ---------------- Customers ----------------
def get_or_create_customer(
    db: Session, company_id: int, email: str, name: str | None = None
) -> Customer:
    """Return the Company's Customer for this email, creating it if absent."""
    customer = (
        db.query(Customer)
        .filter(Customer.company_id == company_id, Customer.email == email)
        .first()
    )
    if customer is None:
        customer = Customer(company_id=company_id, email=email, name=name)
        db.add(customer)
        db.commit()
        db.refresh(customer)
    return customer


# ---------------- Tickets ----------------
def get_ticket_for_thread(
    db: Session, company_id: int, thread_id: str
) -> Ticket | None:
    return (
        db.query(Ticket)
        .filter(Ticket.company_id == company_id, Ticket.thread_id == thread_id)
        .first()
    )


def open_ticket(
    db: Session,
    company_id: int,
    customer_id: int,
    subject: str | None,
    thread_id: str | None,
) -> Ticket:
    ticket = Ticket(
        company_id=company_id,
        customer_id=customer_id,
        subject=subject,
        thread_id=thread_id,
        status=TicketStatus.OPEN,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def get_ticket(db: Session, company_id: int, ticket_id: int) -> Ticket | None:
    return (
        db.query(Ticket)
        .filter(Ticket.id == ticket_id, Ticket.company_id == company_id)
        .first()
    )


def list_tickets(
    db: Session, company_id: int, status: str | None = None
) -> list[Ticket]:
    query = db.query(Ticket).filter(Ticket.company_id == company_id)
    if status:
        query = query.filter(Ticket.status == status)
    return query.order_by(Ticket.id.desc()).all()


def transition_ticket(db: Session, ticket: Ticket, new_status: str) -> Ticket:
    assert_ticket_transition(ticket.status, new_status)
    ticket.status = new_status
    if new_status == TicketStatus.RESOLVED:
        ticket.resolved_at = func.now()
    elif new_status == TicketStatus.CLOSED:
        ticket.closed_at = func.now()
    db.commit()
    db.refresh(ticket)
    return ticket


def escalate_ticket(db: Session, ticket: Ticket, reason: str) -> Ticket:
    ticket.escalated = True
    ticket.escalation_reason = reason
    db.commit()
    db.refresh(ticket)
    return ticket


# ---------------- Messages ----------------
def add_message(
    db: Session,
    *,
    company_id: int,
    ticket_id: int,
    direction: str,
    body: str,
    subject: str | None = None,
    sender_email: str | None = None,
    recipient_email: str | None = None,
    message_id: str | None = None,
    in_reply_to: str | None = None,
) -> Message:
    """Append a Message to a Ticket. Inbound messages enter the review flow;
    outbound messages are not applicable to it."""
    review_status = (
        ReviewStatus.AWAITING_AI
        if direction == MessageDirection.INBOUND
        else ReviewStatus.NOT_APPLICABLE
    )
    message = Message(
        company_id=company_id,
        ticket_id=ticket_id,
        direction=direction,
        body=body,
        subject=subject,
        sender_email=sender_email,
        recipient_email=recipient_email,
        message_id=message_id,
        in_reply_to=in_reply_to,
        review_status=review_status,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def transition_message(db: Session, message: Message, new_status: str) -> Message:
    assert_review_transition(message.review_status, new_status)
    message.review_status = new_status
    db.commit()
    db.refresh(message)
    return message
