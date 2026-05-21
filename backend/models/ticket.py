from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)

from backend.database import Base
from backend.models.enums import TicketStatus


class Ticket(Base):
    """One support case — equals one email thread. Belongs to one Customer and
    one Company. Carries the case lifecycle (see TicketStatus)."""

    __tablename__ = "tickets"
    __table_args__ = (
        UniqueConstraint("company_id", "thread_id", name="uq_tickets_company_thread"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(
        Integer, ForeignKey("companies.id"), nullable=False, index=True
    )
    customer_id = Column(
        Integer, ForeignKey("customers.id"), nullable=False, index=True
    )

    subject = Column(String)
    thread_id = Column(String)

    status = Column(String, nullable=False, default=TicketStatus.OPEN)
    escalated = Column(Boolean, nullable=False, default=False)
    escalation_reason = Column(String)
    intent = Column(String)
    assigned_to = Column(Integer, ForeignKey("users.id"))
    summary = Column(String)  # generated on close — feeds Memory

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    resolved_at = Column(DateTime(timezone=True))
    closed_at = Column(DateTime(timezone=True))
