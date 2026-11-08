from app.host_bot.schemas import IntentResult


def classify_intent(text: str) -> IntentResult:
    normalized = " ".join(text.lower().strip().split())
    if normalized in {"haan", "ha", "yes", "ji haan", "ठीक है", "हाँ"}:
        return IntentResult(intent="YES")
    if normalized in {"nahi", "nahin", "no", "नहीं", "ना"}:
        return IntentResult(intent="NO")
    if "paisa" in normalized or "payment" in normalized or "पैसा" in normalized:
        return IntentResult(intent="PAYOUT_QUERY")
    if any(word in normalized for word in ("badal", "change", "गलत", "बदल")):
        return IntentResult(intent="CHANGE")
    if any(word in normalized for word in ("listing", "experience", "अनुभव", "काम")):
        return IntentResult(intent="NEW_LISTING")
    return IntentResult(intent="UNCLEAR")
