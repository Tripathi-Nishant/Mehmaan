import re
from collections.abc import Mapping
from datetime import datetime

from telegram import KeyboardButton, ReplyKeyboardMarkup

from app.booking.slots import format_ist
from app.host_bot.intents import classify_intent, fields_to_change
from app.host_bot.onboarding import OnboardingSession, OnboardingState
from app.host_bot.readback import format_rupees, render_readback
from app.host_bot.schemas import ListingFieldsUpdate
from app.llm.client import LlmOutputError, generate_listing_copy
from app.llm.schemas import ListingCopy

# Only descriptive facts go to the LLM; coordinates and the gate photo never leave the server.
COPY_FACTS = (
    "category",
    "activity_description",
    "food_type",
    "duration_min",
    "max_guests",
    "city",
    "area",
    "landmark_hi",
)
FOOD_TYPE_EN = {"veg": "vegetarian", "non-veg": "non-vegetarian"}

LOCATION_KEYBOARD = ReplyKeyboardMarkup(
    [[KeyboardButton("📍 Location bhejiye", request_location=True)]],
    resize_keyboard=True,
    one_time_keyboard=True,
)


def process_extracted_fields(
    session: OnboardingSession, extracted: ListingFieldsUpdate, commission_bps: int
) -> str:
    # Prisma/LLM can occasionally hear "pottery" as "poetry". Keep the
    # host's intended craft experience and its image mapping intact.
    if extracted.activity_description:
        extracted.activity_description = re.sub(
            r"\bpoet+ry\b|\bpotery\b",
            "pottery",
            extracted.activity_description,
            flags=re.IGNORECASE,
        )
    session.merge(extracted)
    return reply_for(session, commission_bps)


def reply_for(session: OnboardingSession, commission_bps: int) -> str:
    if session.state.value == "ABANDONED":
        return "Bahut der ho gayi. Kripya baad mein phir se shuru kijiye."
    if session.state.value == "READBACK":
        return render_readback(session.fields, commission_bps)
    return question_for_field(session.next_field)


async def listing_copy(fields: Mapping, settings) -> ListingCopy:
    """English title/description/landmark from the LLM; template fallback if it fails."""
    facts = {name: fields.get(name) for name in COPY_FACTS}
    try:
        copy = await generate_listing_copy(facts, settings)
    except LlmOutputError:
        return fallback_copy(fields)
    return copy.model_copy(update={"landmark_en": copy.landmark_en or fields.get("landmark_hi")})


def fallback_copy(fields: Mapping) -> ListingCopy:
    category = str(fields["category"])
    place = f"{fields['area']}, {fields['city']}"
    food = FOOD_TYPE_EN.get(str(fields.get("food_type")))
    description = (
        f"A {fields['duration_min']}-minute {category} experience at a local host's home in "
        f"{place}. " + (f"The food is {food}. " if food else "") + f"Up to "
        f"{fields['max_guests']} guests. In the host's words: {fields['activity_description']}."
    )
    return ListingCopy(
        title_en=f"{category.title()} experience in {place}",
        description_en=description,
        landmark_en=fields.get("landmark_hi"),
    )


def booking_prompt_text(
    starts_at: datetime, guests: int, host_payout_paise: int, dietary_notes: str | None = None
) -> str:
    # ponytail: the guest's note is passed through in their words; LLM translation to Hindi is v2.
    note = f'Mehmaan ne khaane ke baare mein bataya: "{dietary_notes}". ' if dietary_notes else ""
    return (
        f"{format_ist(starts_at)} ke liye {guests} mehmaan ki booking aayi hai. "
        f"Aapko {format_rupees(host_payout_paise)} milenge (test). {note}Haan ya nahi?"
    )


def cancel_note_text(starts_at: datetime, host_keep_paise: int) -> str:
    when = format_ist(starts_at)
    if host_keep_paise:
        return (
            f"{when} wali booking mehmaan ne cancel kar di. "
            f"Aapko {format_rupees(host_keep_paise)} milenge (test)."
        )
    return f"{when} wali booking cancel ho gayi."


def route_host_reply(has_pending: bool, intent: str) -> str:
    """Demo scope: a host has at most one PAID_PENDING_HOST booking, and it is the open
    prompt. confirm / decline / ask_again, or onboarding when nothing is pending."""
    if not has_pending:
        return "onboarding"
    return {"YES": "confirm", "NO": "decline"}.get(intent, "ask_again")


ALREADY_LIVE = "Aapka anubhav pehle se website pe hai."


def onboarding_gate(session: OnboardingSession) -> str | None:
    """One listing per host. DONE -> fixed reply (session untouched).
    ABANDONED -> reset to a fresh session so this message starts over. Else -> None."""
    if session.state == OnboardingState.DONE:
        return ALREADY_LIVE
    if session.state == OnboardingState.ABANDONED:
        session.fields = {}
        session.state = OnboardingState.COLLECTING
        session.turn_count = 0
    return None


def try_change(session: OnboardingSession, said: str) -> bool:
    """At read-back, reopen the field(s) the host names. Exact "haan" never counts as a change."""
    if session.state != OnboardingState.READBACK or classify_intent(said).intent == "YES":
        return False
    fields = fields_to_change(said)
    if not fields:
        return False
    for name in fields:
        session.change(name)
    return True


def needs_yes_no(state: OnboardingState, next_field: str | None) -> bool:
    return state == OnboardingState.READBACK or next_field == "consent_voice_clip"


def decide_voice_action(state: OnboardingState, next_field: str | None, intent: str | None) -> str:
    """What to do with a host voice note: publish / change / consent_yes / consent_no /
    ask_again / landmark / extract. `intent` is only needed when needs_yes_no() is true."""
    if state == OnboardingState.READBACK:
        return {"YES": "publish", "NO": "change", "CHANGE": "change"}.get(intent, "ask_again")
    if next_field == "consent_voice_clip":
        return {"YES": "consent_yes", "NO": "consent_no"}.get(intent, "ask_again")
    if next_field == "landmark_hi":
        return "landmark"
    return "extract"


def keyboard_for(session: OnboardingSession) -> ReplyKeyboardMarkup | None:
    return LOCATION_KEYBOARD if session.next_field in ("location_lat", "location_lng") else None


def photo_kind(session: OnboardingSession) -> str:
    # gate_photo is private: /media only serves "photo" and consented "audio".
    return "gate_photo" if session.next_field == "gate_photo_media_id" else "photo"


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
        "location_lat": "Kripya ghar par rehkar neeche wala 'Location bhejiye' button dabaiye.",
        "location_lng": "Kripya ghar par rehkar neeche wala 'Location bhejiye' button dabaiye.",
        "landmark_hi": "Mehmaan aapka ghar kaise pehchanenge? Paas ka landmark bata dijiye.",
        "gate_photo_media_id": (
            "Ghar ke gate ya darwaze ki ek photo bhejiye. Yeh sirf booking confirm hone par "
            "mehmaan ki madad ke liye hai, website par nahi dikhegi."
        ),
        "consent_voice_clip": "Kya aapki awaaz website par dikhayi ja sakti hai? Haan ya nahi.",
    }
    return questions[field_name]
