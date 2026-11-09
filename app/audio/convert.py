import asyncio
import tempfile
from pathlib import Path


class AudioConversionError(RuntimeError):
    pass


async def to_wav(audio: bytes, source_suffix: str = ".ogg") -> bytes:
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / f"source{source_suffix}"
        target = Path(directory) / "audio.wav"
        source.write_bytes(audio)
        process = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-ar",
            "16000",
            "-ac",
            "1",
            str(target),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            raise AudioConversionError(stderr.decode(errors="replace"))
        return target.read_bytes()


async def to_telegram_voice(audio: bytes) -> bytes:
    """Normalize TTS output to Telegram's preferred OGG/Opus voice format."""
    with tempfile.TemporaryDirectory() as directory:
        # Timbre returns headerless signed 16-bit mono PCM, not a WAV container.
        source = Path(directory) / "source.pcm"
        target = Path(directory) / "voice.ogg"
        source.write_bytes(audio)
        process = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-y",
            "-f",
            "s16le",
            "-ar",
            "24000",
            "-ac",
            "1",
            "-i",
            str(source),
            "-vn",
            "-c:a",
            "libopus",
            "-b:a",
            "32k",
            "-ar",
            "48000",
            str(target),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            raise AudioConversionError(stderr.decode(errors="replace"))
        return target.read_bytes()
