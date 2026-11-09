import httpx
import pytest
import respx

from app.config import Settings
from app.host_bot.intents import classify_reply
from app.host_bot.onboarding import OnboardingState
from app.host_bot.service import decide_voice_action

NO_LLM = Settings(_env_file=None)  # any LLM call fails -> UNCLEAR, so a hit proves the fast path
LLM = Settings(_env_file=None, llm_api_key="x", llm_model="m")
LLM_URL = "https://api.groq.com/openai/v1/chat/completions"


@pytest.mark.parametrize(
    "text, expected",
    [
        ("haan", "YES"),
        ("Haan ji.", "YES"),
        ("theek hai", "YES"),
        ("ठीक है।", "YES"),
        ("जी हाँ", "YES"),
        ("nahi", "NO"),
        ("galat hai", "NO"),
        ("नहीं", "NO"),
        ("daam badalna hai", "CHANGE"),
    ],
)
async def test_fast_path_needs_no_llm(text, expected):
    assert await classify_reply(text, NO_LLM) == expected


async def test_unknown_reply_without_llm_is_unclear():
    assert await classify_reply("samajh nahi aaya", NO_LLM) == "UNCLEAR"


@respx.mock
async def test_llm_fallback_classifies_longer_reply():
    respx.post(LLM_URL).respond(json={"choices": [{"message": {"content": "YES"}}]})
    assert await classify_reply("haan bilkul, sab sahi bataya aapne", LLM) == "YES"


@respx.mock
async def test_llm_garbage_is_unclear():
    respx.post(LLM_URL).respond(json={"choices": [{"message": {"content": "maybe?"}}]})
    assert await classify_reply("pata nahi kya bolun", LLM) == "UNCLEAR"


@respx.mock
async def test_llm_http_error_is_unclear():
    respx.post(LLM_URL).mock(return_value=httpx.Response(500))
    assert await classify_reply("pata nahi kya bolun", LLM) == "UNCLEAR"


RB, COL = OnboardingState.READBACK, OnboardingState.COLLECTING


@pytest.mark.parametrize(
    "state, next_field, intent, action",
    [
        (RB, None, "YES", "publish"),
        (RB, None, "NO", "change"),
        (RB, None, "CHANGE", "change"),
        (RB, None, "UNCLEAR", "ask_again"),
        (COL, "consent_voice_clip", "YES", "consent_yes"),
        (COL, "consent_voice_clip", "NO", "consent_no"),
        (COL, "consent_voice_clip", "UNCLEAR", "ask_again"),
        (COL, "consent_voice_clip", "CHANGE", "ask_again"),
        (COL, "landmark_hi", None, "landmark"),
        (COL, "city", None, "extract"),
    ],
)
def test_decide_voice_action(state, next_field, intent, action):
    assert decide_voice_action(state, next_field, intent) == action
