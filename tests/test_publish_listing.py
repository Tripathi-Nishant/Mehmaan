from datetime import UTC, datetime, time
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.db.models import Listing, Slot
from app.host_bot.onboarding import OnboardingSession, OnboardingState
from app.host_bot.persistence import publish_listing
from app.host_bot.schemas import ListingFieldsUpdate
from app.llm.schemas import ListingCopy

GATE = "00000000-0000-0000-0000-000000000001"
COPY = ListingCopy(
    title_en="Blue pottery in Amer",
    description_en="Make blue pottery with a Jaipur artisan.",
    landmark_en="Near Amer fort",
)


class FakeDb:
    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    def add_all(self, objs):
        self.added.extend(objs)

    async def flush(self):
        pass

    async def get(self, *_):
        return None

    async def commit(self):
        pass


async def test_publish_copies_location_fields():
    fields = {
        "category": "craft",
        "activity_description": "Blue pottery banana",
        "price_per_person_paise": 120000,
        "city": "Jaipur",
        "area": "Amer",
        "location_lat": 26.98,
        "location_lng": 75.85,
        "location_accuracy_m": 12.5,
        "landmark_hi": "Amer fort ke paas",
        "gate_photo_media_id": GATE,
        "duration_min": 120,
        "max_guests": 4,
        "available_weekdays": [5, 6],
        "start_time_local": "11:00",
        "food_type": None,
    }
    db = FakeDb()
    listing = await publish_listing(
        db, uuid4(), OnboardingSession(fields, OnboardingState.READBACK), "t", COPY
    )
    assert isinstance(listing, Listing) and listing in db.added
    assert (listing.location_lat, listing.location_lng) == (26.98, 75.85)
    assert listing.location_accuracy_m == 12.5
    assert listing.landmark_hi == "Amer fort ke paas"
    assert listing.title_en == COPY.title_en
    assert listing.description_en == COPY.description_en
    assert listing.landmark_en == COPY.landmark_en
    assert listing.gate_photo_media_id == UUID(GATE)
    assert (listing.duration_min, listing.max_guests) == (120, 4)
    assert listing.available_weekdays == [5, 6]
    assert listing.start_time_local == time(11, 0)
    assert listing.food_type is None
    assert (datetime.now(UTC) - listing.published_at).total_seconds() < 5
    slots = [obj for obj in db.added if isinstance(obj, Slot)]
    assert 8 <= len(slots) <= 10  # Sat + Sun over the next 30 days
    assert all(slot.listing_id == listing.id and slot.capacity == 4 for slot in slots)


@pytest.mark.parametrize(
    "given, stored", [("11:00", "11:00"), ("9:30", "09:30"), ("17:05", "17:05")]
)
def test_start_time_is_normalised_to_hh_mm(given, stored):
    assert ListingFieldsUpdate(start_time_local=given).start_time_local == stored


@pytest.mark.parametrize("bad", ["11 baje", "25:00", "shaam"])
def test_bad_start_time_is_rejected(bad):
    with pytest.raises(ValidationError):
        ListingFieldsUpdate(start_time_local=bad)
