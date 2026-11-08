import pytest

from app.booking.states import BookingStatus, InvalidTransitionError, transition
from app.payments.ledger import LedgerBalanceError, split_charge


def test_booking_transitions_are_restricted():
    assert transition(BookingStatus.HELD, BookingStatus.PAID_PENDING_HOST)
    with pytest.raises(InvalidTransitionError):
        transition(BookingStatus.HELD, BookingStatus.CONFIRMED)


def test_ledger_split_balances_in_paise():
    split = split_charge(10000, 1500)
    assert split.commission == 1500
    assert split.host_payable == 8500


def test_negative_ledger_is_rejected():
    with pytest.raises(LedgerBalanceError):
        split_charge(-1, 1500)
