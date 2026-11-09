from app.host_bot.onboarding import OnboardingSession, OnboardingState
from app.host_bot.service import ALREADY_LIVE, onboarding_gate


def test_done_host_gets_already_live_and_session_is_untouched():
    session = OnboardingSession(fields={"city": "Jaipur"}, state=OnboardingState.DONE)
    assert onboarding_gate(session) == ALREADY_LIVE
    assert session.state == OnboardingState.DONE
    assert session.fields == {"city": "Jaipur"}


def test_abandoned_host_restarts_with_fresh_session():
    session = OnboardingSession(
        fields={"city": "Jaipur"}, state=OnboardingState.ABANDONED, turn_count=12
    )
    assert onboarding_gate(session) is None
    assert session.state == OnboardingState.COLLECTING
    assert session.fields == {}
    assert session.turn_count == 0


def test_collecting_host_passes_through_unchanged():
    session = OnboardingSession(fields={"city": "Jaipur"}, turn_count=3)
    assert onboarding_gate(session) is None
    assert session.fields == {"city": "Jaipur"} and session.turn_count == 3
