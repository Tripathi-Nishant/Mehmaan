from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.booking.policy import NotCancellableError, cancellation_split
from app.booking.states import BookingStatus, transition
from app.db.models import Booking, LedgerEntry, Listing, Payment, Slot, Traveler
from app.notifications.email import enqueue_booking_email
from app.payments.ledger import LedgerSplit, refund_reversal


class SlotFullError(RuntimeError):
    pass


async def create_hold(
    session: AsyncSession,
    slot_id: UUID,
    name: str,
    email: str,
    guests: int,
    hold_minutes: int,
    now: datetime,
) -> Booking:
    """Reserve seats for an unpaid booking. Flushes but does not commit: the caller adds the
    payment order in the same transaction so a hold never exists without one."""
    # FOR UPDATE: two travelers racing for the last seat are serialised on the slot row.
    slot = await session.scalar(select(Slot).where(Slot.id == slot_id).with_for_update())
    if slot is None or slot.starts_at <= now:
        raise SlotFullError("slot is unavailable")
    if guests < 1 or slot.booked_count + guests > slot.capacity:
        raise SlotFullError("slot does not have enough seats")
    listing = await session.get(Listing, slot.listing_id)
    if listing is None or listing.status != "LIVE":
        raise SlotFullError("listing is not bookable")
    # Ids set up front (not at flush) so the payment can reference the booking immediately.
    traveler = Traveler(id=uuid4(), name=name, email=email)
    booking = Booking(
        id=uuid4(),
        slot_id=slot.id,
        traveler_id=traveler.id,
        guests=guests,
        status="HELD",
        amount_paise=listing.price_per_person_paise * guests,  # server-side, never from the form
        hold_expires_at=now + timedelta(minutes=hold_minutes),
    )
    session.add(traveler)
    # Flush the parent row first. This makes the FK ordering explicit for
    # asyncpg/PostgreSQL before the booking references traveler_id.
    await session.flush([traveler])
    session.add(booking)
    slot.booked_count += guests
    await session.flush()
    return booking


CANCELLABLE = (BookingStatus.PAID_PENDING_HOST, BookingStatus.CONFIRMED)


async def cancel_booking(session: AsyncSession, access_token: str, now: datetime) -> int | None:
    """Traveler cancel, one transaction: CANCELLED, payment REFUNDED, ledger reversed, seats
    released. Returns the host's kept share (paise), or None if it was already cancelled."""
    booking = await session.scalar(
        select(Booking).where(Booking.access_token == access_token).with_for_update()
    )
    if booking is None:
        raise NotCancellableError("booking not found")
    if booking.status == BookingStatus.CANCELLED:
        return None  # double POST: nothing to do
    if booking.status not in CANCELLABLE:
        raise NotCancellableError(f"a {booking.status} booking cannot be cancelled")
    slot = await session.scalar(select(Slot).where(Slot.id == booking.slot_id).with_for_update())
    refund, keep = cancellation_split(booking.amount_paise, slot.starts_at, now)
    booking.status = transition(BookingStatus(booking.status), BookingStatus.CANCELLED).value
    payment = await session.scalar(
        select(Payment).where(Payment.booking_id == booking.id).with_for_update()
    )
    payment.status = "REFUNDED"
    listing = await session.get(Listing, slot.listing_id)
    split = LedgerSplit(booking.amount_paise, booking.commission_paise, booking.host_payout_paise)
    session.add_all(
        LedgerEntry(booking_id=booking.id, host_id=listing.host_id, type=kind, amount_paise=amount)
        for kind, amount in refund_reversal(split, refund, keep)
    )
    booking.commission_paise = 0  # the host's late-cancel share is commission-free
    booking.host_payout_paise = keep
    slot.booked_count = max(0, slot.booked_count - booking.guests)
    await enqueue_booking_email(session, booking, "BOOKING_CANCELLED", refund_paise=refund)
    await session.commit()
    return keep
