from dataclasses import dataclass

import httpx

from app.config import Settings
from app.gnani.usage import UsageGuard


class SttError(RuntimeError):
    pass


@dataclass(frozen=True)
class SttResult:
    transcript: str


async def transcribe(
    audio: bytes, language: str, settings: Settings, usage: UsageGuard
) -> SttResult:
    usage.consume()
    headers = {"X-API-Key-ID": settings.gnani_api_key}
    files = {"audio_file": ("audio.wav", audio, "audio/wav")}
    data = {"language_code": language, "model": settings.gnani_stt_model}
    try:
        async with httpx.AsyncClient(base_url=settings.gnani_base_url, timeout=30) as client:
            response = await client.post("/stt/v3", headers=headers, files=files, data=data)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise SttError("Gnani Prisma transcription failed") from exc
    transcript = payload.get("transcript", "").strip()
    if not transcript:
        raise SttError("Gnani Prisma returned an empty transcript")
    return SttResult(transcript=transcript)
