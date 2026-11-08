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
