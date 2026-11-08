from io import BytesIO

from telegram import Bot

from app.config import Settings
from app.gnani.tts import TtsError, synthesize
from app.gnani.usage import UsageGuard


async def send_host_message(
    bot: Bot, chat_id: int, text: str, settings: Settings, language: str = "hi-IN"
) -> None:
    try:
        audio = await synthesize(
            text, language, settings, UsageGuard(settings.gnani_daily_call_cap)
        )
        await bot.send_voice(
            chat_id=chat_id, voice=BytesIO(audio), caption="TEST voice notification"
        )
    except (TtsError, RuntimeError):
        await bot.send_message(chat_id=chat_id, text=text)
