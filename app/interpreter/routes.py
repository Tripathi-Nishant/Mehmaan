import base64
from time import perf_counter

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.audio.convert import to_wav
from app.config import get_settings
from app.gnani.stt import SttError, transcribe
from app.gnani.tts import synthesize
from app.gnani.usage import UsageGuard
from app.interpreter.service import languages_for_speaker, translate_text

router = APIRouter()


@router.post("/interpreter/{access_token}/turn")
async def interpreter_turn(
    access_token: str,
    speaker: str,
    audio: UploadFile = File(...),  # noqa: B008
):
    del access_token
    settings = get_settings()
    try:
        source_language, target_language = languages_for_speaker(speaker)
        wav = await to_wav(await audio.read(), ".webm")
        started = perf_counter()
        usage = UsageGuard(settings.gnani_daily_call_cap)
        result = await transcribe(wav, source_language, settings, usage)
        translated = await translate_text(result.transcript, speaker, settings)
        audio_bytes = await synthesize(translated, target_language, settings, usage)
    except (ValueError, SttError, OSError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail="voice turn could not be processed") from exc
    return {
        "source_text": result.transcript,
        "translated_text": translated,
        "target_language": target_language,
        "audio_b64": base64.b64encode(audio_bytes).decode(),
        "latency_ms": round((perf_counter() - started) * 1000),
    }
