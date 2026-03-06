"""
LiteLLM proxy client factory.

Creates an ``openai.OpenAI`` client pre-configured to talk to the LiteLLM
proxy endpoint, with the master (or virtual) key injected as the Bearer token.
"""

from __future__ import annotations

import os

import openai


def create_llm_client(
    base_url: str | None = None,
    api_key: str | None = None,
    timeout: float = 60.0,
    extra_headers: dict[str, str] | None = None,
) -> openai.OpenAI:
    """Return an OpenAI client pointing at the LiteLLM proxy.

    Args:
        base_url:      LiteLLM proxy URL, defaults to ``APP_LITELLM_BASE_URL``
                       env var or ``http://localhost:4000``.
        api_key:       Bearer token (LiteLLM master or virtual key), defaults
                       to ``LITELLM_MASTER_KEY`` env var.
        timeout:       Request timeout in seconds.
        extra_headers: Optional additional HTTP headers for every request.

    Returns:
        A configured ``openai.OpenAI`` client instance.
    """
    resolved_url = base_url or os.getenv("APP_LITELLM_BASE_URL", "http://localhost:4000")
    resolved_key = api_key or os.getenv("LITELLM_MASTER_KEY", "sk-litellm-master-key-change-me")

    default_headers: dict[str, str] = {
        "X-Forwarded-For": "app",  # propagated as metadata in LiteLLM logs
    }
    if extra_headers:
        default_headers.update(extra_headers)

    return openai.OpenAI(
        base_url=f"{resolved_url.rstrip('/')}/v1",
        api_key=resolved_key,
        timeout=timeout,
        default_headers=default_headers,
    )


def create_async_llm_client(
    base_url: str | None = None,
    api_key: str | None = None,
    timeout: float = 60.0,
    extra_headers: dict[str, str] | None = None,
) -> openai.AsyncOpenAI:
    """Return an async OpenAI client pointing at the LiteLLM proxy.

    See :func:`create_llm_client` for parameter descriptions.
    """
    resolved_url = base_url or os.getenv("APP_LITELLM_BASE_URL", "http://localhost:4000")
    resolved_key = api_key or os.getenv("LITELLM_MASTER_KEY", "sk-litellm-master-key-change-me")

    default_headers: dict[str, str] = {"X-Forwarded-For": "app"}
    if extra_headers:
        default_headers.update(extra_headers)

    return openai.AsyncOpenAI(
        base_url=f"{resolved_url.rstrip('/')}/v1",
        api_key=resolved_key,
        timeout=timeout,
        default_headers=default_headers,
    )
