import httpx
import pytest
from test_host_booking_reply import seed_paid_booking

from app.db.session import get_session
from app.interpreter.service import LANGUAGES, translation_prompt
from app.llm.client import LlmOutputError
from app.main import app
from app.web import booking_routes


def test_prompt_names_both_languages_and_keeps_numbers():
    prompt = translation_prompt("Where is the gate?", "fr", "hi")
    assert "French" in prompt and "Hindi" in prompt and "numbers" in prompt
    assert set(LANGUAGES) == {"en", "fr", "de", "es", "it", "ja", "hi"}


@pytest.fixture
async def client(db, monkeypatch):
    calls = []

    async def fake_translate(text, source, target, settings):
        calls.append((text, source, target))
        if text == "boom":
            raise LlmOutputError("down")
        return f"[{target}] {text}"

    async def test_session():
        yield db

    monkeypatch.setattr(booking_routes, "translate_between", fake_translate)
    app.dependency_overrides[get_session] = test_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        c.calls = calls
        yield c
    app.dependency_overrides.clear()


async def confirmed_token(db):
    _, _, booking = await seed_paid_booking(db)
    booking.status = "CONFIRMED"
    await db.commit()
    return booking.access_token


async def test_confirmed_booking_can_translate(client, db):
    token = await confirmed_token(db)
    page = await client.get(f"/b/{token}/translate")
    assert page.status_code == 200 and 'id="translate-form"' in page.text
    r = await client.post(
        f"/b/{token}/translate", json={"text": " Thank you! ", "source": "en", "target": "hi"}
    )
    assert r.status_code == 200
    assert r.json() == {"source_text": "Thank you!", "translated_text": "[hi] Thank you!"}


async def test_unconfirmed_booking_is_refused(client, db):
    _, _, booking = await seed_paid_booking(db)  # still waiting for the host
    assert (await client.get(f"/b/{booking.access_token}/translate")).status_code == 403
    r = await client.post(
        f"/b/{booking.access_token}/translate", json={"text": "hi", "source": "en", "target": "hi"}
    )
    assert r.status_code == 403 and client.calls == []


@pytest.mark.parametrize(
    "body",
    [
        {"text": "x" * 501, "source": "en", "target": "hi"},
        {"text": "   ", "source": "en", "target": "hi"},
        {"text": "hello", "source": "en", "target": "fr"},  # one side must be Hindi
        {"text": "hello", "source": "xx", "target": "hi"},
    ],
)
async def test_bad_requests_never_reach_the_model(client, db, body):
    token = await confirmed_token(db)
    assert (await client.post(f"/b/{token}/translate", json=body)).status_code == 422
    assert client.calls == []


async def test_model_failure_is_a_friendly_503(client, db):
    token = await confirmed_token(db)
    r = await client.post(
        f"/b/{token}/translate", json={"text": "boom", "source": "en", "target": "hi"}
    )
    assert r.status_code == 503 and "try again" in r.json()["detail"]
