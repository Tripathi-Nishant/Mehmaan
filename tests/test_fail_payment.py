from types import SimpleNamespace

import pytest

from app.booking.actions import expire_hold
from app.booking.states import InvalidTransitionError
from app.web.booking_routes import templates


def make(status="HELD", guests=2, booked=3):
    return SimpleNamespace(status=status, guests=guests), SimpleNamespace(booked_count=booked)


def test_expire_hold_releases_seats():
    booking, slot = make()
    expire_hold(booking, slot)
    assert booking.status == "EXPIRED"
    assert slot.booked_count == 1


def test_seat_count_never_goes_negative():
    booking, slot = make(guests=2, booked=1)
    expire_hold(booking, slot)
    assert slot.booked_count == 0


@pytest.mark.parametrize("status", ["PAID_PENDING_HOST", "CONFIRMED", "EXPIRED"])
def test_only_held_bookings_expire_and_seats_stay(status):
    booking, slot = make(status=status)
    with pytest.raises(InvalidTransitionError):
        expire_hold(booking, slot)
    assert slot.booked_count == 3


def test_checkout_has_pay_and_fail_buttons():
    payment = SimpleNamespace(provider_order_id="mock_order_x", amount_paise=300000)
    html = templates.get_template("payment.html").render(payment=payment)
    assert 'action="/pay/mock/mock_order_x/verify"' in html
    assert 'action="/pay/mock/mock_order_x/fail"' in html
    assert "TEST" in html
