"""Ticket and Message state machines: allowed transitions and validation.

Two separate machines (per the design): the Ticket case lifecycle and the
per-Message AI-draft review flow. Status strings are never set arbitrarily —
they go through these validators.
"""

from backend.models.enums import ReviewStatus, TicketStatus


class InvalidTransitionError(Exception):
    """Raised when a status transition is not allowed by the state machine."""


# Ticket case lifecycle.
TICKET_TRANSITIONS: dict[str, set[str]] = {
    TicketStatus.OPEN: {
        TicketStatus.PENDING,
        TicketStatus.RESOLVED,
        TicketStatus.CLOSED,
    },
    TicketStatus.PENDING: {
        TicketStatus.OPEN,
        TicketStatus.RESOLVED,
        TicketStatus.CLOSED,
    },
    TicketStatus.RESOLVED: {TicketStatus.OPEN, TicketStatus.CLOSED},
    TicketStatus.CLOSED: {TicketStatus.OPEN},  # reopen if the Customer replies
}

# Per inbound Message: AI draft -> human review -> send.
REVIEW_TRANSITIONS: dict[str, set[str]] = {
    ReviewStatus.AWAITING_AI: {ReviewStatus.DRAFTED, ReviewStatus.NOT_APPLICABLE},
    ReviewStatus.DRAFTED: {ReviewStatus.DRAFTED, ReviewStatus.REVIEWED},
    ReviewStatus.REVIEWED: {ReviewStatus.DRAFTED, ReviewStatus.SENT},
    ReviewStatus.SENT: set(),
    ReviewStatus.NOT_APPLICABLE: set(),
}


def _check(
    transitions: dict[str, set[str]], current: str, new: str, label: str
) -> None:
    if new not in transitions.get(current, set()):
        raise InvalidTransitionError(
            f"Invalid {label} transition: {current} -> {new}"
        )


def assert_ticket_transition(current: str, new: str) -> None:
    _check(TICKET_TRANSITIONS, current, new, "ticket status")


def assert_review_transition(current: str, new: str) -> None:
    _check(REVIEW_TRANSITIONS, current, new, "message review status")
