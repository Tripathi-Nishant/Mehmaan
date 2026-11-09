import json

import httpx
import respx

from app.config import Settings
from app.host_bot.service import fallback_copy, listing_copy

LLM = Settings(_env_file=None, llm_api_key="x", llm_model="m")
LLM_URL = "https://api.groq.com/openai/v1/chat/completions"
FIELDS = {
    "category": "food",
    "activity_description": "Rajasthani dal baati banana",
    "food_type": "veg",
    "duration_min": 180,
    "max_guests": 4,
    "city": "Jaipur",
    "area": "Old City",
    "landmark_hi": "Hawa Mahal ke peeche wali gali",
}
GOOD = {
    "title_en": "Cook Rajasthani dal baati in a Jaipur home",
    "description_en": "Learn to cook dal baati with a home cook in Jaipur's Old City.",
    "landmark_en": "The lane behind Hawa Mahal",
}


def reply(content: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


@respx.mock
async def test_llm_copy_is_used_when_valid():
    respx.post(LLM_URL).mock(return_value=reply(json.dumps(GOOD)))
    copy = await listing_copy(FIELDS, LLM)
    assert copy.model_dump() == GOOD


@respx.mock
async def test_invalid_llm_output_twice_falls_back_to_template():
    route = respx.post(LLM_URL)
    route.side_effect = [reply("not json"), reply(json.dumps({"title_en": "x"}))]
    copy = await listing_copy(FIELDS, LLM)
    assert copy == fallback_copy(FIELDS)
    assert route.call_count == 2


@respx.mock
async def test_network_error_falls_back_to_template():
    respx.post(LLM_URL).mock(side_effect=httpx.ConnectError("down"))
    assert await listing_copy(FIELDS, LLM) == fallback_copy(FIELDS)


async def test_no_llm_config_falls_back_to_template():
    assert await listing_copy(FIELDS, Settings(_env_file=None)) == fallback_copy(FIELDS)


def test_fallback_copy_uses_the_facts_and_hindi_landmark():
    copy = fallback_copy(FIELDS)
    assert "Jaipur" in copy.title_en and "Old City" in copy.title_en
    assert "180-minute" in copy.description_en and "vegetarian" in copy.description_en
    assert "4 guests" in copy.description_en
    assert copy.landmark_en == FIELDS["landmark_hi"]
