import pytest

from app.booking.actions import capture_payment, host_accept, host_decline, refund_declined
from app.booking.states import InvalidTransitionError


def test_capture_and_host_acceptance():
    captured = capture_payment("HELD", 10000, 1500)
    assert captured.status.value == "PAID_PENDING_HOST"
    assert captured.ledger.host_payable == 8500
    assert host_accept(captured.status.value) == "CONFIRMED"


def test_decline_then_refund():
    assert refund_declined(host_decline("PAID_PENDING_HOST")) == "REFUNDED"


def test_invalid_refund_before_decline():
    with pytest.raises(InvalidTransitionError):
        refund_declined("HELD")
