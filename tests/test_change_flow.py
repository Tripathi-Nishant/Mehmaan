import pytest

from app.host_bot.intents import fields_to_change
from app.host_bot.onboarding import OnboardingSession, OnboardingState
from app.host_bot.schemas import ListingFieldsUpdate
from app.host_bot.service import question_for_field, reply_for, try_change

FULL = {
    "category": "craft",
    "activity_description": "Blue pottery banana",
    "duration_min": 120,
    "max_guests": 4,
    "price_per_person_paise": 120000,
    "city": "Jaipur",
    "area": "Amer",
    "available_weekdays": [5, 6],
    "start_time_local": "11:00",
    "location_lat": 26.98,
    "location_lng": 75.85,
    "landmark_hi": "Amer fort ke paas",
    "gate_photo_media_id": "m1",
    "consent_voice_clip": True,
}


def readback_session() -> OnboardingSession:
    return OnboardingSession(fields=dict(FULL), state=OnboardingState.READBACK)


def test_daam_badalna_hai_reopens_only_price():
    session = readback_session()
    assert try_change(session, "daam badalna hai")
    assert session.state == OnboardingState.COLLECTING
    assert session.missing_fields == ["price_per_person_paise"]
    assert reply_for(session, 1500) == question_for_field("price_per_person_paise")


def test_new_answer_returns_to_readback_with_new_value():
    session = readback_session()
    try_change(session, "daam badalna hai")
    session.merge(ListingFieldsUpdate(price_per_person_paise=150000))
    assert session.state == OnboardingState.READBACK
    assert "₹1,500" in reply_for(session, 1500)


def test_location_change_clears_the_whole_pin():
    session = readback_session()
    assert try_change(session, "location galat hai")
    assert session.missing_fields == ["location_lat", "location_lng"]


@pytest.mark.parametrize("said", ["nahi", "haan", "kuch theek nahi lag raha"])
def test_no_named_field_keeps_readback(said):
    session = readback_session()
    assert not try_change(session, said)
    assert session.state == OnboardingState.READBACK


def test_change_only_applies_in_readback():
    session = OnboardingSession(fields={"city": "Jaipur"})
    assert not try_change(session, "daam badalna hai")


@pytest.mark.parametrize(
    "said, fields",
    [
        ("samay badlo", ("start_time_local",)),
        ("दाम बदलना है", ("price_per_person_paise",)),
        ("din change karne hain", ("available_weekdays",)),
        ("dinner ka khana", None),  # whole words only: "din" must not match "dinner"
    ],
)
def test_fields_to_change(said, fields):
    assert fields_to_change(said) == fields


def test_change_resets_turn_budget():
    session = readback_session()
    session.turn_count = 11
    try_change(session, "daam badalna hai")
    session.merge(ListingFieldsUpdate(price_per_person_paise=150000))
    assert session.state == OnboardingState.READBACK
