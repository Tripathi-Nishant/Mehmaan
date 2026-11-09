import smtplib
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from test_host_booking_reply import seed_paid_booking

from app.booking.db_service import cancel_booking
from app.booking.host_reply import answer_booking
from app.config import Settings
from app.db.models import Booking, EmailOutbox
from app.notifications.email import enqueue_booking_email, render_email, send_pending_emails

START = datetime(2026, 11, 14, 5, 30, tzinfo=UTC)
URL = "http://t/b/tok"
COMMON = {"title": "Dal baati in Jaipur", "starts_at": START, "guests": 2, "booking_url": URL}
LOCATION = {"map_url": "https://www.google.com/maps?q=26.9,75.8", "landmark": "Blue gate"}


def test_received_has_no_location():
    subject, body = render_email("BOOKING_RECEIVED", **COMMON)
    assert "TEST" in subject and "TEST" in body
    assert "Sat 14 Nov, 11:00 AM" in body and URL in body
    assert "maps" not in body and "Blue gate" not in body


def test_confirmed_has_location_interpreter_and_cancel_links():
    _, body = render_email("BOOKING_CONFIRMED", **COMMON, location=LOCATION)
    assert "TEST" in body
    assert LOCATION["map_url"] in body and "Blue gate" in body
    assert f"{URL}/interpreter" in body and f"{URL}/cancel" in body


def test_cancelled_states_refund():
    _, body = render_email("BOOKING_CANCELLED", **COMMON, refund_paise=240000)
    assert "₹2,400" in body and "TEST" in body
    _, declined = render_email("BOOKING_CANCELLED", **COMMON, refund_paise=300000, declined=True)
    assert "couldn't confirm" in declined and "₹3,000" in declined


# --- real Postgres ---------------------------------------------------------------------------
async def outbox(db, booking_id):
    return (await db.scalars(select(EmailOutbox).where(EmailOutbox.booking_id == booking_id))).all()


async def test_enqueue_twice_gives_one_row(db):
    _, _, booking = await seed_paid_booking(db)
    await enqueue_booking_email(db, booking, "BOOKING_RECEIVED")
    await enqueue_booking_email(db, booking, "BOOKING_RECEIVED")
    await db.commit()
    rows = await outbox(db, booking.id)
    assert len(rows) == 1
    assert rows[0].dedupe_key == f"{booking.id}:BOOKING_RECEIVED"
    assert rows[0].status == "PENDING" and rows[0].to_email == "a@example.com"


async def test_confirm_queues_confirmation_email(db):
    _, _, booking = await seed_paid_booking(db)
    await answer_booking(db, booking, "confirm")
    assert [r.kind for r in await outbox(db, booking.id)] == ["BOOKING_CONFIRMED"]


async def test_decline_queues_declined_email(db):
    _, _, booking = await seed_paid_booking(db)
    await answer_booking(db, booking, "decline")
    (row,) = await outbox(db, booking.id)
    assert row.kind == "BOOKING_CANCELLED" and "couldn't confirm" in row.body


SMTP = Settings(smtp_host="smtp.test", smtp_from="demo@mehmaan.test")


async def queued(db):
    _, _, booking = await seed_paid_booking(db)
    await enqueue_booking_email(db, booking, "BOOKING_RECEIVED")
    await db.commit()
    return (await outbox(db, booking.id))[0]


async def test_sender_marks_sent(db):
    row = await queued(db)
    sent = []
    now = datetime.now(UTC) + timedelta(seconds=1)
    assert await send_pending_emails(db, SMTP, now, send=lambda *a: sent.append(a)) == 1
    await db.refresh(row)
    assert row.status == "SENT" and row.sent_at == now
    assert sent == [(SMTP, "a@example.com", row.subject, row.body)]
    assert await send_pending_emails(db, SMTP, now, send=lambda *a: sent.append(a)) == 0


def failing(*_):
    raise smtplib.SMTPException("mailbox busy")


async def test_failure_backs_off_then_gives_up_after_5_attempts(db):
    row = await queued(db)
    now = datetime.now(UTC) + timedelta(seconds=1)
    await send_pending_emails(db, SMTP, now, send=failing)
    await db.refresh(row)
    assert row.status == "PENDING" and row.attempts == 1 and "busy" in row.last_error
    assert row.next_attempt_at == now + timedelta(minutes=1)
    assert await send_pending_emails(db, SMTP, now, send=failing) == 0  # not due yet
    for hour in range(1, 5):  # each retry an hour later: always past the backoff
        await send_pending_emails(db, SMTP, now + timedelta(hours=hour), send=failing)
    await db.refresh(row)
    assert row.status == "FAILED" and row.attempts == 5


async def test_no_smtp_host_leaves_rows_pending(db):
    row = await queued(db)
    assert await send_pending_emails(db, Settings(smtp_host=""), datetime.now(UTC)) == 0
    await db.refresh(row)
    assert row.status == "PENDING"


async def test_double_cancel_queues_one_cancellation_email(db):
    _, _, booking = await seed_paid_booking(db)
    await cancel_booking(db, booking.access_token, datetime.now(UTC))
    await cancel_booking(db, booking.access_token, datetime.now(UTC))
    (row,) = await outbox(db, booking.id)
    assert row.kind == "BOOKING_CANCELLED" and "₹3,000" in row.body
    status = await db.scalar(select(Booking.status).where(Booking.id == booking.id))
    assert status == "CANCELLED"
    assert await db.scalar(select(func.count()).select_from(EmailOutbox)) == 1
