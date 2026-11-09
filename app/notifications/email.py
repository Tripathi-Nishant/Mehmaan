import asyncio
import smtplib
import ssl
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.booking.slots import format_ist
from app.config import Settings, get_settings
from app.db.models import Booking, EmailOutbox, Listing, Slot, Traveler
from app.host_bot.readback import format_rupees

FOOTER = "TEST BOOKING: this is a demo, no real money moved.\n— Mehmaan"
MAX_EMAIL_ATTEMPTS = 5


def render_email(
    kind: str,
    *,
    title: str,
    starts_at: datetime,
    guests: int,
    booking_url: str,
    location: dict | None = None,
    refund_paise: int | None = None,
    declined: bool = False,
) -> tuple[str, str]:
    """(subject, plain-text body). Never given host contact or UPI details, so can't leak them."""
    when = f"{title}\n{format_ist(starts_at)} · {guests} guest{'s' if guests != 1 else ''}"
    if kind == "BOOKING_RECEIVED":
        subject = "[TEST] Booking received — waiting for the host"
        lines = [
            "Your payment went through. The host will confirm shortly.",
            when,
            f"Your booking: {booking_url}",
        ]
    elif kind == "BOOKING_CONFIRMED":
        subject = "[TEST] Booking confirmed"
        lines = ["Your host confirmed!", when]
        if location:
            lines.append(f"Map: {location['map_url']}")
            if location["landmark"]:
                lines.append(f"Landmark: {location['landmark']}")
        lines += [
            f"Interpreter (on the day): {booking_url}/interpreter",
            f"Need to cancel? {booking_url}/cancel",
        ]
    elif kind == "BOOKING_CANCELLED":
        subject = "[TEST] Booking cancelled"
        reason = (
            "Sorry, the host couldn't confirm this booking."
            if declined
            else "Your booking is cancelled."
        )
        lines = [reason, when, f"Refund: {format_rupees(refund_paise)} (TEST)"]
    else:
        raise ValueError(f"unknown email kind {kind}")
    return subject, "\n\n".join([*lines, FOOTER])


async def enqueue_booking_email(
    session: AsyncSession,
    booking: Booking,
    kind: str,
    refund_paise: int | None = None,
    declined: bool = False,
) -> None:
    """Queue in the caller's transaction (no commit). A repeat for the same booking+kind is
    dropped by the unique dedupe_key."""
    from app.booking.host_reply import location_reveal  # import here: host_reply -> jobs -> us

    slot = await session.get(Slot, booking.slot_id)
    listing = await session.get(Listing, slot.listing_id)
    traveler = await session.get(Traveler, booking.traveler_id)
    subject, body = render_email(
        kind,
        title=listing.title_en or listing.description_hi or "Your Mehmaan experience",
        starts_at=slot.starts_at,
        guests=booking.guests,
        booking_url=f"{get_settings().public_base_url}/b/{booking.access_token}",
        location=location_reveal(booking, listing),
        refund_paise=refund_paise,
        declined=declined,
    )
    await session.execute(
        insert(EmailOutbox)
        .values(
            booking_id=booking.id,
            kind=kind,
            to_email=traveler.email,
            subject=subject,
            body=body,
            dedupe_key=f"{booking.id}:{kind}",
            status="PENDING",
            attempts=0,
        )
        .on_conflict_do_nothing(index_elements=["dedupe_key"])
    )


def send_smtp(settings: Settings, to: str, subject: str, body: str) -> None:
    """Blocking; run in a thread."""
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = settings.smtp_from, to, subject
    msg.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)


async def send_pending_emails(
    session: AsyncSession,
    settings: Settings,
    now: datetime | None = None,
    send: Callable[[Settings, str, str, str], None] = send_smtp,
) -> int:
    """Send due PENDING rows. Failure: retry after 1, 2, 4, 8 min, FAILED on the 5th."""
    if not settings.smtp_host:
        return 0
    now = now or datetime.now(UTC)
    rows = (
        await session.scalars(
            select(EmailOutbox)
            .where(EmailOutbox.status == "PENDING", EmailOutbox.next_attempt_at <= now)
            .order_by(EmailOutbox.created_at)
            .limit(20)
            .with_for_update(skip_locked=True)
        )
    ).all()
    sent = 0
    for row in rows:
        row.attempts += 1
        try:
            await asyncio.to_thread(send, settings, row.to_email, row.subject, row.body)
        except (smtplib.SMTPException, OSError) as exc:  # OSError: DNS, refused, timeout
            row.last_error = str(exc)[:500]
            if row.attempts >= MAX_EMAIL_ATTEMPTS:
                row.status = "FAILED"
            else:
                row.next_attempt_at = now + timedelta(minutes=2 ** (row.attempts - 1))
        else:
            row.status, row.sent_at = "SENT", now
            sent += 1
    await session.commit()
    return sent
