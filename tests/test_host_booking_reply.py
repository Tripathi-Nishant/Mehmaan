from datetime import UTC, datetime

import pytest

from app.host_bot.service import booking_prompt_text, route_host_reply


def test_booking_prompt_names_date_guests_and_payout():
    text = booking_prompt_text(datetime(2026, 11, 14, 5, 30, tzinfo=UTC), 2, 255000)
    assert text == (
        "Sat 14 Nov, 11:00 AM ke liye 2 mehmaan ki booking aayi hai. "
        "Aapko ₹2,550 milenge (test). Haan ya nahi?"
    )


def test_booking_prompt_includes_dietary_note_before_the_question():
    starts = datetime(2026, 11, 14, 5, 30, tzinfo=UTC)
    text = booking_prompt_text(starts, 2, 255000, "Peanut allergy")
    assert text.endswith('Mehmaan ne khaane ke baare mein bataya: "Peanut allergy". Haan ya nahi?')
    assert booking_prompt_text(starts, 2, 255000, None).endswith("(test). Haan ya nahi?")


def test_single_guest_prompt():
    assert "1 mehmaan" in booking_prompt_text(datetime(2026, 11, 14, 5, 30, tzinfo=UTC), 1, 1)


@pytest.mark.parametrize(
    "has_pending, intent, action",
    [
        (True, "YES", "confirm"),
        (True, "NO", "decline"),
        (True, "UNCLEAR", "ask_again"),
        (True, "CHANGE", "ask_again"),
        (False, "YES", "onboarding"),
        (False, "NO", "onboarding"),
    ],
)
def test_route_host_reply(has_pending, intent, action):
    assert route_host_reply(has_pending, intent) == action


# --- real Postgres (tests/conftest.py `db` fixture) ---------------------------------------
from datetime import timedelta  # noqa: E402
from uuid import uuid4  # noqa: E402

from sqlalchemy import func, select  # noqa: E402

from app.booking.host_reply import answer_booking, pending_booking_for  # noqa: E402
from app.db.models import (  # noqa: E402
    Booking,
    Host,
    LedgerEntry,
    Listing,
    Payment,
    Slot,
    Traveler,
)


async def seed_paid_booking(db, telegram_user_id=111, guests=2):
    """A LIVE listing with one slot and one paid booking waiting for the host."""
    host = Host(id=uuid4(), telegram_user_id=telegram_user_id, telegram_chat_id=telegram_user_id)
    listing = Listing(
        id=uuid4(),
        host_id=host.id,
        status="LIVE",
        category="food",
        price_per_person_paise=150000,
        city="Jaipur",
        area="Old City",
    )
    slot = Slot(
        id=uuid4(),
        listing_id=listing.id,
        starts_at=datetime.now(UTC) + timedelta(days=3),
        capacity=4,
        booked_count=guests,
    )
    traveler = Traveler(id=uuid4(), name="Asha", email="a@example.com")
    booking = Booking(
        id=uuid4(),
        slot_id=slot.id,
        traveler_id=traveler.id,
        guests=guests,
        status="PAID_PENDING_HOST",
        amount_paise=300000,
        commission_paise=45000,
        host_payout_paise=255000,
    )
    payment = Payment(
        booking_id=booking.id,
        provider_order_id=f"mock_order_{uuid4().hex}",
        provider_payment_id=f"mock_payment_{uuid4().hex}",
        amount_paise=300000,
        status="CAPTURED",
    )
    capture = [("CHARGE", 300000), ("COMMISSION", -45000), ("HOST_PAYABLE", -255000)]
    ledger = [
        LedgerEntry(booking_id=booking.id, host_id=host.id, type=t, amount_paise=a)
        for t, a in capture
    ]
    for row in (host, listing, slot, traveler, booking, payment, *ledger):
        db.add(row)
        await db.flush()  # parents before children (no ORM relationships to order them)
    await db.commit()
    return host, slot, booking


