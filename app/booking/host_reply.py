from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.booking.actions import host_accept
from app.config import Settings
from app.db.models import Booking, Listing, Slot
from app.host_bot.intents import classify_reply
from app.host_bot.service import booking_prompt_text, route_host_reply
from app.jobs.actions import decline_and_refund
from app.notifications.email import enqueue_booking_email

CONFIRMED_REPLY = "Booking confirm ho gayi. Mehmaan ko pata chal gaya."
DECLINED_REPLY = "Booking decline aur test refund kar diya gaya."


def location_reveal(booking, listing) -> dict | None:
    """Map link + landmark for the guest, only once the host has confirmed. Computed here (not
    in the template) so coordinates never reach the page before confirmation."""
    if booking.status != "CONFIRMED" or listing is None or listing.location_lat is None:
        return None
    return {
        "map_url": f"https://www.google.com/maps?q={listing.location_lat},{listing.location_lng}",
        "landmark": listing.landmark_en or listing.landmark_hi,
    }


async def pending_booking_for(db: AsyncSession, host_id: UUID) -> Booking | None:
    """The host's booking awaiting haan/nahi. Demo scope: at most one, so it is the open prompt.
    Locked so a reply and the reply-timeout job can't both act on it."""
    return await db.scalar(
        select(Booking)
        .join(Slot, Booking.slot_id == Slot.id)
        .join(Listing, Slot.listing_id == Listing.id)
        .where(Listing.host_id == host_id, Booking.status == "PAID_PENDING_HOST")
        .order_by(Booking.created_at)
        .limit(1)
        .with_for_update(of=Booking)
    )


async def booking_reply(db: AsyncSession, booking: Booking, said: str, settings: Settings) -> str:
    """Apply a host's text/voice reply to their pending booking; return what to say back."""
    action = route_host_reply(True, await classify_reply(said, settings))
    if action == "ask_again":
        slot = await db.get(Slot, booking.slot_id)
        prompt = booking_prompt_text(slot.starts_at, booking.guests, booking.host_payout_paise)
        return "Kripya haan ya nahi boliye. " + prompt
    return await answer_booking(db, booking, action)


async def answer_booking(db: AsyncSession, booking: Booking, action: str) -> str:
    """action is "confirm" or "decline" (from route_host_reply). Commits."""
    if action == "confirm":
        booking.status = host_accept(booking.status)
        await enqueue_booking_email(db, booking, "BOOKING_CONFIRMED")
        await db.commit()
        return CONFIRMED_REPLY
    await decline_and_refund(db, booking)  # DECLINED -> REFUNDED, ledger REFUND, seats back
    return DECLINED_REPLY
