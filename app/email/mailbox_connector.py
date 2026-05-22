"""Mailbox connector abstraction.

Every interaction with a Company's support mailbox — verifying credentials,
fetching inbound mail, sending replies — goes through a ``MailboxConnector``.
Callers stay independent of *how* the mailbox authenticates, so a Gmail OAuth
connector can be added later without changing them (ADR-0002).
"""

import imaplib
import smtplib
from abc import ABC, abstractmethod

from app.email.email_listener import EmailListener
from app.email.email_sender import EmailSender

# Network operations get a bounded timeout so a verify call cannot hang a
# request indefinitely.
_TIMEOUT_SECONDS = 15


class MailboxError(Exception):
    """A mailbox operation failed — bad credentials, or the host is
    unreachable. The message is user-facing and safe to surface."""


class MailboxConnector(ABC):
    """Interface for all mailbox access."""

    @abstractmethod
    def verify(self) -> None:
        """Check the mailbox accepts both reading (IMAP) and sending (SMTP).
        Raise ``MailboxError`` if either fails."""

    @abstractmethod
    def fetch_unread(self) -> list[dict]:
        """Return unread inbound messages, marking them read."""

    @abstractmethod
    def send(
        self,
        *,
        to_email: str,
        subject: str,
        body: str,
        in_reply_to: str | None = None,
    ) -> None:
        """Send an outbound reply."""


class AppPasswordConnector(MailboxConnector):
    """An IMAP/SMTP mailbox authenticated with an App Password (Gmail in v1).

    The App Password is held only in memory for the connector's lifetime; at
    rest it lives Fernet-encrypted in the ``mailboxes`` table.
    """

    def __init__(
        self,
        email_address: str,
        app_password: str,
        imap_host: str = "imap.gmail.com",
        smtp_host: str = "smtp.gmail.com",
    ) -> None:
        self.email_address = email_address
        self._app_password = app_password
        self.imap_host = imap_host
        self.smtp_host = smtp_host

    def verify(self) -> None:
        self._verify_imap()
        self._verify_smtp()

    def _verify_imap(self) -> None:
        try:
            with imaplib.IMAP4_SSL(
                self.imap_host, timeout=_TIMEOUT_SECONDS
            ) as imap:
                imap.login(self.email_address, self._app_password)
        except imaplib.IMAP4.error as exc:
            raise MailboxError(
                "IMAP login failed — check the email address and App Password."
            ) from exc
        except OSError as exc:
            raise MailboxError(
                f"Could not reach the IMAP server {self.imap_host!r}."
            ) from exc

    def _verify_smtp(self) -> None:
        try:
            with smtplib.SMTP_SSL(
                self.smtp_host, 465, timeout=_TIMEOUT_SECONDS
            ) as smtp:
                smtp.login(self.email_address, self._app_password)
        except smtplib.SMTPException as exc:
            raise MailboxError(
                "SMTP login failed — check the email address and App Password."
            ) from exc
        except OSError as exc:
            raise MailboxError(
                f"Could not reach the SMTP server {self.smtp_host!r}."
            ) from exc

    def fetch_unread(self) -> list[dict]:
        listener = EmailListener(
            host=self.imap_host,
            email_user=self.email_address,
            password=self._app_password,
        )
        return listener.fetch_unread_emails()

    def send(
        self,
        *,
        to_email: str,
        subject: str,
        body: str,
        in_reply_to: str | None = None,
    ) -> None:
        EmailSender(self.email_address, self._app_password).send_email(
            to_email=to_email,
            subject=subject,
            body=body,
            message_id=in_reply_to,
        )
