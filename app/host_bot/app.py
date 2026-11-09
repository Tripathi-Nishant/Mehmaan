from io import BytesIO

from sqlalchemy.ext.asyncio import AsyncSession
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from app.audio.convert import to_wav
from app.booking.host_reply import booking_reply, pending_booking_for
from app.config import Settings
from app.db.models import Host
from app.db.session import session_factory
from app.gnani.stt import SttError, transcribe
from app.gnani.tts import TtsError, synthesize
from app.gnani.usage import UsageGuard
from app.host_bot.intents import classify_reply
from app.host_bot.location import PIN_REJECTIONS, check_location_pin
from app.host_bot.onboarding import OnboardingSession
from app.host_bot.persistence import load_session, publish_listing, save_session
from app.host_bot.service import (
    decide_voice_action,
    keyboard_for,
    listing_copy,
    needs_yes_no,
    onboarding_gate,
    photo_kind,
    process_extracted_fields,
    question_for_field,
    reply_for,
    try_change,
)
from app.llm.client import LlmOutputError, extract_listing_fields
from app.media.store import MediaTooLargeError, save_media


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
        async with session_factory() as db:
            host, onboarding = await load_session(
                db, update.effective_user.id, update.effective_chat.id
            )
            # A pending booking is the open prompt and wins over onboarding (even when LIVE).
            pending = await pending_booking_for(db, host.id)
            # Else gate before STT so a host whose listing is LIVE doesn't spend a Gnani call.
            reply = None if pending else onboarding_gate(onboarding)
            if reply is None:
                telegram_file = await context.bot.get_file(update.message.voice.file_id)
                audio = await telegram_file.download_as_bytearray()
                wav = await to_wav(bytes(audio))
                said = (
                    await transcribe(
                        wav, "hi-IN", settings, UsageGuard(settings.gnani_daily_call_cap)
                    )
                ).transcript
                if pending:
                    reply = await booking_reply(db, pending, said, settings)
                else:
                    reply = await onboarding_reply(db, host, onboarding, said, settings)
        await send_host_voice_or_text(update, context, reply, keyboard_for(onboarding))
    except (SttError, OSError, RuntimeError):
        await update.message.reply_text("Awaaz saaf nahi aayi, kripya phir se bhejiye.")


async def onboarding_reply(
    db: AsyncSession, host: Host, onboarding: OnboardingSession, said: str, settings: Settings
) -> str:
    """Apply one host message (voice transcript or typed text) to onboarding; return the reply."""
    if blocked := onboarding_gate(onboarding):
        return blocked
    if try_change(onboarding, said):
        # Host named a field at read-back: it is cleared, so re-ask just that one.
        await save_session(db, host.id, onboarding)
        return reply_for(onboarding, settings.commission_bps)
    intent = None
    if needs_yes_no(onboarding.state, onboarding.next_field):
        intent = await classify_reply(said, settings)
    action = decide_voice_action(onboarding.state, onboarding.next_field, intent)
    if action == "publish":
        copy = await listing_copy(onboarding.fields, settings)
        await publish_listing(db, host.id, onboarding, "Telegram onboarding transcript", copy)
        reply = "Bahut badhiya! Aapka anubhav Mehmaan par LIVE ho gaya hai."
    elif action == "change":
        reply = "Kya badalna hai? Jaise daam, samay, din ya location boliye."
    elif action == "ask_again":
        reply = "Kripya haan ya nahi boliye. " + reply_for(onboarding, settings.commission_bps)
    elif action in ("consent_yes", "consent_no"):
        onboarding.set_field("consent_voice_clip", action == "consent_yes")
        reply = reply_for(onboarding, settings.commission_bps)
    elif action == "landmark":
        # Landmark is kept in the host's own words; no LLM extraction.
        onboarding.set_field("landmark_hi", said)
        reply = reply_for(onboarding, settings.commission_bps)
    else:
        extracted = await extract_listing_fields(said, settings)
        reply = process_extracted_fields(onboarding, extracted, settings.commission_bps)
    await save_session(db, host.id, onboarding)
    return reply


