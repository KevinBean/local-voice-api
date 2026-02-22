"""
Local Voice API — LLM module
Dual-provider abstraction: Ollama (default) or OpenAI.
Callers can pass provider= per-request to override the server default.
"""
from typing import AsyncGenerator, Optional

import httpx

import config

# ── Lazy singleton clients ────────────────────────────────────────────────────

_openai_client = None
_ollama_client = None


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        from openai import AsyncOpenAI
        _openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    return _openai_client


def _get_ollama_client():
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = httpx.AsyncClient(
            base_url=config.OLLAMA_BASE_URL,
            timeout=120.0,
        )
    return _ollama_client


# ── Public API ────────────────────────────────────────────────────────────────

async def chat(
    messages: list,
    model: Optional[str] = None,
    provider: Optional[str] = None,
) -> str:
    """Send a chat request and return the assistant's text response."""
    p = provider or config.LLM_PROVIDER
    if p == "openai":
        return await _chat_openai(messages, model or config.OPENAI_MODEL)
    return await _chat_ollama(messages, model or config.OLLAMA_MODEL)


async def chat_stream(
    messages: list,
    model: Optional[str] = None,
    provider: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """Yield text chunks from LLM as they arrive."""
    p = provider or config.LLM_PROVIDER
    if p == "openai":
        async for chunk in _chat_openai_stream(messages, model or config.OPENAI_MODEL):
            yield chunk
    else:
        async for chunk in _chat_ollama_stream(messages, model or config.OLLAMA_MODEL):
            yield chunk


async def _chat_openai_stream(messages: list, model: str) -> AsyncGenerator[str, None]:
    client = _get_openai_client()
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
    )
    async for chunk in response:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content


async def _chat_ollama_stream(messages: list, model: str) -> AsyncGenerator[str, None]:
    client = _get_ollama_client()
    async with client.stream(
        "POST",
        "/api/chat",
        json={"model": model, "messages": messages, "stream": True},
    ) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if not line:
                continue
            import json
            data = json.loads(line)
            content = data.get("message", {}).get("content", "")
            if content:
                yield content


async def _chat_openai(messages: list, model: str) -> str:
    client = _get_openai_client()
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
    )
    return response.choices[0].message.content


async def _chat_ollama(messages: list, model: str) -> str:
    client = _get_ollama_client()
    response = await client.post(
        "/api/chat",
        json={
            "model": model,
            "messages": messages,
            "stream": False,
        },
    )
    response.raise_for_status()
    data = response.json()
    return data["message"]["content"]
