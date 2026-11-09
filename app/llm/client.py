import json
from pathlib import Path

import httpx
from pydantic import BaseModel, ValidationError

from app.config import Settings
from app.llm.schemas import ExtractionResult, ListingCopy


class LlmOutputError(RuntimeError):
    pass


def _prompt(name: str) -> str:
    return Path(__file__).with_name("prompts").joinpath(name).read_text(encoding="utf-8")


EXTRACTION_PROMPT = _prompt("extraction.txt")
LISTING_COPY_PROMPT = _prompt("listing_copy.txt")


async def _complete_json[T: BaseModel](prompt: str, model: type[T], settings: Settings) -> T:
    """Ask for JSON, validate with `model`; on any failure retry once with the error, then raise."""
    if not settings.llm_api_key or not settings.llm_model:
        raise LlmOutputError("LLM_API_KEY and LLM_MODEL are required")
    body = {
        "model": settings.llm_model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {"Authorization": f"Bearer {settings.llm_api_key}"}
    async with httpx.AsyncClient(base_url=settings.llm_base_url, timeout=30) as client:
        for attempt in range(2):
            try:
                response = await client.post("/chat/completions", headers=headers, json=body)
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                return model.model_validate(json.loads(content))
            except (httpx.HTTPError, KeyError, TypeError, ValueError, ValidationError) as exc:
                if attempt == 1:
                    raise LlmOutputError("LLM JSON output failed after retry") from exc
                body["messages"].append(
                    {
                        "role": "user",
                        "content": f"Your output was invalid: {exc}. "
                        "Return valid JSON matching the fields.",
                    }
                )
    raise LlmOutputError("LLM JSON output failed")


async def extract_listing_fields(transcript: str, settings: Settings) -> ExtractionResult:
    prompt = EXTRACTION_PROMPT.format(transcript=transcript)
    return await _complete_json(prompt, ExtractionResult, settings)


async def generate_listing_copy(facts: dict, settings: Settings) -> ListingCopy:
    prompt = LISTING_COPY_PROMPT.format(facts=json.dumps(facts, ensure_ascii=False))
    return await _complete_json(prompt, ListingCopy, settings)


async def complete_text(prompt: str, settings: Settings) -> str:
    if not settings.llm_api_key or not settings.llm_model:
        raise LlmOutputError("LLM_API_KEY and LLM_MODEL are required")
    body = {
        "model": settings.llm_model,
        "temperature": 0.2,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {"Authorization": f"Bearer {settings.llm_api_key}"}
    try:
        async with httpx.AsyncClient(base_url=settings.llm_base_url, timeout=10) as client:
            response = await client.post("/chat/completions", headers=headers, json=body)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        # Includes connect errors/timeouts, so callers only need to handle LlmOutputError.
        raise LlmOutputError("LLM text completion failed") from exc
