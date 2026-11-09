from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest

from app.booking.host_reply import location_reveal
from app.web.booking_routes import templates

LISTING = SimpleNamespace(
    location_lat=26.9239,
    location_lng=75.8267,
    landmark_en="The lane behind Hawa Mahal",
    landmark_hi="Hawa Mahal ke peeche wali gali",
    title_en="Dal baati in Jaipur",
    description_hi="Dal baati banana",
)
MAP = "https://www.google.com/maps?q=26.9239,75.8267"


def booking(status):
    return SimpleNamespace(status=status, access_token="tok")


def test_confirmed_booking_reveals_map_and_english_landmark():
    assert location_reveal(booking("CONFIRMED"), LISTING) == {
        "map_url": MAP,
        "landmark": "The lane behind Hawa Mahal",
    }


def test_landmark_falls_back_to_hindi():
    listing = SimpleNamespace(**{**vars(LISTING), "landmark_en": None})
    assert location_reveal(booking("CONFIRMED"), listing)["landmark"] == LISTING.landmark_hi


@pytest.mark.parametrize("status", ["HELD", "PAID_PENDING_HOST", "EXPIRED", "REFUNDED"])
def test_not_revealed_before_confirmation(status):
    assert location_reveal(booking(status), LISTING) is None


def render(status):
    b = booking(status)
    return templates.get_template("booking.html").render(
        booking=b, listing=LISTING, location=location_reveal(b, LISTING)
    )


def test_template_shows_map_only_when_confirmed():
    shown = render("CONFIRMED")
    assert MAP in shown and "The lane behind Hawa Mahal" in shown
    hidden = render("PAID_PENDING_HOST")
    assert "maps?q=" not in hidden and "26.9239" not in hidden
    assert "Hawa Mahal" not in hidden
    assert "after the host confirms" in hidden


# --- real Postgres: the gate photo is never served by /media -------------------------------
async def test_gate_photo_is_never_served_but_experience_photo_is(db):
    from app.db.models import Host, Listing
    from app.db.session import get_session
    from app.main import app
    from app.media.store import Media

    host = Host(id=uuid4(), telegram_user_id=333, telegram_chat_id=333)
    listing = Listing(
        id=uuid4(),
        host_id=host.id,
        status="LIVE",
        category="food",
        price_per_person_paise=1,
        city="Jaipur",
        area="Old City",
    )
    gate = Media(id=uuid4(), kind="gate_photo", content_type="image/jpeg", data=b"g", size_bytes=1)
    food = Media(id=uuid4(), kind="photo", content_type="image/jpeg", data=b"f", size_bytes=1)
    for row in (host, listing, gate, food):
        db.add(row)
        await db.flush()
    gate.listing_id = food.listing_id = listing.id
    await db.commit()

    async def test_session():
        yield db

    app.dependency_overrides[get_session] = test_session
    try:
        transport = httpx.ASGITransport(app=app)  # no lifespan: bot and job loop stay off
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
            assert (await client.get(f"/media/{gate.id}")).status_code == 404
            served = await client.get(f"/media/{food.id}")
            assert served.status_code == 200 and served.content == b"f"
    finally:
        app.dependency_overrides.clear()
