from app.host_bot.location import PIN_REJECTIONS
from app.host_bot.onboarding import OnboardingSession, OnboardingState
from app.host_bot.service import keyboard_for, photo_kind, question_for_field, reply_for

BEFORE_PIN = {
    "category": "craft",
    "activity_description": "Blue pottery banana",
    "duration_min": 120,
    "max_guests": 4,
    "price_per_person_paise": 120000,
    "city": "Jaipur",
    "area": "Amer",
    "available_weekdays": [5, 6],
    "start_time_local": "11:00",
}
PIN = {"location_lat": 26.98, "location_lng": 75.85}


def session_with(**extra) -> OnboardingSession:
    return OnboardingSession(fields={**BEFORE_PIN, **extra})


def test_pin_question_shows_location_button():
    keyboard = keyboard_for(session_with())
    assert keyboard is not None
    assert keyboard.keyboard[0][0].request_location is True


def test_no_location_button_once_pin_is_stored():
    assert keyboard_for(session_with(**PIN)) is None


def test_after_pin_bot_asks_landmark():
    assert reply_for(session_with(**PIN), 1500) == question_for_field("landmark_hi")


def test_set_field_advances_to_readback_when_last_field_arrives():
    session = session_with(**PIN, landmark_hi="Amer fort ke paas", consent_voice_clip=True)
    session.set_field("gate_photo_media_id", "m1")
    assert session.state == OnboardingState.READBACK


def test_photo_is_gate_photo_only_when_it_is_the_next_field():
    assert photo_kind(session_with(**PIN, landmark_hi="Amer fort ke paas")) == "gate_photo"
    assert photo_kind(session_with()) == "photo"


def test_every_pin_rejection_has_a_message():
    assert set(PIN_REJECTIONS) == {"venue", "forwarded", "too_far"}
