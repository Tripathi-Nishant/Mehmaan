import pytest

from app.host_bot.intents import classify_intent
from app.host_bot.onboarding import OnboardingSession, OnboardingState, location_complete
from app.host_bot.readback import render_readback
from app.host_bot.schemas import ListingFieldsUpdate


def complete_fields() -> ListingFieldsUpdate:
    return ListingFieldsUpdate(
        category="food",
        activity_description="Rajasthani khana banana",
        duration_min=180,
        max_guests=4,
        price_per_person_paise=150000,
        city="Jaipur",
        area="Old City",
        available_weekdays=[5],
        start_time_local="11:00",
        food_type="veg",
        consent_voice_clip=True,
    )


# Set by the Telegram location/voice/photo handlers, not by LLM extraction.
LOCATION = {
    "location_lat": 26.9239,
    "location_lng": 75.8267,
    "landmark_hi": "Hawa Mahal ke peeche wali gali",
    "gate_photo_media_id": "00000000-0000-0000-0000-000000000001",
}


def located_session() -> OnboardingSession:
    return OnboardingSession(fields=dict(LOCATION))


def all_fields() -> dict:
    return {**complete_fields().model_dump(), **LOCATION}


def test_merge_moves_to_readback_and_publish_requires_yes():
    session = located_session()
    session.merge(complete_fields())
    assert session.state == OnboardingState.READBACK
    session.publish()
    assert session.state == OnboardingState.DONE


def test_missing_fields_are_in_required_order():
    session = OnboardingSession()
    session.merge(ListingFieldsUpdate(category="food"))
    assert session.missing_fields[:3] == ["activity_description", "duration_min", "max_guests"]


def test_change_returns_to_collecting():
    session = located_session()
    session.merge(complete_fields())
    session.change("area")
    assert session.state == OnboardingState.COLLECTING
    assert "area" in session.missing_fields


def test_turn_limit_abandons_incomplete_session():
    session = OnboardingSession()
    for _ in range(12):
        session.merge(ListingFieldsUpdate(category="food"))
    assert session.state == OnboardingState.ABANDONED


def test_readback_contains_exact_price_and_payout():
    text = render_readback(all_fields())
    assert "₹1,500" in text
    assert "₹1,275" in text


@pytest.mark.parametrize(
    "text, expected", [("haan", "YES"), ("nahi", "NO"), ("kuch badalna hai", "CHANGE")]
)
def test_intent_fallbacks(text: str, expected: str):
    assert classify_intent(text).intent == expected


def test_unclear_is_safe_fallback():
    assert classify_intent("samajh nahi aaya").intent == "UNCLEAR"


def test_consent_no_counts_as_answered():
    session = located_session()
    session.merge(complete_fields().model_copy(update={"consent_voice_clip": False}))
    assert "consent_voice_clip" not in session.missing_fields
    assert session.state == OnboardingState.READBACK


def test_readback_states_fixed_cancellation_policy():
    text = render_readback(all_fields())
    assert "48 ghante" in text


def test_location_complete_needs_pin_landmark_and_gate_photo():
    assert location_complete(LOCATION)
    for key in LOCATION:
        partial = {k: v for k, v in LOCATION.items() if k != key}
        assert not location_complete(partial), key


def test_pin_is_asked_after_schedule_fields():
    session = OnboardingSession()
    session.merge(complete_fields().model_copy(update={"consent_voice_clip": None}))
    assert session.missing_fields[0] == "location_lat"


def test_readback_reads_hindi_landmark():
    assert "Hawa Mahal ke peeche wali gali" in render_readback(all_fields())
