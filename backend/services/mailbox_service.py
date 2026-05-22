"""Tenant-scoped operations on a Company's support Mailbox.

One Mailbox per Company. Credentials are verified against the live IMAP/SMTP
servers before anything is stored, and the App Password is persisted only as
a Fernet-encrypted token — never plaintext (ADR-0002).
"""

from sqlalchemy.orm import Session

from app.email.mailbox_connector import AppPasswordConnector
from backend import crypto
from backend.models.enums import MailboxProvider, MailboxStatus
from backend.models.mailbox import Mailbox


def get_mailbox(db: Session, company_id: int) -> Mailbox | None:
    """Return the Company's mailbox, or None if none is connected."""
    return db.query(Mailbox).filter(Mailbox.company_id == company_id).first()


def build_connector(mailbox: Mailbox) -> AppPasswordConnector:
    """Build a live connector from a stored Mailbox row, decrypting the
    credential. The single place that turns persisted mailbox state into a
    usable connector — used by the worker (polling) and the send path.
    """
    return AppPasswordConnector(
        mailbox.email_address,
        crypto.decrypt(mailbox.encrypted_credential),
        imap_host=mailbox.imap_host,
        smtp_host=mailbox.smtp_host,
    )


def connect_mailbox(
    db: Session,
    company_id: int,
    *,
    email_address: str,
    app_password: str,
    imap_host: str,
    smtp_host: str,
) -> Mailbox:
    """Verify credentials against the live mailbox, then store them (App
    Password encrypted). Re-connecting replaces the Company's existing mailbox.

    Raises ``MailboxError`` if IMAP or SMTP verification fails — nothing is
    written to the database in that case.
    """
    # Verify first: a failure raises MailboxError before anything is stored.
    AppPasswordConnector(
        email_address, app_password, imap_host, smtp_host
    ).verify()

    mailbox = get_mailbox(db, company_id)
    if mailbox is None:
        mailbox = Mailbox(company_id=company_id)
        db.add(mailbox)

    mailbox.email_address = email_address
    mailbox.provider = MailboxProvider.GMAIL_APP_PASSWORD
    mailbox.encrypted_credential = crypto.encrypt(app_password)
    mailbox.imap_host = imap_host
    mailbox.smtp_host = smtp_host
    mailbox.status = MailboxStatus.CONNECTED

    db.commit()
    db.refresh(mailbox)
    return mailbox
