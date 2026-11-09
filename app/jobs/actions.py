from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.booking.actions import expire_hold, host_decline, refund_declined
from app.db.models import Booking, LedgerEntry, Listing, Payment, Payout, Slot
from app.notifications.email import enqueue_booking_email
from app.payments.ledger import LedgerSplit, refund_reversal


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
    for booking in bookings:
        expire_hold(booking, await session.get(Slot, booking.slot_id))
    await session.commit()
    return len(bookings)


async def decline_and_refund(session: AsyncSession, booking: Booking) -> None:
    booking.status = host_decline(booking.status)
    payment = await session.scalar(select(Payment).where(Payment.booking_id == booking.id))
    slot = await session.get(Slot, booking.slot_id)
    if payment and payment.status == "CAPTURED":
        payment.status = "REFUNDED"
        booking.status = refund_declined(booking.status)
        listing = await session.get(Listing, slot.listing_id) if slot else None
        split = LedgerSplit(
            booking.amount_paise, booking.commission_paise, booking.host_payout_paise
        )
        session.add_all(
            LedgerEntry(
                booking_id=booking.id,
                host_id=listing.host_id if listing else None,
                type=kind,
                amount_paise=amount,
            )
            for kind, amount in refund_reversal(split, refund=booking.amount_paise, host_keep=0)
        )
        booking.host_payout_paise = 0
        await enqueue_booking_email(
            session, booking, "BOOKING_CANCELLED", refund_paise=booking.amount_paise, declined=True
        )
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
            .where(
                or_(
                    Booking.status == "COMPLETED",
                    # late traveler cancel: the host's kept share is paid out too
                    and_(Booking.status == "CANCELLED", Booking.host_payout_paise > 0),
                )
            )
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
