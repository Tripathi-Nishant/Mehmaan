from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import Base

MAX_MEDIA_BYTES = 5 * 1024 * 1024


class MediaTooLargeError(ValueError):
    pass


class Media(Base):
    __tablename__ = "media"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    kind: Mapped[str] = mapped_column(String(20))
    content_type: Mapped[str] = mapped_column(String(100))
    data: Mapped[bytes] = mapped_column(LargeBinary)
    size_bytes: Mapped[int] = mapped_column(Integer)
    listing_id: Mapped[UUID | None] = mapped_column(ForeignKey("listings.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


async def save_media(db: AsyncSession, kind: str, content_type: str, data: bytes) -> Media:
    if len(data) > MAX_MEDIA_BYTES:
        raise MediaTooLargeError("media exceeds 5 MB")
    media = Media(kind=kind, content_type=content_type, data=data, size_bytes=len(data))
    db.add(media)
    await db.flush()
    return media
