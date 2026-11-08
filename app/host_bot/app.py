from io import BytesIO

from sqlalchemy import select
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from app.audio.convert import to_wav
from app.booking.actions import host_accept
from app.config import Settings
from app.db.models import Booking, Host, Listing, Slot
from app.db.session import session_factory
from app.gnani.stt import SttError, transcribe
from app.gnani.tts import TtsError, synthesize
from app.gnani.usage import UsageGuard
from app.host_bot.intents import classify_intent
from app.host_bot.persistence import load_session, publish_listing, save_session
from app.host_bot.service import process_extracted_fields, question_for_field
from app.jobs.actions import decline_and_refund
from app.llm.client import extract_listing_fields
from app.media.store import save_media


async def start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text("Namaste! Mehmaan par apna anubhav awaaz mein bhejiye.")


async def unsupported(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text("Kripya apne anubhav ka voice note bhejiye.")


async def voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.voice:
        return
    settings: Settings = context.application.bot_data["settings"]
    try:
        telegram_file = await context.bot.get_file(update.message.voice.file_id)
        audio = await telegram_file.download_as_bytearray()
        wav = await to_wav(bytes(audio))
        result = await transcribe(wav, "hi-IN", settings, UsageGuard(settings.gnani_daily_call_cap))
        async with session_factory() as db:
            host, onboarding = await load_session(
                db, update.effective_user.id, update.effective_chat.id
            )
            extracted = await extract_listing_fields(result.transcript, settings)
            reply = process_extracted_fields(onboarding, extracted, settings.commission_bps)
            await save_session(db, host.id, onboarding)
        await send_host_voice_or_text(update, context, reply)
    except (SttError, OSError, RuntimeError):
        await update.message.reply_text("Awaaz saaf nahi aayi, kripya phir se bhejiye.")


async def send_host_voice_or_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE, text: str
) -> None:
    settings: Settings = context.application.bot_data["settings"]
    try:
        audio = await synthesize(
            text, "hi-IN", settings, UsageGuard(settings.gnani_daily_call_cap, kind="tts")
        )
        await update.message.reply_voice(voice=BytesIO(audio), caption=text)
    except (TtsError, RuntimeError):
        await update.message.reply_text(text)


async def location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.location:
        return
    if update.message.forward_origin is not None:
        await send_host_voice_or_text(
            update, context, "Kripya apne ghar se naya location pin bhejiye."
        )
        return
    async with session_factory() as db:
        host, onboarding = await load_session(
            db, update.effective_user.id, update.effective_chat.id
        )
        onboarding.fields["location_shared"] = True
        onboarding.fields["location_lat"] = update.message.location.latitude
        onboarding.fields["location_lng"] = update.message.location.longitude
        await save_session(db, host.id, onboarding)
    next_field = onboarding.missing_fields[0] if onboarding.missing_fields else "landmark"
    await send_host_voice_or_text(update, context, question_for_field(next_field))


async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.photo:
        return
    telegram_file = await context.bot.get_file(update.message.photo[-1].file_id)
    data = bytes(await telegram_file.download_as_bytearray())
    async with session_factory() as db:
        host, onboarding = await load_session(
            db, update.effective_user.id, update.effective_chat.id
        )
        media = await save_media(db, "photo", "image/jpeg", data)
        if "gate_photo_media_id" not in onboarding.fields:
            onboarding.fields["gate_photo_media_id"] = str(media.id)
            reply = "Gate ya door ki photo mil gayi. Ab experience ki photo bhejiye."
        else:
            photos = onboarding.fields.setdefault("experience_photo_media_ids", [])
            photos.append(str(media.id))
            reply = (
                "Experience ki photo mil gayi. Ab voice clip consent ke liye haan ya nahi bhejiye."
            )
        await save_session(db, host.id, onboarding)
    await send_host_voice_or_text(update, context, reply)


async def text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    intent = classify_intent(update.message.text).intent
    if intent not in {"YES", "NO"}:
        await update.message.reply_text("Kripya read-back ke baad haan ya badalna likhiye.")
        return
    async with session_factory() as db:
        host = await db.scalar(
            select(Host).where(Host.telegram_user_id == update.effective_user.id)
        )
        pending = None
        if host:
            pending = await db.scalar(
                select(Booking)
                .join(Slot, Booking.slot_id == Slot.id)
                .join(Listing, Slot.listing_id == Listing.id)
                .where(Listing.host_id == host.id, Booking.status == "PAID_PENDING_HOST")
                .order_by(Booking.created_at)
            )
        if pending:
            if intent == "YES":
                pending.status = host_accept(pending.status)
                await db.commit()
                await update.message.reply_text(
                    "Booking confirm ho gayi. Mehmaan ko pata chal gaya."
                )
            else:
                await decline_and_refund(db, pending)
                await update.message.reply_text("Booking decline aur test refund kar diya gaya.")
            return
        host, onboarding = await load_session(
            db, update.effective_user.id, update.effective_chat.id
        )
        if onboarding.state.value != "READBACK":
            await update.message.reply_text("Pehle apne anubhav ka voice note bhejiye.")
            return
        await publish_listing(db, host.id, onboarding, "Telegram onboarding transcript")
        await save_session(db, host.id, onboarding)
    await update.message.reply_text("Bahut badhiya! Aapka anubhav Mehmaan par LIVE ho gaya hai.")


def build_application(settings: Settings) -> Application:
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required to start the host bot")
    application = Application.builder().token(settings.telegram_bot_token).build()
    application.bot_data["settings"] = settings
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.VOICE, voice))
    application.add_handler(MessageHandler(filters.LOCATION, location))
    application.add_handler(MessageHandler(filters.PHOTO, photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))
    application.add_handler(MessageHandler(~filters.VOICE & ~filters.COMMAND, unsupported))
    return application
