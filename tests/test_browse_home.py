from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx


# --- real Postgres: home shows 3 listings, "?all=1" and search show all; cards use own photo ---
async def test_home_limits_listings_and_cards_use_their_own_first_photo(db):
    from app.db.models import Host, Listing
    from app.db.session import get_session
    from app.main import app
    from app.media.store import Media

    host = Host(id=uuid4(), telegram_user_id=444, telegram_chat_id=444)
    db.add(host)
    await db.flush()
    now = datetime.now(UTC)
    listings = [
        Listing(
            id=uuid4(),
            host_id=host.id,
            status="LIVE",
            category="food",
            title_en=f"Home {i}",
            price_per_person_paise=100,
            city="Jaipur",
            area="Old City",
            created_at=now - timedelta(minutes=i),
        )
        for i in range(5)
    ]
    db.add_all(listings)
    await db.flush()
    newest = listings[0].id
    gate = Media(
        id=uuid4(),
        kind="gate_photo",
        content_type="image/jpeg",
        data=b"g",
        size_bytes=1,
        listing_id=newest,
        created_at=now - timedelta(days=2),
    )
    first = Media(
        id=uuid4(),
        kind="photo",
        content_type="image/jpeg",
        data=b"1",
        size_bytes=1,
        listing_id=newest,
        created_at=now - timedelta(days=1),
    )
    later = Media(
        id=uuid4(),
        kind="photo",
        content_type="image/jpeg",
        data=b"2",
        size_bytes=1,
        listing_id=newest,
        created_at=now,
    )
    db.add_all([gate, first, later])
    await db.commit()

    async def test_session():
        yield db

    app.dependency_overrides[get_session] = test_session
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
            home = (await client.get("/")).text
            assert [f"Home {i}" in home for i in range(5)] == [True, True, True, False, False]
            assert f"/media/{first.id}" in home
            assert f"/media/{gate.id}" not in home and f"/media/{later.id}" not in home
            assert home.count("Host photo coming soon") == 2  # listings without a photo
            assert 'href="/?all=1#experiences"' in home
            for url in ("/?all=1", "/?q=jaipur"):  # the full list and search are not capped
                page = (await client.get(url)).text
                assert all(f"Home {i}" in page for i in range(5)), url
    finally:
        app.dependency_overrides.clear()
