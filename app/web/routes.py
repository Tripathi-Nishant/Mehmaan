from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.booking.slots import format_ist
from app.config import get_settings
from app.db.models import Host, Listing, Slot
from app.db.session import get_session
from app.media.store import Media

HOME_LISTINGS = 3  # the home page shows this many; "/?all=1" shows every live listing

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")
templates.env.filters["ist"] = format_ist


@router.get("/", response_class=HTMLResponse)
async def browse(
    request: Request,
    q: str = Query(default=""),
    show_all: bool = Query(default=False, alias="all"),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> HTMLResponse:
    live = Listing.status == "LIVE"
    statement = select(Listing).where(live).order_by(Listing.created_at.desc())
    if not q.strip() and not show_all:
        statement = statement.limit(HOME_LISTINGS)
    if q.strip():
        term = f"%{q.strip()}%"
        statement = statement.where(
            or_(
                Listing.category.ilike(term),
                Listing.city.ilike(term),
                Listing.area.ilike(term),
                Listing.title_en.ilike(term),
                Listing.description_en.ilike(term),
                Listing.description_hi.ilike(term),
            )
        )
    listings = (await session.scalars(statement)).all()
    # First experience photo per listing (ids only). "photo" never includes the private gate photo.
    first_photo = (
        select(Media.listing_id, Media.id)
        .where(Media.kind == "photo", Media.listing_id.in_([x.id for x in listings]))
        .order_by(Media.listing_id, Media.created_at, Media.id)
        .distinct(Media.listing_id)
    )
    photos = dict((await session.execute(first_photo)).tuples().all())
    cities = (
        await session.scalars(select(Listing.city).where(live).distinct().order_by(Listing.city))
    ).all()
    return templates.TemplateResponse(
        request=request,
        name="browse.html",
        context={
            "listings": listings,
            "q": q,
            "photos": photos,
            "cities": cities,
            "show_all": show_all,
        },
    )


STATIC_PAGES = {
    "/about": "about.html",
    "/privacy": "privacy.html",
    "/terms": "terms.html",
    "/cancellation-policy": "cancellation_policy.html",
}


@router.get("/about", response_class=HTMLResponse)
@router.get("/privacy", response_class=HTMLResponse)
@router.get("/terms", response_class=HTMLResponse)
@router.get("/cancellation-policy", response_class=HTMLResponse)
async def static_page(request: Request) -> HTMLResponse:
    """Content-only pages; numbers come from settings so the text matches the system."""
    settings = get_settings()
    return templates.TemplateResponse(
        request=request,
        name=STATIC_PAGES[request.url.path],
        context={
            "hold_minutes": settings.hold_minutes,
            "reply_hours": settings.host_reply_timeout_minutes // 60,
        },
    )


@router.get("/listings/{listing_id}", response_class=HTMLResponse)
async def listing_detail(
    request: Request,
    listing_id: UUID,
    payment: str = Query(default=""),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> HTMLResponse:
    listing = await session.scalar(
        select(Listing).where(Listing.id == listing_id, Listing.status == "LIVE")
    )
    if listing is None:
        raise HTTPException(status_code=404, detail="listing not found")
    slots = (
        await session.scalars(
            select(Slot)
            .where(
                Slot.listing_id == listing.id,
                Slot.starts_at > datetime.now(UTC),
                Slot.booked_count < Slot.capacity,
            )
            .order_by(Slot.starts_at)
        )
    ).all()
    return templates.TemplateResponse(
        request=request,
        name="listing.html",
        context={
            "listing": listing,
            "host": await session.get(Host, listing.host_id),
            "slots": slots,
            "payment_failed": payment == "failed",
        },
    )
