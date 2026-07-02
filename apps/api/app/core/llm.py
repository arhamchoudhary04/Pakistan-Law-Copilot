"""LLM generation provider.

Groq exposes an OpenAI-compatible ``/chat/completions`` endpoint, so we talk to
it directly with httpx and stream token deltas back to the caller. Keeping this
behind a small interface means the provider can be swapped later without
touching the agent pipeline.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from functools import lru_cache

import httpx

from app.core.config import get_settings


class LLMError(RuntimeError):
    """Raised when the LLM provider is misconfigured or returns an error."""


class GroqLLM:
    """Streaming client for Groq's OpenAI-compatible chat completions API."""

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> AsyncIterator[str]:
        """Yield content token strings from a streamed chat completion."""
        if not self.api_key:
            raise LLMError(
                "GROQ_API_KEY is not set. Add it to your .env to enable generation."
            )

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}/chat/completions"

        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as resp:
                if resp.status_code >= 400:
                    body = (await resp.aread()).decode("utf-8", "replace")
                    raise LLMError(f"Groq API error {resp.status_code}: {body}")
                async for line in resp.aiter_lines():
                    token = _parse_sse_line(line)
                    if token is not None:
                        yield token


def _parse_sse_line(line: str) -> str | None:
    """Extract a content delta from one OpenAI-style SSE line, if present."""
    if not line or not line.startswith("data:"):
        return None
    data = line[len("data:") :].strip()
    if not data or data == "[DONE]":
        return None
    try:
        chunk = json.loads(data)
    except json.JSONDecodeError:
        return None
    choices = chunk.get("choices") or []
    if not choices:
        return None
    delta = choices[0].get("delta") or {}
    return delta.get("content")


@lru_cache
def get_llm() -> GroqLLM:
    """Return a cached LLM client built from application settings."""
    settings = get_settings()
    return GroqLLM(
        api_key=settings.groq_api_key,
        base_url=settings.groq_base_url,
        model=settings.groq_model,
    )
