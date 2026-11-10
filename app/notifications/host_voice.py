from io import BytesIO

from telegram import Bot

from app.audio.convert import to_telegram_voice
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
        audio = await to_telegram_voice(audio)
        await bot.send_voice(
            chat_id=chat_id,
            voice=BytesIO(audio),
            caption="TEST voice notification: booking request",
        )
    except (TtsError, RuntimeError):
        await bot.send_message(chat_id=chat_id, text=text)
