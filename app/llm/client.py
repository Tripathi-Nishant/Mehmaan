import json
from pathlib import Path

import httpx
from pydantic import ValidationError

from app.config import Settings
from app.llm.schemas import ExtractionResult


class LlmOutputError(RuntimeError):
    pass


EXTRACTION_PROMPT = (
    Path(__file__).with_name("prompts").joinpath("extraction.txt").read_text(encoding="utf-8")
)


async def extract_listing_fields(transcript: str, settings: Settings) -> ExtractionResult:
    if not settings.llm_api_key or not settings.llm_model:
        raise LlmOutputError("LLM_API_KEY and LLM_MODEL are required for extraction")
    body = {
        "model": settings.llm_model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [{"role": "user", "content": EXTRACTION_PROMPT.format(transcript=transcript)}],
    }
    headers = {"Authorization": f"Bearer {settings.llm_api_key}"}
    async with httpx.AsyncClient(base_url=settings.llm_base_url, timeout=30) as client:
        for attempt in range(2):
            response = await client.post("/chat/completions", headers=headers, json=body)
            try:
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                return ExtractionResult.model_validate(json.loads(content))
            except (httpx.HTTPError, KeyError, TypeError, ValueError, ValidationError) as exc:
                if attempt == 1:
                    raise LlmOutputError("LLM extraction failed validation after retry") from exc
                body["messages"].append(
                    {"role": "user", "content": "Return valid JSON matching the fields."}
                )
    raise LlmOutputError("LLM extraction failed")


async def complete_text(prompt: str, settings: Settings) -> str:
    if not settings.llm_api_key or not settings.llm_model:
        raise LlmOutputError("LLM_API_KEY and LLM_MODEL are required")
    body = {
        "model": settings.llm_model,
        "temperature": 0.2,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {"Authorization": f"Bearer {settings.llm_api_key}"}
    async with httpx.AsyncClient(base_url=settings.llm_base_url, timeout=10) as client:
        response = await client.post("/chat/completions", headers=headers, json=body)
        try:
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise LlmOutputError("LLM text completion failed") from exc
