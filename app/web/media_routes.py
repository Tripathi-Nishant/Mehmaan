from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Host, Listing
from app.db.session import get_session
from app.media.store import Media

router = APIRouter()


@router.get("/media/{media_id}")
async def media(
    media_id: UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> Response:
    item = await session.scalar(
        select(Media)
        .join(Listing, Media.listing_id == Listing.id)
        .join(Host, Listing.host_id == Host.id)
        .where(
            Media.id == media_id,
            Listing.status == "LIVE",
            (Media.kind != "audio") | Host.consent_voice_clip.is_(True),
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="media not found")
    if item.kind not in {"audio", "photo"}:
        raise HTTPException(status_code=404, detail="media unavailable")
    return Response(content=item.data, media_type=item.content_type)
