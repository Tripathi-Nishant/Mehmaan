import pytest

from app.host_bot.intents import classify_intent
from app.host_bot.onboarding import OnboardingSession, OnboardingState
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
        landmark="Hawa Mahal",
        consent_voice_clip=True,
        cancellation_rule="48 ghante pehle free",
        location_shared=True,
    )


def test_merge_moves_to_readback_and_publish_requires_yes():
    session = OnboardingSession()
    session.merge(complete_fields())
    assert session.state == OnboardingState.READBACK
    session.publish()
    assert session.state == OnboardingState.DONE


def test_missing_fields_are_in_required_order():
    session = OnboardingSession()
    session.merge(ListingFieldsUpdate(category="food"))
    assert session.missing_fields[:3] == ["activity_description", "duration_min", "max_guests"]


def test_change_returns_to_collecting():
    session = OnboardingSession()
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
    text = render_readback(complete_fields().model_dump())
    assert "₹1,500" in text
    assert "₹1,275" in text


@pytest.mark.parametrize(
    "text, expected", [("haan", "YES"), ("nahi", "NO"), ("kuch badalna hai", "CHANGE")]
)
def test_intent_fallbacks(text: str, expected: str):
    assert classify_intent(text).intent == expected


def test_unclear_is_safe_fallback():
    assert classify_intent("samajh nahi aaya").intent == "UNCLEAR"
