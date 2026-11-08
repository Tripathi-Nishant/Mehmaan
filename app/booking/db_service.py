from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Booking, Listing, Slot, Traveler


class SlotFullError(RuntimeError):
    pass


async def create_hold(
    session: AsyncSession, slot_id: UUID, name: str, email: str, guests: int
) -> Booking:
    slot = await session.scalar(select(Slot).where(Slot.id == slot_id).with_for_update())
    if slot is None or guests < 1 or slot.booked_count + guests > slot.capacity:
        raise SlotFullError("slot is full or unavailable")
    listing = await session.get(Listing, slot.listing_id)
    if listing is None:
        raise SlotFullError("listing is unavailable")
    traveler = Traveler(name=name, email=email)
    session.add(traveler)
    await session.flush()
    booking = Booking(
        slot_id=slot.id,
        traveler_id=traveler.id,
        guests=guests,
        amount_paise=listing.price_per_person_paise * guests,
    )
    session.add(booking)
    slot.booked_count += guests
    await session.commit()
    return booking
