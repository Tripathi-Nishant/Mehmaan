from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_user
from app.booking.host_reply import answer_booking
from app.booking.slots import format_ist
from app.db.models import Booking, Listing, Slot, UserAccount
from app.db.session import get_session

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")
templates.env.filters["ist"] = format_ist


async def required_user(request: Request, session: AsyncSession) -> UserAccount | RedirectResponse:
    user = await current_user(request, session)
    if not user:
        # Return a response instead of raising HTTPException(303). The HTML error
        # handler intentionally renders HTML errors, so a raised 303 became the
        # visible "Error 303" page instead of redirecting to login.
        return RedirectResponse("/auth/login", status_code=303)
    return user


@router.get("/account", response_class=HTMLResponse)
async def account(request: Request, session: AsyncSession = Depends(get_session)):  # noqa: B008
    user = await required_user(request, session)
    if isinstance(user, RedirectResponse):
        return user
    if user.role == "traveler":
        bookings = list(
            await session.scalars(
                select(Booking)
                .where(Booking.traveler_account_id == user.id)
                .order_by(Booking.created_at.desc())
            )
        )
        details = []
        for booking in bookings:
            slot = await session.get(Slot, booking.slot_id)
            listing = await session.get(Listing, slot.listing_id) if slot else None
            details.append((booking, slot, listing))
        return templates.TemplateResponse(
            request=request, name="account.html", context={"user": user, "bookings": details}
        )
    listings = list(
        await session.scalars(
            select(Listing)
            .where(Listing.host_id == user.host_id)
            .order_by(Listing.created_at.desc())
        )
    )
    requests = list(
        await session.scalars(
            select(Booking)
            .join(Slot, Booking.slot_id == Slot.id)
            .join(Listing, Slot.listing_id == Listing.id)
            .where(Listing.host_id == user.host_id)
            .order_by(Booking.created_at.desc())
        )
    )
    return templates.TemplateResponse(
        request=request,
        name="host_account.html",
        context={"user": user, "listings": listings, "bookings": requests},
    )


@router.post("/account/host/bookings/{booking_id}/{decision}")
async def decide_booking(
    request: Request,
    booking_id: str,
    decision: str,
    session: AsyncSession = Depends(get_session),  # noqa: B008
):
    user = await required_user(request, session)
    if isinstance(user, RedirectResponse):
        return user
    if user.role != "host" or decision not in {"confirm", "decline"}:
        raise HTTPException(status_code=403, detail="Not allowed")
    booking = await session.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    slot = await session.get(Slot, booking.slot_id)
    listing = await session.get(Listing, slot.listing_id) if slot else None
    if not listing or listing.host_id != user.host_id or booking.status != "PAID_PENDING_HOST":
        raise HTTPException(status_code=403, detail="Booking is not awaiting your decision")
    await answer_booking(session, booking, "confirm" if decision == "confirm" else "decline")
    return RedirectResponse("/account", status_code=303)
