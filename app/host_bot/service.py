from collections.abc import Mapping

from app.host_bot.onboarding import OnboardingSession
from app.host_bot.readback import render_readback
from app.host_bot.schemas import ListingFieldsUpdate


def process_extracted_fields(
    session: OnboardingSession, extracted: ListingFieldsUpdate, commission_bps: int
) -> str:
    session.merge(extracted)
    if session.state.value == "ABANDONED":
        return "Bahut der ho gayi. Kripya baad mein phir se shuru kijiye."
    if session.state.value == "READBACK":
        return render_readback(session.fields, commission_bps)
    next_field = session.missing_fields[0]
    return question_for_field(next_field)


def question_for_field(field_name: str) -> str:
    questions: Mapping[str, str] = {
        "category": "Aapka anubhav khane, kala ya sangeet mein hai?",
        "activity_description": "Aap mehmaan ko kya karna sikhayengi?",
        "duration_min": "Yeh anubhav kitne minute ka hoga?",
        "max_guests": "Ek baar mein kitne mehmaan aa sakte hain?",
        "price_per_person_paise": "Prati mehmaan aapka daam kitna hoga?",
        "city": "Aap kis shehar mein hain?",
        "area": "Shehar ke kis ilaake mein hain?",
        "available_weekdays": "Aap kaunse din mehmaan bula sakti hain?",
        "start_time_local": "Anubhav kis samay shuru hoga?",
        "food_type": "Khana shakahari hai ya maansahari?",
        "location_shared": "Kripya isi ghar se Telegram location pin bhejiye.",
        "landmark": "Aapke ghar ke paas koi pehchaan ki jagah ya landmark kya hai?",
        "consent_voice_clip": "Kya aapki awaaz website par dikhayi ja sakti hai? Haan ya nahi.",
        "cancellation_rule": "Mehmaan booking cancel kare to aapka niyam kya hoga?",
    }
    return questions[field_name]
