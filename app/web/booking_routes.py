from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import Booking, Host, LedgerEntry, Listing, Payment, Review, Slot
from app.db.session import get_session
from app.notifications.host_voice import send_host_message
from app.payments.ledger import split_charge
from app.payments.mock_provider import MockProvider

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")


@router.post("/book/{slot_id}")
async def book(
    slot_id: UUID,
    name: str = Form(),
    email: str = Form(),
    guests: int = Form(),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> RedirectResponse:
    slot = await session.scalar(select(Slot).where(Slot.id == slot_id).with_for_update())
    if slot is None:
        raise HTTPException(status_code=404, detail="slot not found")
    listing = await session.get(Listing, slot.listing_id)
    if listing is None or guests < 1 or slot.booked_count + guests > slot.capacity:
        raise HTTPException(status_code=409, detail="slot is full")
    from app.db.models import Traveler

    traveler = Traveler(name=name, email=email)
    session.add(traveler)
    await session.flush()
    now = datetime.now(UTC)
    settings = get_settings()
    booking = Booking(
        slot_id=slot.id,
        traveler_id=traveler.id,
        guests=guests,
        amount_paise=listing.price_per_person_paise * guests,
        hold_expires_at=now + timedelta(minutes=settings.hold_minutes),
    )
    session.add(booking)
    slot.booked_count += guests
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
    return templates.TemplateResponse(
        request=request, name="payment.html", context={"payment": payment}
    )


@router.post("/pay/mock/{order_id}/verify")
async def verify_payment(order_id: str, session: AsyncSession = Depends(get_session)):  # noqa: B008
    payment = await session.scalar(select(Payment).where(Payment.provider_order_id == order_id))
    if payment is None:
        raise HTTPException(status_code=404, detail="order not found")
    provider = MockProvider(get_settings().mock_payment_secret)
    result = provider.pay(order_id)
    if not provider.verify(result):
        raise HTTPException(status_code=400, detail="invalid payment signature")
    captured_now = payment.status != "CAPTURED"
    if captured_now:
        payment.provider_payment_id = result.payment_id
        payment.status = "CAPTURED"
        booking = await session.get(Booking, payment.booking_id)
        if booking:
            booking.status = "PAID_PENDING_HOST"
            booking.host_reply_deadline = datetime.now(UTC) + timedelta(
                minutes=get_settings().host_reply_timeout_minutes
            )
            split = split_charge(booking.amount_paise, get_settings().commission_bps)
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
        await session.commit()
    booking = await session.get(Booking, payment.booking_id)
    if captured_now and booking and get_settings().telegram_bot_token:
        slot = await session.get(Slot, booking.slot_id)
        listing = await session.get(Listing, slot.listing_id) if slot else None
        host = await session.get(Host, listing.host_id) if listing else None
        if host:
            from telegram import Bot

            async with Bot(get_settings().telegram_bot_token) as bot:
                await send_host_message(
                    bot,
                    host.telegram_chat_id,
                    "Naya booking aaya hai. Kripya haan ya nahi bhejiye. Yeh TEST payment hai.",
                    get_settings(),
                )
    return RedirectResponse(f"/b/{booking.access_token}", status_code=303)


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
    exact_address = listing.exact_address if booking.status == "CONFIRMED" and listing else None
    return templates.TemplateResponse(
        request=request,
        name="booking.html",
        context={"booking": booking, "listing": listing, "exact_address": exact_address},
    )


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
