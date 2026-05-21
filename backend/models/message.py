from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    func,
)

from backend.database import Base


class Message(Base):
    """A single email belonging to one Ticket. Inbound (from the Customer) or
    outbound (sent by the Company). An inbound Message needing a reply carries
    the review flow in `review_status` (see ReviewStatus)."""

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(
        Integer, ForeignKey("companies.id"), nullable=False, index=True
    )
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False, index=True)

    direction = Column(String, nullable=False)  # MessageDirection
    sender_email = Column(String)
    recipient_email = Column(String)
    subject = Column(String)
    body = Column(String)

    message_id = Column(String)  # email Message-ID header
    in_reply_to = Column(String)  # email In-Reply-To header

    review_status = Column(String)  # ReviewStatus (inbound-needing-reply only)
    intent = Column(String)
    confidence = Column(SmallInteger)  # 0-100
    ai_draft = Column(String)  # the Draft
    final_reply = Column(String)  # human-edited text actually sent
    reviewed_by = Column(Integer, ForeignKey("users.id"))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sent_at = Column(DateTime(timezone=True))
