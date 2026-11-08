from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Listing, Slot
from app.db.session import get_session

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")


@router.get("/", response_class=HTMLResponse)
async def browse(
    request: Request,
    q: str = Query(default=""),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> HTMLResponse:
    statement = select(Listing).where(Listing.status == "LIVE").order_by(Listing.created_at.desc())
    if q.strip():
        term = f"%{q.strip()}%"
        statement = statement.where(
            or_(
                Listing.category.ilike(term),
                Listing.city.ilike(term),
                Listing.area.ilike(term),
                Listing.description_hi.ilike(term),
            )
        )
    listings = (await session.scalars(statement)).all()
    return templates.TemplateResponse(
        request=request, name="browse.html", context={"listings": listings, "q": q}
    )


@router.get("/listings/{listing_id}", response_class=HTMLResponse)
async def listing_detail(
    request: Request,
    listing_id: UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> HTMLResponse:
    listing = await session.scalar(
        select(Listing).where(Listing.id == listing_id, Listing.status == "LIVE")
    )
    if listing is None:
        raise HTTPException(status_code=404, detail="listing not found")
    slots = (await session.scalars(select(Slot).where(Slot.listing_id == listing.id))).all()
    return templates.TemplateResponse(
        request=request, name="listing.html", context={"listing": listing, "slots": slots}
    )
