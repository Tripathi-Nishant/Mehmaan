from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.booking.actions import host_decline, refund_declined
from app.db.models import Booking, LedgerEntry, Listing, Payment, Payout, Slot


async def expire_unpaid_holds(session: AsyncSession, now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    bookings = (
        await session.scalars(
            select(Booking).where(
                Booking.status == "HELD",
                Booking.hold_expires_at.is_not(None),
                Booking.hold_expires_at < now,
            )
        )
    ).all()
    count = 0
    for booking in bookings:
        booking.status = "EXPIRED"
        slot = await session.get(Slot, booking.slot_id)
        if slot:
            slot.booked_count = max(0, slot.booked_count - booking.guests)
        count += 1
    await session.commit()
    return count


async def decline_and_refund(session: AsyncSession, booking: Booking) -> None:
    booking.status = host_decline(booking.status)
    payment = await session.scalar(select(Payment).where(Payment.booking_id == booking.id))
    if payment and payment.status == "CAPTURED":
        payment.status = "REFUNDED"
        booking.status = refund_declined(booking.status)
        session.add(
            LedgerEntry(
                booking_id=booking.id,
                type="REFUND",
                amount_paise=booking.amount_paise,
            )
        )
    slot = await session.get(Slot, booking.slot_id)
    if slot:
        slot.booked_count = max(0, slot.booked_count - booking.guests)
    await session.commit()


async def expire_host_replies(session: AsyncSession, now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    bookings = (
        await session.scalars(
            select(Booking).where(
                Booking.status == "PAID_PENDING_HOST",
                Booking.host_reply_deadline.is_not(None),
                Booking.host_reply_deadline < now,
            )
        )
    ).all()
    for booking in bookings:
        await decline_and_refund(session, booking)
    return len(bookings)


async def complete_due_bookings(session: AsyncSession, now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    bookings = (
        await session.scalars(
            select(Booking)
            .join(Slot, Booking.slot_id == Slot.id)
            .where(Booking.status == "CONFIRMED", Slot.starts_at < now - timedelta(hours=2))
        )
    ).all()
    for booking in bookings:
        booking.status = "COMPLETED"
    await session.commit()
    return len(bookings)


async def schedule_completed_payouts(session: AsyncSession, now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    bookings = (
        await session.scalars(
            select(Booking)
            .join(Slot, Booking.slot_id == Slot.id)
            .join(Listing, Slot.listing_id == Listing.id)
            .where(Booking.status == "COMPLETED")
        )
    ).all()
    count = 0
    for booking in bookings:
        exists = await session.scalar(select(Payout).where(Payout.booking_id == booking.id))
        if exists:
            continue
        listing = await session.get(Listing, (await session.get(Slot, booking.slot_id)).listing_id)
        payout = Payout(
            host_id=listing.host_id,
            booking_id=booking.id,
            amount_paise=booking.host_payout_paise,
            scheduled_for=now,
        )
        session.add(payout)
        count += 1
    await session.commit()
    return count


async def send_due_mock_payouts(session: AsyncSession, now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    payouts = (
        await session.scalars(
            select(Payout).where(Payout.status == "SCHEDULED", Payout.scheduled_for <= now)
        )
    ).all()
    for payout in payouts:
        payout.status = "SENT_MOCK"
        payout.sent_at = now
        session.add(
            LedgerEntry(
                booking_id=payout.booking_id,
                host_id=payout.host_id,
                type="PAYOUT",
                amount_paise=-payout.amount_paise,
            )
        )
    await session.commit()
    return len(payouts)
