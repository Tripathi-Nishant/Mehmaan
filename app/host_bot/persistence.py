from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Host, Listing, OnboardingSessionRecord
from app.host_bot.onboarding import OnboardingSession, OnboardingState
from app.media.store import Media


async def load_session(
    session: AsyncSession, telegram_user_id: int, chat_id: int
) -> tuple[Host, OnboardingSession]:
    host = await session.scalar(select(Host).where(Host.telegram_user_id == telegram_user_id))
    if host is None:
        host = Host(telegram_user_id=telegram_user_id, telegram_chat_id=chat_id)
        session.add(host)
        await session.flush()
    record = await session.scalar(
        select(OnboardingSessionRecord).where(OnboardingSessionRecord.host_id == host.id)
    )
    if record is None:
        record = OnboardingSessionRecord(host_id=host.id, fields={})
        session.add(record)
        await session.flush()
    return host, OnboardingSession(
        fields=dict(record.fields),
        state=OnboardingState(record.state),
        turn_count=record.turn_count,
    )


async def save_session(session: AsyncSession, host_id: UUID, onboarding: OnboardingSession) -> None:
    record = await session.scalar(
        select(OnboardingSessionRecord).where(OnboardingSessionRecord.host_id == host_id)
    )
    if record is None:
        raise ValueError(f"onboarding session missing for host {host_id}")
    record.fields = onboarding.fields
    record.state = onboarding.state.value
    record.turn_count = onboarding.turn_count
    await session.commit()


async def publish_listing(
    session: AsyncSession, host_id: UUID, onboarding: OnboardingSession, transcript: str
) -> Listing:
    if onboarding.state != OnboardingState.READBACK:
        raise ValueError("listing cannot publish before read-back")
    listing = Listing(
        host_id=host_id,
        status="LIVE",
        category=onboarding.fields["category"],
        description_hi=onboarding.fields["activity_description"],
        source_transcript=transcript,
        price_per_person_paise=onboarding.fields["price_per_person_paise"],
        city=onboarding.fields["city"],
        area=onboarding.fields["area"],
        location_lat=onboarding.fields.get("location_lat"),
        location_lng=onboarding.fields.get("location_lng"),
        landmark=onboarding.fields.get("landmark"),
        cancellation_rule=onboarding.fields.get("cancellation_rule"),
    )
    onboarding.publish()
    session.add(listing)
    await session.flush()
    media_ids = [
        onboarding.fields.get("gate_photo_media_id"),
        *onboarding.fields.get("experience_photo_media_ids", []),
    ]
    for media_id in filter(None, media_ids):
        media = await session.get(Media, UUID(str(media_id)))
        if media:
            media.listing_id = listing.id
    await session.commit()
    return listing
