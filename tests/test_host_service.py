from app.host_bot.onboarding import OnboardingSession
from app.host_bot.schemas import ListingFieldsUpdate
from app.host_bot.service import process_extracted_fields


def test_service_asks_one_follow_up():
    response = process_extracted_fields(
        OnboardingSession(), ListingFieldsUpdate(category="food"), commission_bps=1500
    )
    assert response == "Aap mehmaan ko kya karna sikhayengi?"
