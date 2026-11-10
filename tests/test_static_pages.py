import httpx
import pytest

from app.main import app

PAGES = {
    "/about": "About Mehmaan",
    "/privacy": "Privacy",
    "/terms": "Terms",
    "/cancellation-policy": "Cancellation policy",
}


@pytest.mark.parametrize("path, heading", PAGES.items())
async def test_static_page_renders_and_is_linked_from_footer(path, heading):
    transport = httpx.ASGITransport(app=app)  # no lifespan: bot and job loop stay off
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        page = await client.get(path)
    assert page.status_code == 200
    assert heading in page.text
    assert f'href="{path}"' in page.text  # nav/footer link every policy page
    assert "TEST" in page.text


async def test_cancellation_policy_states_the_real_rules():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        text = (await client.get("/cancellation-policy")).text
    assert "48 hours" in text and "80%" in text and "20%" in text
