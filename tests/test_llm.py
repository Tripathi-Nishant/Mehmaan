import httpx
import pytest
import respx

from app.config import Settings
from app.llm.client import LlmOutputError, extract_listing_fields


@pytest.mark.asyncio
@respx.mock
async def test_extraction_retries_invalid_json():
    route = respx.post("https://api.groq.com/openai/v1/chat/completions")
    route.side_effect = [
        httpx.Response(200, json={"choices": [{"message": {"content": "not json"}}]}),
        httpx.Response(200, json={"choices": [{"message": {"content": '{"category":"food"}'}}]}),
    ]
    result = await extract_listing_fields(
        "main khana banati hoon", Settings(llm_api_key="x", llm_model="m")
    )
    assert result.category == "food"
    assert route.call_count == 2


@pytest.mark.asyncio
async def test_extraction_requires_config():
    with pytest.raises(LlmOutputError):
        await extract_listing_fields("hello", Settings(_env_file=None))


VOICE_FIELDS = (
    "category",
    "activity_description",
    "food_type",
    "available_weekdays",
    "start_time_local",
    "duration_min",
    "max_guests",
    "price_per_person_paise",
    "city",
    "area",
)


def test_prompt_covers_spoken_fields_only():
    from app.host_bot.onboarding import REQUIRED_FIELDS
    from app.llm.client import EXTRACTION_PROMPT

    assert all(name in EXTRACTION_PROMPT for name in VOICE_FIELDS)
    assert "cancellation_rule" not in EXTRACTION_PROMPT
    assert "cancellation_rule" not in REQUIRED_FIELDS


@pytest.mark.asyncio
@respx.mock
async def test_retry_sends_validation_error_back():
    route = respx.post("https://api.groq.com/openai/v1/chat/completions")
    route.side_effect = [
        httpx.Response(200, json={"choices": [{"message": {"content": '{"max_guests":0}'}}]}),
        httpx.Response(200, json={"choices": [{"message": {"content": '{"max_guests":4}'}}]}),
    ]
    await extract_listing_fields("chaar log", Settings(llm_api_key="x", llm_model="m"))
    retry_body = route.calls[1].request.content.decode()
    assert "max_guests" in retry_body and "greater than or equal to 1" in retry_body
