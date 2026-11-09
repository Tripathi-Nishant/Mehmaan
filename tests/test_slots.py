from datetime import UTC, date, datetime, time
from uuid import uuid4

from app.booking.slots import IST, generate_slots

MONDAY = date(2026, 11, 9)  # window: Tue 10 Nov .. Wed 9 Dec
LISTING = uuid4()


def test_only_requested_weekdays_in_ist():
    slots = generate_slots(LISTING, [5, 6], time(11, 0), 4, MONDAY)
    assert len(slots) == 8  # Sat/Sun: 14,15,21,22,28,29 Nov + 5,6 Dec
    assert {s.starts_at.astimezone(IST).weekday() for s in slots} == {5, 6}


def test_ist_start_time_is_stored_as_utc():
    first = generate_slots(LISTING, [5], time(11, 0), 4, MONDAY)[0]
    assert first.starts_at == datetime(2026, 11, 14, 5, 30, tzinfo=UTC)


def test_early_morning_start_keeps_the_indian_weekday():
    # 04:00 IST Saturday is 22:30 UTC Friday; the slot must still be the host's Saturday.
    first = generate_slots(LISTING, [5], time(4, 0), 4, MONDAY)[0]
    assert first.starts_at == datetime(2026, 11, 13, 22, 30, tzinfo=UTC)
    assert first.starts_at.astimezone(IST).weekday() == 5


def test_window_is_tomorrow_through_30_days():
    slots = generate_slots(LISTING, list(range(7)), time(11, 0), 4, MONDAY)
    ist_dates = [s.starts_at.astimezone(IST).date() for s in slots]
    assert len(slots) == 30
    assert ist_dates[0] == date(2026, 11, 10)
    assert ist_dates[-1] == date(2026, 12, 9)


def test_slot_capacity_and_listing():
    slot = generate_slots(LISTING, [5], time(11, 0), 6, MONDAY)[0]
    assert (slot.listing_id, slot.capacity, slot.booked_count) == (LISTING, 6, 0)
