from contextlib import suppress
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_user
from app.booking.actions import HoldExpiredError, capture_payment, expire_hold
from app.booking.db_service import CANCELLABLE, SlotFullError, cancel_booking, create_hold
from app.booking.host_reply import location_reveal
from app.booking.policy import NotCancellableError, cancellation_split
from app.booking.slots import format_ist
from app.booking.states import InvalidTransitionError
from app.config import get_settings
from app.db.models import Booking, Host, LedgerEntry, Listing, Payment, Review, Slot, Traveler
from app.db.session import get_session
from app.host_bot.service import booking_prompt_text, cancel_note_text
from app.interpreter.service import LANGUAGES, translate_between
from app.llm.client import LlmOutputError
from app.notifications.email import enqueue_booking_email
from app.notifications.host_voice import send_host_message
from app.payments.mock_provider import MockProvider

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")
templates.env.filters["ist"] = format_ist


@router.post("/book")
async def book(
    request: Request,
    slot_id: UUID = Form(),  # noqa: B008
    name: str = Form(),
    email: str = Form(),
    phone: str = Form(default="", max_length=40),
    guests: int = Form(),
    dietary: str = Form(default="", max_length=200),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> RedirectResponse:
    settings = get_settings()
    user = await current_user(request, session)
    try:
        booking = await create_hold(
            session,
            slot_id,
            name,
            email,
            guests,
            settings.hold_minutes,
            datetime.now(UTC),
            dietary,
            user.id if user and user.role == "traveler" else None,
            phone,
        )
    except SlotFullError as exc:
        raise HTTPException(
            status_code=409, detail="That date just filled up. Please choose another date."
        ) from exc
    provider = MockProvider(settings.mock_payment_secret)
    order_id = provider.create_order()
    session.add(
        Payment(
            booking_id=booking.id, provider_order_id=order_id, amount_paise=booking.amount_paise
        )
    )
    await session.commit()
    return RedirectResponse(f"/pay/mock/{order_id}", status_code=303)


@router.get("/pay/mock/{order_id}", response_class=HTMLResponse)
async def mock_checkout(
    request: Request,
    order_id: str,
    session: AsyncSession = Depends(get_session),  # noqa: B008
):  # noqa: B008
    payment = await session.scalar(select(Payment).where(Payment.provider_order_id == order_id))
    if payment is None:
        raise HTTPException(status_code=404, detail="order not found")
    booking = await session.get(Booking, payment.booking_id)
    slot = await session.get(Slot, booking.slot_id)
    return templates.TemplateResponse(
        request=request,
        name="payment.html",
        context={
            "payment": payment,
            "booking": booking,
            "slot": slot,
            "listing": await session.get(Listing, slot.listing_id),
            "traveler": await session.get(Traveler, booking.traveler_id),
        },
    )


@router.post("/pay/mock/{order_id}/verify")
async def verify_payment(order_id: str, session: AsyncSession = Depends(get_session)):  # noqa: B008
    # Row locks: a double-click or the hold-expiry job can't interleave with this capture.
    payment = await session.scalar(
        select(Payment).where(Payment.provider_order_id == order_id).with_for_update()
    )
    if payment is None:
        raise HTTPException(status_code=404, detail="order not found")
    provider = MockProvider(get_settings().mock_payment_secret)
    result = provider.pay(order_id)
    if not provider.verify(result):
        raise HTTPException(status_code=400, detail="invalid payment signature")
    captured_now = payment.status != "CAPTURED"
    if captured_now:
        booking = await session.scalar(
            select(Booking).where(Booking.id == payment.booking_id).with_for_update()
        )
        now = datetime.now(UTC)
        try:
            capture = capture_payment(
                booking.status,
                booking.amount_paise,
                get_settings().commission_bps,
                hold_expires_at=booking.hold_expires_at,
                now=now,
            )
        except (InvalidTransitionError, HoldExpiredError) as exc:
            # Nothing is written: the session rolls back, payment stays CREATED.
            raise HTTPException(
                status_code=409,
                detail="This booking hold has expired. Please choose a date and book again.",
            ) from exc
        payment.provider_payment_id = result.payment_id
        payment.status = "CAPTURED"
        if booking:
            booking.status = capture.status.value
            booking.host_reply_deadline = now + timedelta(
                minutes=get_settings().host_reply_timeout_minutes
            )
            split = capture.ledger
            booking.commission_paise = split.commission
            booking.host_payout_paise = split.host_payable
            slot = await session.get(Slot, booking.slot_id)
            listing = await session.get(Listing, slot.listing_id) if slot else None
            session.add_all(
                [
                    LedgerEntry(
                        booking_id=booking.id,
                        host_id=listing.host_id if listing else None,
                        type="CHARGE",
                        amount_paise=split.charge,
                    ),
                    LedgerEntry(
                        booking_id=booking.id,
                        host_id=listing.host_id if listing else None,
                        type="COMMISSION",
                        amount_paise=-split.commission,
                    ),
                    LedgerEntry(
                        booking_id=booking.id,
                        host_id=listing.host_id if listing else None,
                        type="HOST_PAYABLE",
                        amount_paise=-split.host_payable,
                    ),
                ]
            )
            await enqueue_booking_email(session, booking, "BOOKING_RECEIVED")
        await session.commit()
    booking = await session.get(Booking, payment.booking_id)
    if captured_now and booking:
        slot = await session.get(Slot, booking.slot_id)
        traveler = await session.get(Traveler, booking.traveler_id)
        with suppress(Exception):
            await notify_host(
                session,
                booking,
                booking_prompt_text(
                    slot.starts_at,
                    booking.guests,
                    booking.host_payout_paise,
                    booking.dietary_notes,
                    traveler.name if traveler else None,
                    traveler.phone if traveler else None,
                ),
            )
    return RedirectResponse(f"/b/{booking.access_token}", status_code=303)


async def notify_host(session: AsyncSession, booking: Booking, text: str) -> None:
    """Voice note (text fallback) to the booking's host. No-op without a bot token."""
    if not get_settings().telegram_bot_token:
        return
    slot = await session.get(Slot, booking.slot_id)
    listing = await session.get(Listing, slot.listing_id) if slot else None
    host = await session.get(Host, listing.host_id) if listing else None
    if host:
        from telegram import Bot

        async with Bot(get_settings().telegram_bot_token) as bot:
            await send_host_message(bot, host.telegram_chat_id, text, get_settings())


@router.post("/pay/mock/{order_id}/fail")
async def fail_payment(order_id: str, session: AsyncSession = Depends(get_session)):  # noqa: B008
    """TEST decline: payment FAILED, hold EXPIRED, seats released now (not after 15 min)."""
    payment = await session.scalar(
        select(Payment).where(Payment.provider_order_id == order_id).with_for_update()
    )
    if payment is None:
        raise HTTPException(status_code=404, detail="order not found")
    if payment.status not in ("CREATED", "FAILED"):
        raise HTTPException(status_code=409, detail="this payment was already completed")
    booking = await session.scalar(
        select(Booking).where(Booking.id == payment.booking_id).with_for_update()
    )
    slot = await session.scalar(select(Slot).where(Slot.id == booking.slot_id).with_for_update())
    if payment.status == "CREATED":
        payment.status = "FAILED"
        if booking.status == "HELD":  # else the expiry job already released the seats
            expire_hold(booking, slot)
        await session.commit()
    return RedirectResponse(f"/listings/{slot.listing_id}?payment=failed", status_code=303)


@router.get("/b/{access_token}", response_class=HTMLResponse)
async def booking_page(
    request: Request,
    access_token: str,
    session: AsyncSession = Depends(get_session),  # noqa: B008
):  # noqa: B008
    booking = await session.scalar(select(Booking).where(Booking.access_token == access_token))
    if booking is None:
        raise HTTPException(status_code=404, detail="booking not found")
    slot = await session.get(Slot, booking.slot_id)
    listing = await session.get(Listing, slot.listing_id) if slot else None
    return templates.TemplateResponse(
        request=request,
        name="booking.html",
        context={
            "booking": booking,
            "listing": listing,
            "slot": slot,
            "host": await session.get(Host, listing.host_id) if listing else None,
            "traveler": await session.get(Traveler, booking.traveler_id),
            "location": location_reveal(booking, listing),
            "cancellable": booking.status in CANCELLABLE and slot.starts_at > datetime.now(UTC),
        },
    )


@router.get("/b/{access_token}/cancel", response_class=HTMLResponse)
async def cancel_preview(
    request: Request,
    access_token: str,
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    booking = await session.scalar(select(Booking).where(Booking.access_token == access_token))
    if booking is None:
        raise HTTPException(status_code=404, detail="booking not found")
    slot = await session.get(Slot, booking.slot_id)
    listing = await session.get(Listing, slot.listing_id)
    try:
        if booking.status not in CANCELLABLE:
            raise NotCancellableError(booking.status)
        refund, keep = cancellation_split(booking.amount_paise, slot.starts_at, datetime.now(UTC))
    except NotCancellableError as exc:
        raise HTTPException(status_code=409, detail="This booking can't be cancelled.") from exc
    return templates.TemplateResponse(
        request=request,
        name="cancel.html",
        context={
            "booking": booking,
            "slot": slot,
            "listing": listing,
            "host": await session.get(Host, listing.host_id) if listing else None,
            "refund": refund,
            "keep": keep,
        },
    )


@router.post("/b/{access_token}/cancel")
async def cancel_confirm(
    access_token: str,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> RedirectResponse:
    try:
        keep = await cancel_booking(session, access_token, datetime.now(UTC))
    except NotCancellableError as exc:
        raise HTTPException(status_code=409, detail="This booking can't be cancelled.") from exc
    if keep is not None:  # None: already cancelled by an earlier click, host already told
        booking = await session.scalar(select(Booking).where(Booking.access_token == access_token))
        slot = await session.get(Slot, booking.slot_id)
        await notify_host(session, booking, cancel_note_text(slot.starts_at, keep))
    return RedirectResponse(f"/b/{access_token}", status_code=303)


class TranslateIn(BaseModel):
    text: str = Field(max_length=500)
    source: Literal[tuple(LANGUAGES)]  # type: ignore[valid-type]
    target: Literal[tuple(LANGUAGES)]  # type: ignore[valid-type]

    @model_validator(mode="after")
    def guest_language_and_hindi(self):
        self.text = self.text.strip()
        if not self.text:
            raise ValueError("text is empty")
        if sorted([self.source == "hi", self.target == "hi"]) != [False, True]:
            raise ValueError("one side must be Hindi and the other a guest language")
        return self


async def confirmed_booking(session: AsyncSession, access_token: str) -> Booking:
    booking = await session.scalar(select(Booking).where(Booking.access_token == access_token))
    if booking is None:
        raise HTTPException(status_code=404, detail="booking not found")
    if booking.status != "CONFIRMED":
        raise HTTPException(
            status_code=403, detail="Translation help opens once your host confirms."
        )
    return booking


@router.get("/b/{access_token}/translate", response_class=HTMLResponse)
async def translate_page(
    request: Request,
    access_token: str,
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    booking = await confirmed_booking(session, access_token)
    slot = await session.get(Slot, booking.slot_id)
    listing = await session.get(Listing, slot.listing_id)
    return templates.TemplateResponse(
        request=request,
        name="translate.html",
        context={
            "booking": booking,
            "host": await session.get(Host, listing.host_id),
            "languages": {k: v for k, v in LANGUAGES.items() if k != "hi"},
        },
    )


@router.post("/b/{access_token}/translate")
async def translate_message(
    access_token: str,
    body: TranslateIn,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, str]:
    await confirmed_booking(session, access_token)
    try:
        translated = await translate_between(body.text, body.source, body.target, get_settings())
    except LlmOutputError as exc:
        raise HTTPException(
            status_code=503, detail="Translation is busy right now. Please try again."
        ) from exc
    return {"source_text": body.text, "translated_text": translated}


@router.post("/b/{access_token}/review")
async def create_review(
    access_token: str,
    warmth: int = Form(),
    text: str = Form(),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> RedirectResponse:
    booking = await session.scalar(select(Booking).where(Booking.access_token == access_token))
    if booking is None:
        raise HTTPException(status_code=404, detail="booking not found")
    if booking.status != "COMPLETED" or not 1 <= warmth <= 5 or not text.strip():
        raise HTTPException(status_code=400, detail="reviews require a completed booking")
    existing = await session.scalar(select(Review).where(Review.booking_id == booking.id))
    if existing:
        raise HTTPException(status_code=409, detail="review already submitted")
    session.add(Review(booking_id=booking.id, warmth=warmth, text=text.strip()))
    await session.commit()
    return RedirectResponse(f"/b/{access_token}", status_code=303)
