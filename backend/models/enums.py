"""Canonical domain enum values.

Stored as plain strings in the database (consistent with the existing
``emails.status`` column) and validated at the application layer via these
``StrEnum`` classes — avoids the ALTER TYPE friction of native Postgres enums.
"""

from enum import StrEnum


class TicketStatus(StrEnum):
    """Ticket case lifecycle."""

    OPEN = "open"
    PENDING = "pending"  # waiting on the Customer
    RESOLVED = "resolved"
    CLOSED = "closed"


class ReviewStatus(StrEnum):
    """Per inbound Message: the AI draft -> human review -> send flow."""

    AWAITING_AI = "awaiting_ai"
    DRAFTED = "drafted"
    REVIEWED = "reviewed"
    SENT = "sent"
    NOT_APPLICABLE = "not_applicable"  # e.g. outbound messages


class MessageDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class Intent(StrEnum):
    """Detected intent of an inbound Message."""

    PRODUCT_INQUIRY = "product_inquiry"
    DAMAGED_DELIVERY = "damaged_delivery"
    REFUND_REQUEST = "refund_request"
    SERVICE_INQUIRY = "service_inquiry"
    COMPLAINT = "complaint"
    GENERAL_SUPPORT = "general_support"


class MailboxProvider(StrEnum):
    """How a Company's support mailbox authenticates."""

    GMAIL_APP_PASSWORD = "gmail_app_password"
    # Future: GMAIL_OAUTH = "gmail_oauth" — see ADR-0002.


class MailboxStatus(StrEnum):
    """Health of a connected mailbox."""

    CONNECTED = "connected"  # last IMAP/SMTP check succeeded
    ERROR = "error"  # last check failed — needs reconnection
