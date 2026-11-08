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
