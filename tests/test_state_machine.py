"""Ticket + Message review state-machine transition rules."""

import pytest

from backend.models.enums import ReviewStatus, TicketStatus
from backend.services.state_machine import (
    InvalidTransitionError,
    assert_review_transition,
    assert_ticket_transition,
)


@pytest.mark.parametrize(
    "current,new",
    [
        (TicketStatus.OPEN, TicketStatus.PENDING),
        (TicketStatus.OPEN, TicketStatus.RESOLVED),
        (TicketStatus.PENDING, TicketStatus.RESOLVED),
        (TicketStatus.RESOLVED, TicketStatus.CLOSED),
        (TicketStatus.CLOSED, TicketStatus.OPEN),  # reopen on reply
    ],
)
def test_valid_ticket_transitions(current, new):
    assert_ticket_transition(current, new)  # does not raise


@pytest.mark.parametrize(
    "current,new",
    [
        (TicketStatus.CLOSED, TicketStatus.RESOLVED),
        (TicketStatus.RESOLVED, TicketStatus.PENDING),
        (TicketStatus.CLOSED, TicketStatus.PENDING),
    ],
)
def test_invalid_ticket_transitions(current, new):
    with pytest.raises(InvalidTransitionError):
        assert_ticket_transition(current, new)


@pytest.mark.parametrize(
    "current,new",
    [
        (ReviewStatus.AWAITING_AI, ReviewStatus.DRAFTED),
        (ReviewStatus.DRAFTED, ReviewStatus.REVIEWED),
        (ReviewStatus.REVIEWED, ReviewStatus.SENT),
        (ReviewStatus.REVIEWED, ReviewStatus.DRAFTED),  # regenerate
    ],
)
def test_valid_review_transitions(current, new):
    assert_review_transition(current, new)


@pytest.mark.parametrize(
    "current,new",
    [
        (ReviewStatus.AWAITING_AI, ReviewStatus.SENT),  # cannot skip review
        (ReviewStatus.SENT, ReviewStatus.REVIEWED),  # terminal
        (ReviewStatus.DRAFTED, ReviewStatus.SENT),  # must be reviewed first
    ],
)
def test_invalid_review_transitions(current, new):
    with pytest.raises(InvalidTransitionError):
        assert_review_transition(current, new)
