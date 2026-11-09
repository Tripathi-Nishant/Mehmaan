from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.booking.slots import format_ist
from app.web.routes import templates

LISTING = SimpleNamespace(
    id=uuid4(),
    category="craft",
    city="Jaipur",
    area="Amer",
    title_en="Blue pottery in Amer",
    description_en="Make blue pottery with a Jaipur artisan.",
    description_hi="Blue pottery banana",
    price_per_person_paise=120000,
    max_guests=4,
)


def slot(day: int, booked: int = 0):
    starts = datetime(2026, 11, day, 5, 30, tzinfo=UTC)  # 11:00 IST
    return SimpleNamespace(id=uuid4(), starts_at=starts, capacity=4, booked_count=booked)


def render(slots) -> str:
    return templates.get_template("listing.html").render(listing=LISTING, slots=slots)


def test_format_ist():
    assert format_ist(datetime(2026, 11, 14, 5, 30, tzinfo=UTC)) == "Sat 14 Nov, 11:00 AM"
    assert format_ist(datetime(2026, 11, 14, 12, 0, tzinfo=UTC)) == "Sat 14 Nov, 5:30 PM"


def test_one_option_per_slot_with_ist_time_and_seats():
    slots = [slot(14), slot(15, booked=3)]
    html = render(slots)
    assert html.count('name="slot_id"') == 2
    assert all(f'value="{s.id}"' in html for s in slots)
    assert "Sat 14 Nov, 11:00 AM · 4 seats left" in html
    assert "Sun 15 Nov, 11:00 AM · 1 seat left" in html
    assert 'action="/book"' in html
    assert html.count("checked") == 1


def test_no_slots_message():
    assert "No upcoming dates" in render([])


def test_failed_payment_notice_only_when_flagged():
    page = templates.get_template("listing.html")
    assert "TEST payment failed" in page.render(listing=LISTING, slots=[], payment_failed=True)
    assert "TEST payment failed" not in render([])
