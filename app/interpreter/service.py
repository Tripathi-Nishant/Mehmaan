from app.config import Settings
from app.llm.client import complete_text


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