async def test_haan_confirms_the_pending_booking(db):
    host, _, booking = await seed_paid_booking(db)
    pending = await pending_booking_for(db, host.id)
    assert pending.id == booking.id
    reply = await answer_booking(db, pending, "confirm")
    assert "confirm" in reply
    assert (await db.get(Booking, booking.id, populate_existing=True)).status == "CONFIRMED"


async def test_nahi_declines_refunds_and_releases_seats(db):
    host, slot, booking = await seed_paid_booking(db, guests=2)
    await answer_booking(db, await pending_booking_for(db, host.id), "decline")
    assert (await db.get(Booking, booking.id, populate_existing=True)).status == "REFUNDED"
    payment = await db.scalar(select(Payment).where(Payment.booking_id == booking.id))
    assert payment.status == "REFUNDED"
    refunds = (
        await db.scalars(
            select(LedgerEntry).where(
                LedgerEntry.booking_id == booking.id, LedgerEntry.type == "REFUND"
            )
        )
    ).all()
    assert len(refunds) == 1
    balance = await db.scalar(
        select(func.sum(LedgerEntry.amount_paise)).where(LedgerEntry.booking_id == booking.id)
    )
    assert balance == 0  # capture + reversal net out
    assert (await db.get(Slot, slot.id, populate_existing=True)).booked_count == 0


async def test_hold_stores_trimmed_dietary_note_and_blank_as_null(db):
    from app.booking.db_service import create_hold

    _, slot, _ = await seed_paid_booking(db)  # 2 of 4 seats left
    now = datetime.now(UTC)
    noted = await create_hold(db, slot.id, "Sophie", "s@x.test", 1, 15, now, " Peanut allergy ")
    blank = await create_hold(db, slot.id, "Tom", "t@x.test", 1, 15, now, "   ")
    assert noted.dietary_notes == "Peanut allergy"
    assert blank.dietary_notes is None


async def test_nothing_pending_goes_to_onboarding(db):
    host, _, booking = await seed_paid_booking(db)
    await answer_booking(db, await pending_booking_for(db, host.id), "confirm")
    assert await pending_booking_for(db, host.id) is None  # answered: no longer pending
    assert route_host_reply(False, "YES") == "onboarding"  # -> T7 "already live" reply


async def test_only_the_hosts_own_booking_is_pending(db):
    await seed_paid_booking(db, telegram_user_id=111)
    other_host, _, _ = await seed_paid_booking(db, telegram_user_id=222)
    pending = await pending_booking_for(db, other_host.id)
    slot = await db.get(Slot, pending.slot_id)
    listing = await db.get(Listing, slot.listing_id)
    assert listing.host_id == other_host.id


# --- booking_reply: the path both text and voice handlers use -----------------------------
from app.booking.host_reply import booking_reply  # noqa: E402
from app.config import Settings  # noqa: E402

NO_LLM = Settings(_env_file=None)  # proves plain haan/nahi never needs the LLM


async def test_spoken_haan_confirms(db):
    host, _, booking = await seed_paid_booking(db)
    reply = await booking_reply(db, await pending_booking_for(db, host.id), "Haan ji.", NO_LLM)
    assert "confirm" in reply
    assert (await db.get(Booking, booking.id, populate_existing=True)).status == "CONFIRMED"


async def test_spoken_nahi_declines(db):
    host, _, booking = await seed_paid_booking(db)
    await booking_reply(db, await pending_booking_for(db, host.id), "नहीं", NO_LLM)
    assert (await db.get(Booking, booking.id, populate_existing=True)).status == "REFUNDED"


async def test_unclear_reply_re_asks_with_the_booking_details(db):
    host, _, booking = await seed_paid_booking(db)
    reply = await booking_reply(db, await pending_booking_for(db, host.id), "kaun?", NO_LLM)
    assert reply.startswith("Kripya haan ya nahi boliye.")
    assert "2 mehmaan" in reply and "₹2,550" in reply
    assert (await db.get(Booking, booking.id, populate_existing=True)).status == "PAID_PENDING_HOST"
