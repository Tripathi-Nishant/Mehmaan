from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from test_host_booking_reply import seed_paid_booking

from app.booking.db_service import cancel_booking
from app.booking.policy import NotCancellableError
from app.booking.states import BookingStatus, InvalidTransitionError, transition
from app.db.models import Booking, LedgerEntry, Payment, Payout, Slot
from app.host_bot.service import cancel_note_text
from app.jobs.actions import schedule_completed_payouts


@pytest.mark.parametrize("current", ["PAID_PENDING_HOST", "CONFIRMED"])
def test_paid_bookings_can_be_cancelled(current):
    assert transition(BookingStatus(current), BookingStatus.CANCELLED) == "CANCELLED"


@pytest.mark.parametrize("current", ["HELD", "EXPIRED", "REFUNDED", "COMPLETED", "CANCELLED"])
def test_other_bookings_cannot_be_cancelled(current):
    with pytest.raises(InvalidTransitionError):
        transition(BookingStatus(current), BookingStatus.CANCELLED)


# --- real Postgres ---------------------------------------------------------------------------
async def ledger_total(db, booking_id):
    return await db.scalar(
        select(func.sum(LedgerEntry.amount_paise)).where(LedgerEntry.booking_id == booking_id)
    )


async def test_early_cancel_refunds_everything_and_releases_seats(db):
    _, slot, booking = await seed_paid_booking(db, guests=2)  # starts in 3 days
    keep = await cancel_booking(db, booking.access_token, datetime.now(UTC))
    assert keep == 0
    fresh = await db.get(Booking, booking.id, populate_existing=True)
    assert fresh.status == "CANCELLED" and fresh.host_payout_paise == 0
    payment = await db.scalar(select(Payment).where(Payment.booking_id == booking.id))
    assert payment.status == "REFUNDED"
    assert await ledger_total(db, booking.id) == 0
    assert (await db.get(Slot, slot.id, populate_existing=True)).booked_count == 0


async def test_late_cancel_host_keeps_20_percent_commission_free(db):
    _, slot, booking = await seed_paid_booking(db)
    now = slot.starts_at - timedelta(hours=10)
    assert await cancel_booking(db, booking.access_token, now) == 60000  # 20% of ₹3,000
    fresh = await db.get(Booking, booking.id, populate_existing=True)
    assert fresh.host_payout_paise == 60000 and fresh.commission_paise == 0
    refund = await db.scalar(
        select(LedgerEntry.amount_paise).where(
            LedgerEntry.booking_id == booking.id, LedgerEntry.type == "REFUND"
        )
    )
    assert refund == -240000
    assert await ledger_total(db, booking.id) == 0


async def test_double_cancel_is_a_no_op(db):
    _, _, booking = await seed_paid_booking(db)
    await cancel_booking(db, booking.access_token, datetime.now(UTC))
    assert await cancel_booking(db, booking.access_token, datetime.now(UTC)) is None
    refunds = await db.scalar(
        select(func.count()).where(
            LedgerEntry.booking_id == booking.id, LedgerEntry.type == "REFUND"
        )
    )
    assert refunds == 1
    assert await ledger_total(db, booking.id) == 0


async def test_cannot_cancel_after_start(db):
    _, slot, booking = await seed_paid_booking(db)
    with pytest.raises(NotCancellableError):
        await cancel_booking(db, booking.access_token, slot.starts_at)


async def test_unknown_token_is_not_cancellable(db):
    with pytest.raises(NotCancellableError):
        await cancel_booking(db, "nope", datetime.now(UTC))


def test_host_cancel_notes():
    starts = datetime(2026, 11, 14, 5, 30, tzinfo=UTC)
    assert cancel_note_text(starts, 60000) == (
        "Sat 14 Nov, 11:00 AM wali booking mehmaan ne cancel kar di. Aapko ₹600 milenge (test)."
    )
    assert cancel_note_text(starts, 0) == "Sat 14 Nov, 11:00 AM wali booking cancel ho gayi."


async def test_late_cancel_share_is_paid_out_early_cancel_is_not(db):
    _, slot, late = await seed_paid_booking(db, telegram_user_id=1)
    _, _, early = await seed_paid_booking(db, telegram_user_id=2)
    await cancel_booking(db, late.access_token, slot.starts_at - timedelta(hours=10))
    await cancel_booking(db, early.access_token, datetime.now(UTC))
    assert await schedule_completed_payouts(db) == 1
    payout = await db.scalar(select(Payout))
    assert payout.booking_id == late.id and payout.amount_paise == 60000


async def test_cancel_pages_preview_then_confirm_once(db, monkeypatch):
    from app.db.session import get_session
    from app.main import app
    from app.web import booking_routes

    _, slot, booking = await seed_paid_booking(db)
    slot.starts_at = datetime.now(UTC) + timedelta(hours=10)  # late: host keeps 20%
    await db.commit()
    notes = []

    async def fake_notify(session, b, text):
        notes.append(text)

    async def test_session():
        yield db

    monkeypatch.setattr(booking_routes, "notify_host", fake_notify)
    app.dependency_overrides[get_session] = test_session
    url = f"/b/{booking.access_token}"
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
            assert f'href="{url}/cancel"' in (await client.get(url)).text
            preview = (await client.get(f"{url}/cancel")).text
            assert "₹2,400" in preview and "₹600" in preview
            first = await client.post(f"{url}/cancel")
            again = await client.post(f"{url}/cancel")
            assert first.status_code == again.status_code == 303
            page = (await client.get(url)).text
            assert "CANCELLED" in page and f"{url}/cancel" not in page
            assert (await client.get(f"{url}/cancel")).status_code == 409
    finally:
        app.dependency_overrides.clear()
    assert len(notes) == 1 and "₹600 milenge" in notes[0]


async def test_database_refuses_a_second_refund_row(db):
    _, _, booking = await seed_paid_booking(db)
    db.add(LedgerEntry(booking_id=booking.id, type="REFUND", amount_paise=-1))
    await db.flush()
    db.add(LedgerEntry(booking_id=booking.id, type="REFUND", amount_paise=-1))
    with pytest.raises(IntegrityError):
        await db.flush()
    await db.rollback()
