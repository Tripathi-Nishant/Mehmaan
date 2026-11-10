from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.web.booking_routes import templates

LISTING = SimpleNamespace(id="L1", title_en="Dal baati with Meena", area="Old City", city="Jaipur")
SLOT = SimpleNamespace(starts_at=datetime(2026, 11, 14, 5, 30, tzinfo=UTC))
HOST = SimpleNamespace(display_name="Meena")
TRAVELER = SimpleNamespace(name="Sophie Martin")


def render(status, amount=240000, keep=0, location=None, cancellable=False):
    booking = SimpleNamespace(
        status=status,
        access_token="tok",
        guests=2,
        amount_paise=amount,
        host_payout_paise=keep,
        dietary_notes=None,
        hold_expires_at=None,
    )
    return templates.get_template("booking.html").render(
        booking=booking,
        listing=LISTING,
        slot=SLOT,
        host=HOST,
        traveler=TRAVELER,
        location=location,
        cancellable=cancellable,
    )


@pytest.mark.parametrize(
    "status, text",
    [
        ("PAID_PENDING_HOST", "Meena ji has your request"),
        ("CONFIRMED", "Your place is ready"),
        ("EXPIRED", "Your reservation time ended"),
        ("REFUNDED", "Meena ji could not host you"),
        ("COMPLETED", "Phir zaroor aana: please come again, Sophie."),
    ],
)
def test_each_status_has_its_own_message(status, text):
    html = render(status)
    assert text in html
    assert f'data-status="{status}"' in html


def test_cancelled_shows_the_actual_refund():
    html = render("CANCELLED", amount=300000, keep=60000)
    assert "₹2,400 refunded (TEST)" in html


def test_confirmed_shows_details_and_map_only_with_location():
    html = render("CONFIRMED", location={"map_url": "https://maps/x", "landmark": "Blue gate"})
    assert "Sat 14 Nov, 11:00 AM" in html and "https://maps/x" in html and "Blue gate" in html


def test_cancel_link_only_when_cancellable():
    assert 'href="/b/tok/cancel"' in render("CONFIRMED", cancellable=True)
    assert 'href="/b/tok/cancel"' not in render("CONFIRMED")
