import httpx

from app.config import Settings
from app.gnani.usage import UsageGuard


class TtsError(RuntimeError):
    pass


async def synthesize(text: str, language: str, settings: Settings, usage: UsageGuard) -> bytes:
    usage.consume()
    voice = settings.gnani_tts_voice_hi if language == "hi-IN" else settings.gnani_tts_voice_en
    payload = {
        "text": text,
        "model": settings.gnani_tts_model,
        "language": language,
        "voice": voice,
    }
    headers = {"X-API-Key-ID": settings.gnani_api_key}
    try:
        async with httpx.AsyncClient(base_url=settings.gnani_base_url, timeout=20) as client:
            response = await client.post("/api/v1/tts/inference", headers=headers, json=payload)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise TtsError("Gnani Timbre synthesis failed") from exc
    return response.content