async def send_host_voice_or_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    reply_markup: ReplyKeyboardMarkup | None = None,
) -> None:
    settings: Settings = context.application.bot_data["settings"]
    try:
        audio = await synthesize(
            text, "hi-IN", settings, UsageGuard(settings.gnani_daily_call_cap, kind="tts")
        )
        await update.message.reply_voice(
            voice=BytesIO(audio), caption=text, reply_markup=reply_markup
        )
    except (TtsError, RuntimeError):
        await update.message.reply_text(text, reply_markup=reply_markup)


async def location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.location:
        return
    settings: Settings = context.application.bot_data["settings"]
    pin = update.message.location
    async with session_factory() as db:
        host, onboarding = await load_session(
            db, update.effective_user.id, update.effective_chat.id
        )
        if blocked := onboarding_gate(onboarding):
            await send_host_voice_or_text(update, context, blocked)
            return
        if not onboarding.fields.get("city"):
            # The distance check needs the city, so ask for it before accepting a pin.
            await send_host_voice_or_text(update, context, question_for_field("city"))
            return
        rejection = check_location_pin(
            lat=pin.latitude,
            lng=pin.longitude,
            city=onboarding.fields["city"],
            is_venue=update.message.venue is not None,
            is_forwarded=update.message.forward_origin is not None,
            max_km=settings.location_max_km_from_city,
        )
        if rejection:
            await send_host_voice_or_text(
                update, context, PIN_REJECTIONS[rejection], keyboard_for(onboarding)
            )
            return
        onboarding.fields["location_accuracy_m"] = pin.horizontal_accuracy
        onboarding.fields["location_lat"] = pin.latitude
        onboarding.set_field("location_lng", pin.longitude)
        await save_session(db, host.id, onboarding)
    await send_host_voice_or_text(
        update, context, reply_for(onboarding, settings.commission_bps), keyboard_for(onboarding)
    )


async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.photo:
        return
    settings: Settings = context.application.bot_data["settings"]
    telegram_file = await context.bot.get_file(update.message.photo[-1].file_id)
    data = bytes(await telegram_file.download_as_bytearray())
    async with session_factory() as db:
        host, onboarding = await load_session(
            db, update.effective_user.id, update.effective_chat.id
        )
        if blocked := onboarding_gate(onboarding):
            await send_host_voice_or_text(update, context, blocked)
            return
        kind = photo_kind(onboarding)
        try:
            media = await save_media(db, kind, "image/jpeg", data)
        except MediaTooLargeError:
            await update.message.reply_text("Photo bahut badi hai. Kripya chhoti photo bhejiye.")
            return
        if kind == "gate_photo":
            onboarding.set_field("gate_photo_media_id", str(media.id))
            reply = reply_for(onboarding, settings.commission_bps)
        else:
            onboarding.fields.setdefault("experience_photo_media_ids", []).append(str(media.id))
            reply = "Experience ki photo mil gayi, dhanyavaad."
        await save_session(db, host.id, onboarding)
    await send_host_voice_or_text(update, context, reply, keyboard_for(onboarding))


async def text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    settings: Settings = context.application.bot_data["settings"]
    said = update.message.text
    async with session_factory() as db:
        host, onboarding = await load_session(
            db, update.effective_user.id, update.effective_chat.id
        )
        try:
            if pending := await pending_booking_for(db, host.id):
                reply = await booking_reply(db, pending, said, settings)
            else:
                reply = await onboarding_reply(db, host, onboarding, said, settings)
        except LlmOutputError:
            reply = "Maaf kijiye, abhi samajh nahi paaye. Kripya thodi der baad phir bhejiye."
    await update.message.reply_text(reply, reply_markup=keyboard_for(onboarding))


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
