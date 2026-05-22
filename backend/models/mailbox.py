from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    func,
)

from backend.database import Base
from backend.models.enums import MailboxProvider, MailboxStatus


class Mailbox(Base):
    """A Company's support mailbox — exactly one per Company in v1.

    The App Password is stored only as a Fernet-encrypted token in
    ``encrypted_credential`` (ADR-0002); plaintext never touches the database.
    All mailbox access goes through a connector abstraction, so a Gmail OAuth
    provider can be added later without changing callers.
    """

    __tablename__ = "mailboxes"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(
        Integer,
        ForeignKey("companies.id"),
        nullable=False,
        unique=True,  # one mailbox per Company
        index=True,
    )
    email_address = Column(String, nullable=False)
    provider = Column(
        String, nullable=False, default=MailboxProvider.GMAIL_APP_PASSWORD
    )
    # Fernet-encrypted App Password — encrypt/decrypt via backend/crypto.py.
    encrypted_credential = Column(LargeBinary, nullable=False)
    imap_host = Column(String, nullable=False, default="imap.gmail.com")
    smtp_host = Column(String, nullable=False, default="smtp.gmail.com")
    status = Column(String, nullable=False, default=MailboxStatus.CONNECTED)
    last_polled_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
