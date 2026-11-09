from datetime import UTC, datetime, timedelta

import pytest

from app.booking.actions import (
    HoldExpiredError,
    capture_payment,
    host_accept,
    host_decline,
    refund_declined,
)
from app.booking.states import InvalidTransitionError

NOW = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)
LATER = NOW + timedelta(minutes=5)


def test_capture_and_host_acceptance():
    captured = capture_payment("HELD", 10000, 1500, hold_expires_at=LATER, now=NOW)
    assert captured.status.value == "PAID_PENDING_HOST"
    assert captured.ledger.host_payable == 8500
    assert host_accept(captured.status.value) == "CONFIRMED"


def test_expired_hold_cannot_be_paid():
    with pytest.raises(HoldExpiredError):
        capture_payment("HELD", 10000, 1500, hold_expires_at=NOW, now=NOW)


@pytest.mark.parametrize("status", ["EXPIRED", "PAID_PENDING_HOST", "CONFIRMED", "REFUNDED"])
def test_only_held_bookings_can_be_paid(status):
    with pytest.raises(InvalidTransitionError):
        capture_payment(status, 10000, 1500, hold_expires_at=LATER, now=NOW)


def test_decline_then_refund():
    assert refund_declined(host_decline("PAID_PENDING_HOST")) == "REFUNDED"


def test_invalid_refund_before_decline():
    with pytest.raises(InvalidTransitionError):
        refund_declined("HELD")
