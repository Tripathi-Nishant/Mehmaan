import asyncio
import sys
from pathlib import Path

from app.config import get_settings
from app.gnani.stt import transcribe
from app.gnani.tts import synthesize
from app.gnani.usage import UsageGuard


async def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: uv run python scripts/smoke_gnani.py path/to/audio.wav")
        return 2
    audio_path = Path(sys.argv[1])
    settings = get_settings()
    usage = UsageGuard(settings.gnani_daily_call_cap)
    audio = await asyncio.to_thread(audio_path.read_bytes)
    result = await transcribe(audio, "hi-IN", settings, usage)
    print(f"Transcript: {result.transcript}")
    output = await synthesize("Mehmaan mein aapka swagat hai.", "hi-IN", settings, usage)
    await asyncio.to_thread(Path("smoke_timbre_output.bin").write_bytes, output)
    print("Wrote smoke_timbre_output.bin")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
