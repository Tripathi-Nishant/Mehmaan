from app.config import Settings
from app.host_bot.schemas import IntentResult
from app.llm.client import LlmOutputError, complete_text

YES_PHRASES = {
    "haan", "ha", "haa", "yes", "ji", "ji haan", "haan ji", "ha ji", "theek hai", "thik hai",
    "sahi hai", "bilkul", "हाँ", "हां", "जी", "जी हाँ", "जी हां", "हाँ जी", "हां जी", "ठीक है",
    "सही है",
}  # fmt: skip
NO_PHRASES = {
    "nahi", "nahin", "no", "ji nahi", "galat", "galat hai", "नहीं", "ना", "जी नहीं", "गलत",
    "गलत है",
}  # fmt: skip
_PUNCTUATION = str.maketrans("", "", ".,!?।")

YES_NO_PROMPT = (
    "A host in India replied to a yes/no question in Hindi or Hinglish. "
    "Answer with exactly one word: YES, NO, or UNCLEAR. Reply: {text}"
)


# Words a host uses to name what to change at the read-back -> fields to clear.
CHANGE_KEYWORDS: dict[tuple[str, ...], set[str]] = {
    ("price_per_person_paise",): {"daam", "keemat", "kimat", "price", "rupaye", "दाम", "कीमत"},
    ("start_time_local",): {"samay", "time", "waqt", "baje", "समय", "टाइम", "बजे"},
    ("available_weekdays",): {"din", "day", "days", "दिन"},
    ("duration_min",): {"ghante", "ghanta", "minute", "duration", "घंटे", "घंटा"},
    ("max_guests",): {"mehmaan", "guest", "guests", "log", "मेहमान", "लोग"},
    ("city",): {"shehar", "sheher", "city", "शहर"},
    ("area",): {"ilaaka", "ilaka", "area", "mohalla", "इलाका", "मोहल्ला"},
    ("activity_description",): {"anubhav", "activity", "description", "अनुभव"},
    ("category",): {"category", "shreni", "श्रेणी"},
    ("food_type",): {"veg", "nonveg", "shakahari", "maansahari", "शाकाहारी", "मांसाहारी"},
    ("location_lat", "location_lng"): {"location", "pin", "lokesan", "लोकेशन"},
    ("landmark_hi",): {"landmark", "pehchaan", "लैंडमार्क", "पहचान"},
    ("gate_photo_media_id",): {"photo", "gate", "darwaza", "फोटो", "गेट"},
    ("consent_voice_clip",): {"awaaz", "voice", "आवाज़", "आवाज"},
}  # fmt: skip


def _normalize(text: str) -> str:
    return " ".join(text.lower().translate(_PUNCTUATION).split())


def fields_to_change(text: str) -> tuple[str, ...] | None:
    """First field group the host names, matching whole words only (so "din" != "dinner")."""
    for word in _normalize(text).split():
        for fields, keywords in CHANGE_KEYWORDS.items():
            if word in keywords:
                return fields
    return None


def classify_intent(text: str) -> IntentResult:
    normalized = _normalize(text)
    if normalized in YES_PHRASES:
        return IntentResult(intent="YES")
    if normalized in NO_PHRASES:
        return IntentResult(intent="NO")
    if "paisa" in normalized or "payment" in normalized or "पैसा" in normalized:
        return IntentResult(intent="PAYOUT_QUERY")
    if any(word in normalized for word in ("badal", "change", "गलत", "बदल")):
        return IntentResult(intent="CHANGE")
    if any(word in normalized for word in ("listing", "experience", "अनुभव", "काम")):
        return IntentResult(intent="NEW_LISTING")
    return IntentResult(intent="UNCLEAR")


async def classify_reply(text: str, settings: Settings) -> str:
    """YES / NO / CHANGE / UNCLEAR for a reply to a yes/no question. Never raises on LLM failure."""
    intent = classify_intent(text).intent
    if intent in {"YES", "NO", "CHANGE"}:
        return intent
    try:
        answer = await complete_text(YES_NO_PROMPT.format(text=text), settings)
    except LlmOutputError:
        return "UNCLEAR"
    answer = answer.strip().strip(".").upper()
    return answer if answer in {"YES", "NO"} else "UNCLEAR"
