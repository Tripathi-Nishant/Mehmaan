import httpx
import pytest

from app.main import app
from app.web.errors import error_copy

HTML = {"Accept": "text/html,application/xhtml+xml"}


@pytest.mark.parametrize(
    "status, path, title, href",
    [
        (404, "/nope", "This door is closed", "/"),
        (404, "/listings/123", "This experience is not available", "/#experiences"),
        (404, "/b/tok", "We could not find this booking", "/"),
        (409, "/book", "That date just filled up", "/#experiences"),
        (409, "/pay/mock/o/verify", "Your reservation time ended", "/#experiences"),
        (409, "/b/tok/cancel", "This booking can no longer be cancelled", "/b/tok"),
        (403, "/b/tok/translate", "Language help opens once your host confirms", "/b/tok"),
        (422, "/book", "Some details were missing", None),
        (500, "/anything", "Something went wrong on our side", "/"),
    ],
)
def test_error_copy_picks_a_message_and_a_next_step(status, path, title, href):
    copy = error_copy(status, path)
    assert copy["title"] == title
    assert copy["href"] == href  # None means "go back" (history)
    assert copy["action"]


async def get(path, headers=None, method="GET", data=None):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        return await client.request(method, path, headers=headers, data=data)


async def test_browser_gets_a_designed_404_with_the_right_status():
    r = await get("/nope", HTML)
    assert r.status_code == 404 and "text/html" in r.headers["content-type"]
    assert "This door is closed" in r.text and 'href="/"' in r.text


async def test_api_clients_still_get_json():
    r = await get("/nope")
    assert r.status_code == 404 and r.json() == {"detail": "Not Found"}


async def test_mangled_listing_link_is_not_found_not_a_form_error():
    r = await get("/listings/abc", HTML)
    assert r.status_code == 404 and "This experience is not available" in r.text


async def test_browser_form_errors_get_a_page():
    r = await get("/book", HTML, method="POST", data={"name": "x"})
    assert r.status_code == 422 and "Some details were missing" in r.text
