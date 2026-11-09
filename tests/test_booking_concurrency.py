from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.booking.db_service import SlotFullError, create_hold
from app.db.models import Booking, Traveler

NOW = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)


class FakeDb:
    """Returns one slot (for the FOR UPDATE select) and one listing (for get)."""

    def __init__(self, slot, listing):
        self.slot, self.listing, self.added = slot, listing, []

    async def scalar(self, _statement):
        return self.slot

    async def get(self, _model, _id):
        return self.listing

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        pass


def db(capacity=4, booked=0, status="LIVE", starts_in=timedelta(days=2)):
    listing = SimpleNamespace(id=uuid4(), status=status, price_per_person_paise=150000)
    slot = SimpleNamespace(
        id=uuid4(),
        listing_id=listing.id,
        capacity=capacity,
        booked_count=booked,
        starts_at=NOW + starts_in,
    )
    return FakeDb(slot, listing)


async def hold(fake, guests=2):
    return await create_hold(fake, fake.slot.id, "Asha", "a@example.com", guests, 15, NOW)


async def test_hold_reserves_seats_with_server_side_amount_and_expiry():
    fake = db()
    booking = await hold(fake)
    assert booking.id is not None  # Payment can reference it in the same transaction
    assert booking.status == "HELD"
    assert booking.amount_paise == 300000
    assert booking.hold_expires_at == NOW + timedelta(minutes=15)
    assert fake.slot.booked_count == 2
    traveler = next(obj for obj in fake.added if isinstance(obj, Traveler))
    assert booking.traveler_id == traveler.id
    assert any(obj is booking for obj in fake.added if isinstance(obj, Booking))


async def test_last_seat_can_only_be_reserved_once():
    fake = db(capacity=1)
    await hold(fake, guests=1)
    with pytest.raises(SlotFullError):
        await hold(fake, guests=1)


@pytest.mark.parametrize(
    "fake, guests",
    [
        (db(capacity=2, booked=2), 1),  # full
        (db(), 0),  # no guests
        (db(status="PAUSED"), 1),  # listing not bookable
        (db(starts_in=timedelta(hours=-1)), 1),  # slot already started
    ],
)
async def test_unbookable_holds_are_rejected(fake, guests):
    with pytest.raises(SlotFullError):
        await hold(fake, guests)
    assert fake.added == []


async def test_missing_slot_is_rejected():
    fake = db()
    fake.slot = None
    with pytest.raises(SlotFullError):
        await create_hold(fake, uuid4(), "Asha", "a@example.com", 1, 15, NOW)
