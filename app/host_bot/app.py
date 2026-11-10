import asyncio
from io import BytesIO

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import InputFile, ReplyKeyboardMarkup, Update
from telegram.error import NetworkError, TimedOut
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.request import HTTPXRequest

from app.audio.convert import to_telegram_voice, to_wav
from app.booking.host_reply import booking_reply, pending_booking_for
from app.config import Settings
from app.db.models import Booking, Host, Listing, Payout, Slot
from app.db.session import session_factory
from app.gnani.stt import SttError, transcribe
from app.gnani.tts import TtsError, synthesize
from app.gnani.usage import UsageGuard
from app.host_bot.intents import classify_reply
from app.host_bot.location import PIN_REJECTIONS, check_location_pin
from app.host_bot.onboarding import OnboardingSession, OnboardingState
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
        await send_host_voice_or_text(
            update,
            _,
            "Namaste! Main Mehmaan Host Assistant hoon. Aap Hindi ya Hinglish mein voice note "
            "bhejkar cooking, craft, music ya local experience list kar sakti hain. Main ek-ek "
            "sawaal poochungi: anubhav, din, samay, duration, mehmaan, daam, city, location pin "
            "aur photos. Booking ka jawab bhi haan ya nahi mein de sakti hain. Shuru karne ke "
            "liye apne experience ke baare mein voice note bhejiye.",
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await send_host_voice_or_text(
            update,
            context,
            "Aap voice note bhejkar apna experience list kar sakti hain. Location ke liye Telegram "
            "ka live location pin, phir gate aur experience ki photos bhejiye. Booking par haan ya "
            "nahi boliye. Nayi listing ke liye /newlisting bhejiye.",
        )


async def new_listing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        async with session_factory() as db:
            host, onboarding = await load_session(
                db, update.effective_user.id, update.effective_chat.id
            )
            onboarding.fields = {}
            onboarding.state = OnboardingState.COLLECTING
            onboarding.turn_count = 0
            await save_session(db, host.id, onboarding)
        await send_host_voice_or_text(
            update,
            context,
            "Theek hai. Apne experience ke baare mein voice note bhejiye. Jaise: main ghar par "
            "Rajasthani dal baati churma banati hoon.",
        )


async def my_listings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    async with session_factory() as db:
        host = await db.scalar(
            select(Host).where(Host.telegram_user_id == update.effective_user.id)
        )
        listings = (
            await db.scalars(select(Listing).where(Listing.host_id == host.id))
            if host
            else []
        )
        rows = list(listings)
    if not rows:
        reply = "Aapki abhi koi listing nahi hai. /newlisting bhejkar shuru kijiye."
    else:
        reply = "Aapki listings: " + "; ".join(
            f"{item.title_en or item.category} — {item.status}" for item in rows
        )
    await send_host_voice_or_text(update, context, reply)


async def bookings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    async with session_factory() as db:
        host = await db.scalar(
            select(Host).where(Host.telegram_user_id == update.effective_user.id)
        )
        rows = []
        if host:
            rows = list(
                await db.scalars(
                    select(Booking)
                    .join(Slot, Booking.slot_id == Slot.id)
                    .join(Listing, Slot.listing_id == Listing.id)
                    .where(Listing.host_id == host.id)
                    .order_by(Booking.created_at.desc())
                    .limit(10)
                )
            )
    if not rows:
        reply = "Abhi koi booking request nahi hai."
    else:
        reply = "Bookings: " + "; ".join(
            f"{item.status}, {item.guests} mehmaan, {item.host_payout_paise // 100} rupaye payout"
            for item in rows
        )
    await send_host_voice_or_text(update, context, reply)


async def payout_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    async with session_factory() as db:
        host = await db.scalar(
            select(Host).where(Host.telegram_user_id == update.effective_user.id)
        )
        rows = list(
            await db.scalars(select(Payout).where(Payout.host_id == host.id))
        ) if host else []
    if not rows:
        reply = "Abhi koi payout scheduled nahi hai."
    else:
        reply = "Payouts: " + "; ".join(
            f"{item.amount_paise // 100} rupaye — {item.status}" for item in rows
        )
    await send_host_voice_or_text(update, context, reply)


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
        voice_audio = await to_telegram_voice(audio)
        await update.message.reply_voice(
            voice=InputFile(BytesIO(voice_audio), filename="mehmaan-reply.ogg"),
            caption=text,
            reply_markup=reply_markup,
        )
    except (TtsError, RuntimeError):
        await update.message.reply_text(text, reply_markup=reply_markup)


async def download_telegram_bytes(context: ContextTypes.DEFAULT_TYPE, file_id: str) -> bytes:
    """Download Telegram media with retries for slow Bot API file responses."""
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            telegram_file = await context.bot.get_file(file_id, read_timeout=300)
            return bytes(
                await telegram_file.download_as_bytearray(
                    read_timeout=300,
                    write_timeout=300,
                    connect_timeout=60,
                    pool_timeout=60,
                )
            )
        except (TimedOut, NetworkError) as exc:
            last_error = exc
            if attempt < 2:
                await asyncio.sleep(2 * (attempt + 1))
    raise RuntimeError("Telegram media download failed") from last_error


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
    try:
        data = await download_telegram_bytes(context, update.message.photo[-1].file_id)
    except RuntimeError:
        await update.message.reply_text(
            "Photo download nahi ho paayi. Kripya photo dobara bhejiye."
        )
        return
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
    # Voice replies can be larger than normal Telegram messages.  Keep the
    # polling timeout short, but allow enough time to upload generated audio.
    telegram_request = HTTPXRequest(
        connection_pool_size=10,
        connect_timeout=30.0,
        read_timeout=300.0,
        write_timeout=120.0,
        pool_timeout=30.0,
        media_write_timeout=300.0,
    )
    application = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .request(telegram_request)
        .build()
    )
    application.bot_data["settings"] = settings
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("newlisting", new_listing))
    application.add_handler(CommandHandler("mylistings", my_listings))
    application.add_handler(CommandHandler("bookings", bookings_command))
    application.add_handler(CommandHandler("payout", payout_command))
    application.add_handler(MessageHandler(filters.VOICE, voice))
    application.add_handler(MessageHandler(filters.LOCATION, location))
    application.add_handler(MessageHandler(filters.PHOTO, photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))
    application.add_handler(MessageHandler(~filters.VOICE & ~filters.COMMAND, unsupported))
    return application
