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


def summary(status="CREATED"):
    from datetime import UTC, datetime

    return {
        "payment": SimpleNamespace(
            provider_order_id="mock_order_x", amount_paise=240000, status=status
        ),
        "booking": SimpleNamespace(
            guests=2,
            amount_paise=240000,
            dietary_notes="No peanuts",
            access_token="tok",
            hold_expires_at=datetime(2026, 11, 14, 4, 0, tzinfo=UTC),
        ),
        "slot": SimpleNamespace(starts_at=datetime(2026, 11, 14, 5, 30, tzinfo=UTC)),
        "listing": SimpleNamespace(
            id="L1",
            title_en="Dal baati with Meena",
            price_per_person_paise=120000,
            area="Old City",
            city="Jaipur",
        ),
        "traveler": SimpleNamespace(name="Sophie", email="s@example.com"),
    }


def test_checkout_summarises_booking_and_states_test_payment():
    html = templates.get_template("payment.html").render(**summary())
    for text in (
        "Dal baati with Meena",
        "Sat 14 Nov, 11:00 AM",
        "₹1,200 × 2 guests",
        "₹2,400",
        "Sophie",
        "s@example.com",
        "No peanuts",
        "TEST PAYMENT — No real money will be charged.",
        "48 hours",
    ):
        assert text in html, text


def test_paid_checkout_links_to_booking_instead_of_buttons():
    html = templates.get_template("payment.html").render(**summary("CAPTURED"))
    assert "/verify" not in html and 'href="/b/tok"' in html
