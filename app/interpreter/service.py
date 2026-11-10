from app.config import Settings
from app.llm.client import complete_text

# Text translation for guests: every pair is guest language <-> Hindi.
LANGUAGES = {
    "en": "English",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "it": "Italian",
    "ja": "Japanese",
    "hi": "Hindi",
}


def translation_prompt(text: str, source: str, target: str) -> str:
    return (
        f"Translate from {LANGUAGES[source]} to {LANGUAGES[target]} for a guest and a host "
        "talking in a family home. Keep it warm and simple. Preserve names, dish names, craft "
        f"names and all numbers exactly. Return only the translation. Text: {text}"
    )


async def translate_between(text: str, source: str, target: str, settings: Settings) -> str:
    return await complete_text(translation_prompt(text, source, target), settings)


def languages_for_speaker(speaker: str) -> tuple[str, str]:
    if speaker == "host":
        return "hi-IN", "en-IN"
    if speaker == "traveler":
        return "en-IN", "hi-IN"
    raise ValueError("speaker must be host or traveler")


async def translate_text(text: str, speaker: str, settings: Settings) -> str:
    source, target = languages_for_speaker(speaker)
    prompt = (
        f"Translate from {source} to {target}. Preserve names, dish names, craft names, "
        f"and all numbers exactly. Return only the translation. Text: {text}"
    )
    return await complete_text(prompt, settings)
