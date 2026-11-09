from datetime import UTC, date, datetime, time, timedelta, timezone
from uuid import UUID

from app.db.models import Slot

# India has no DST, so a fixed offset equals Asia/Kolkata (and needs no tzdata on Windows).
IST = timezone(timedelta(hours=5, minutes=30), "IST")
# ponytail: generated once at publish, so slots run out after 30 days; add a daily top-up job
# (unique listing_id+starts_at makes re-running safe) if listings must stay bookable longer.
SLOT_WINDOW_DAYS = 30


def format_ist(moment: datetime) -> str:
    """'Sat 14 Nov, 11:00 AM' in India time (portable: no %-d, which Windows lacks)."""
    local = moment.astimezone(IST)
    clock = local.strftime("%I:%M %p").lstrip("0")
    return f"{local:%a} {local.day} {local:%b}, {clock}"


def generate_slots(
    listing_id: UUID, weekdays: list[int], start_time_local: time, max_guests: int, today: date
) -> list[Slot]:
    """One slot per matching IST day from tomorrow through today+30, stored in UTC."""
    slots = []
    for offset in range(1, SLOT_WINDOW_DAYS + 1):
        day = today + timedelta(days=offset)
        if day.weekday() in weekdays:
            starts_at = datetime.combine(day, start_time_local, tzinfo=IST).astimezone(UTC)
            slots.append(
                Slot(
                    listing_id=listing_id, starts_at=starts_at, capacity=max_guests, booked_count=0
                )
            )
    return slots
