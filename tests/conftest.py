"""
pytest fixtures shared across the test suite.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _set_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inject dummy environment variables so modules load without real secrets."""
    defaults = {
        "APP_LITELLM_BASE_URL": "http://litellm-test:4000",
        "LITELLM_MASTER_KEY": "sk-test-master-key",
        "LANGFUSE_PUBLIC_KEY": "pk-lf-test",
        "LANGFUSE_SECRET_KEY": "sk-lf-test",
        "LANGFUSE_HOST": "http://langfuse-test:3000",
        "OPENAI_API_KEY": "sk-openai-test",
    }
    for key, value in defaults.items():
        monkeypatch.setenv(key, value)


@pytest.fixture()
def mock_openai_client() -> MagicMock:
    """A mock openai.OpenAI instance."""
    client = MagicMock()
    client.chat.completions.create.return_value = _fake_completion()
    return client


@pytest.fixture()
def mock_langfuse_client() -> MagicMock:
    """A mock Langfuse instance."""
    lf = MagicMock()
    trace = MagicMock()
    trace.id = "trace-test-id"
    lf.trace.return_value = trace
    return lf


# ── internal helpers ──────────────────────────────────────────────────────────

def _fake_completion() -> MagicMock:
    choice = MagicMock()
    choice.message.content = "This is a test response."
    usage = MagicMock()
    usage.prompt_tokens = 10
    usage.completion_tokens = 8
    usage.total_tokens = 18
    completion = MagicMock()
    completion.choices = [choice]
    completion.usage = usage
    completion.model = "gpt-4o-mini"
    return completion
