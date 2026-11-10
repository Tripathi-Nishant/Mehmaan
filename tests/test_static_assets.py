from pathlib import Path

import httpx

from app.main import app

IMG = Path("app/web/static/img")


async def test_images_are_served():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        r = await client.get("/static/img/hero-pichhavai.webp")
    assert r.status_code == 200 and r.headers["content-type"] == "image/webp"


def test_raster_images_are_webp_and_at_most_300_kb():  # DESIGN3 technical rules
    rasters = [p for p in IMG.iterdir() if p.suffix.lower() != ".svg"]
    assert rasters
    for p in rasters:
        assert p.suffix == ".webp", p.name
        assert p.stat().st_size <= 300 * 1024, p.name
