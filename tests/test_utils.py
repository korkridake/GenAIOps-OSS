"""
Unit tests for app/utils — no external services required.

All network calls are mocked so these tests run fully offline.
"""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import httpx
import pytest


# ══════════════════════════════════════════════════════════════════════════════
# llm_client.py
# ══════════════════════════════════════════════════════════════════════════════

class TestCreateLlmClient:
    """Tests for app.utils.llm_client.create_llm_client."""

    def test_default_base_url_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("APP_LITELLM_BASE_URL", "http://my-proxy:4000")
        from app.utils.llm_client import create_llm_client

        client = create_llm_client()
        assert "my-proxy" in str(client.base_url)

    def test_explicit_base_url_overrides_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("APP_LITELLM_BASE_URL", "http://env-proxy:4000")
        from app.utils.llm_client import create_llm_client

        client = create_llm_client(base_url="http://explicit-proxy:4000")
        assert "explicit-proxy" in str(client.base_url)

    def test_api_key_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LITELLM_MASTER_KEY", "sk-env-key")
        from app.utils.llm_client import create_llm_client

        client = create_llm_client()
        assert client.api_key == "sk-env-key"

    def test_explicit_api_key_overrides_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LITELLM_MASTER_KEY", "sk-env-key")
        from app.utils.llm_client import create_llm_client

        client = create_llm_client(api_key="sk-override-key")
        assert client.api_key == "sk-override-key"

    def test_base_url_ends_with_v1(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("APP_LITELLM_BASE_URL", "http://proxy:4000")
        from app.utils.llm_client import create_llm_client

        client = create_llm_client()
        assert str(client.base_url).rstrip("/").endswith("/v1")

    def test_extra_headers_are_included(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.utils.llm_client import create_llm_client

        client = create_llm_client(extra_headers={"X-Team-Id": "team-abc"})
        # The OpenAI SDK stores custom headers in _custom_headers and also
        # merges them into default_headers (case-preserved).
        headers = dict(client.default_headers)
        # header names are preserved as supplied when stored in default_headers
        assert headers.get("X-Team-Id") == "team-abc"

    def test_timeout_is_applied(self) -> None:
        from app.utils.llm_client import create_llm_client

        client = create_llm_client(timeout=42.0)
        # The OpenAI SDK stores timeout as a plain float when a scalar is given.
        assert client.timeout == 42.0

    def test_async_client_base_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("APP_LITELLM_BASE_URL", "http://async-proxy:4000")
        from app.utils.llm_client import create_async_llm_client

        client = create_async_llm_client()
        assert "async-proxy" in str(client.base_url)


# ══════════════════════════════════════════════════════════════════════════════
# tracing.py
# ══════════════════════════════════════════════════════════════════════════════

class TestTracingClient:
    """Tests for app.utils.tracing.TracingClient."""

    def _make_tracer(self) -> "TracingClient":
        from app.utils.tracing import TracingClient

        with patch("app.utils.tracing.Langfuse") as MockLangfuse:
            tracer = TracingClient(
                public_key="pk-lf-test",
                secret_key="sk-lf-test",
                host="http://langfuse-test:3000",
            )
            tracer._client = MockLangfuse.return_value
            return tracer

    def test_trace_context_manager_yields_trace(self) -> None:
        from app.utils.tracing import TracingClient

        with patch("app.utils.tracing.Langfuse") as MockLangfuse:
            mock_trace = MagicMock()
            mock_trace.id = "trace-123"
            MockLangfuse.return_value.trace.return_value = mock_trace

            tracer = TracingClient(public_key="pk", secret_key="sk", host="http://h:3000")
            with tracer.trace(name="test-trace") as t:
                assert t.id == "trace-123"

    def test_trace_calls_langfuse_with_name(self) -> None:
        from app.utils.tracing import TracingClient

        with patch("app.utils.tracing.Langfuse") as MockLangfuse:
            mock_lf = MockLangfuse.return_value
            mock_lf.trace.return_value = MagicMock()

            tracer = TracingClient(public_key="pk", secret_key="sk", host="http://h:3000")
            with tracer.trace(name="my-trace"):
                pass

            mock_lf.trace.assert_called_once()
            call_kwargs = mock_lf.trace.call_args.kwargs
            assert call_kwargs["name"] == "my-trace"

    def test_span_creates_span_on_trace(self) -> None:
        from app.utils.tracing import TracingClient

        with patch("app.utils.tracing.Langfuse"):
            tracer = TracingClient(public_key="pk", secret_key="sk", host="http://h:3000")
            mock_trace = MagicMock()
            mock_trace.span.return_value = MagicMock()

            span = tracer.span(mock_trace, name="test-span", input_data={"q": "hello"})
            mock_trace.span.assert_called_once_with(
                name="test-span", input={"q": "hello"}, metadata={}
            )

    def test_end_span_calls_end(self) -> None:
        from app.utils.tracing import TracingClient

        with patch("app.utils.tracing.Langfuse"):
            tracer = TracingClient(public_key="pk", secret_key="sk", host="http://h:3000")
            mock_span = MagicMock()
            tracer.end_span(mock_span, output_data={"result": "ok"})
            mock_span.end.assert_called_once_with(output={"result": "ok"})

    def test_score_calls_langfuse_score(self) -> None:
        from app.utils.tracing import TracingClient

        with patch("app.utils.tracing.Langfuse") as MockLangfuse:
            mock_lf = MockLangfuse.return_value
            tracer = TracingClient(public_key="pk", secret_key="sk", host="http://h:3000")
            tracer.score(trace_id="tid-1", name="quality", value=0.9, comment="good")
            mock_lf.score.assert_called_once_with(
                trace_id="tid-1", name="quality", value=0.9, comment="good"
            )

    def test_get_prompt_returns_fallback_on_error(self) -> None:
        from app.utils.tracing import TracingClient

        with patch("app.utils.tracing.Langfuse") as MockLangfuse:
            mock_lf = MockLangfuse.return_value
            mock_lf.get_prompt.side_effect = Exception("not found")
            tracer = TracingClient(public_key="pk", secret_key="sk", host="http://h:3000")
            result = tracer.get_prompt("missing-prompt", fallback="default text")
            assert result == "default text"

    def test_get_prompt_returns_prompt_text(self) -> None:
        from app.utils.tracing import TracingClient

        with patch("app.utils.tracing.Langfuse") as MockLangfuse:
            mock_lf = MockLangfuse.return_value
            mock_prompt = MagicMock()
            mock_prompt.prompt = "You are helpful."
            mock_lf.get_prompt.return_value = mock_prompt
            tracer = TracingClient(public_key="pk", secret_key="sk", host="http://h:3000")
            result = tracer.get_prompt("my-prompt")
            assert result == "You are helpful."

    def test_flush_calls_langfuse_flush(self) -> None:
        from app.utils.tracing import TracingClient

        with patch("app.utils.tracing.Langfuse") as MockLangfuse:
            mock_lf = MockLangfuse.return_value
            tracer = TracingClient(public_key="pk", secret_key="sk", host="http://h:3000")
            tracer.flush()
            mock_lf.flush.assert_called_once()


# ══════════════════════════════════════════════════════════════════════════════
# cost_tracker.py
# ══════════════════════════════════════════════════════════════════════════════

class TestCostTracker:
    """Tests for app.utils.cost_tracker.CostTracker."""

    def test_get_spend_summary_calls_correct_endpoint(self) -> None:
        from app.utils.cost_tracker import CostTracker

        with patch("app.utils.cost_tracker.httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"total_cost": 1.23}
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp

            tracker = CostTracker(base_url="http://litellm:4000", api_key="sk-key")
            result = tracker.get_spend_summary()

            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "/spend/logs" in call_args.args[0]
            assert result == {"total_cost": 1.23}

    def test_get_model_metrics_returns_list(self) -> None:
        from app.utils.cost_tracker import CostTracker

        data = [{"model": "gpt-4o", "requests": 10}, {"model": "gpt-3.5-turbo", "requests": 5}]
        with patch("app.utils.cost_tracker.httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = data
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp

            tracker = CostTracker(base_url="http://litellm:4000", api_key="sk-key")
            result = tracker.get_model_metrics()
            assert result == data

    def test_get_model_metrics_unwraps_data_key(self) -> None:
        from app.utils.cost_tracker import CostTracker

        inner = [{"model": "gpt-4o"}]
        with patch("app.utils.cost_tracker.httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"data": inner}
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp

            tracker = CostTracker(base_url="http://litellm:4000", api_key="sk-key")
            result = tracker.get_model_metrics()
            assert result == inner

    def test_returns_none_on_http_error(self) -> None:
        from app.utils.cost_tracker import CostTracker

        with patch("app.utils.cost_tracker.httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "403", request=MagicMock(), response=MagicMock(status_code=403)
            )
            mock_get.return_value = mock_resp

            tracker = CostTracker(base_url="http://litellm:4000", api_key="sk-key")
            result = tracker.get_spend_summary()
            assert result is None

    def test_returns_none_on_request_error(self) -> None:
        from app.utils.cost_tracker import CostTracker

        with patch("app.utils.cost_tracker.httpx.get") as mock_get:
            mock_get.side_effect = httpx.RequestError("connection refused")

            tracker = CostTracker(base_url="http://litellm:4000", api_key="sk-key")
            result = tracker.get_spend_summary()
            assert result is None

    def test_returns_empty_list_when_metrics_unavailable(self) -> None:
        from app.utils.cost_tracker import CostTracker

        with patch("app.utils.cost_tracker.httpx.get") as mock_get:
            mock_get.side_effect = httpx.RequestError("no connection")

            tracker = CostTracker(base_url="http://litellm:4000", api_key="sk-key")
            result = tracker.get_model_metrics()
            assert result == []

    def test_authorization_header_is_set(self) -> None:
        from app.utils.cost_tracker import CostTracker

        with patch("app.utils.cost_tracker.httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {}
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp

            tracker = CostTracker(base_url="http://litellm:4000", api_key="sk-mykey")
            tracker.get_spend_summary()

            _, kwargs = mock_get.call_args
            assert kwargs["headers"]["Authorization"] == "Bearer sk-mykey"

    def test_get_key_spend_passes_key_param(self) -> None:
        from app.utils.cost_tracker import CostTracker

        with patch("app.utils.cost_tracker.httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"key": "sk-vk"}
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp

            tracker = CostTracker(base_url="http://litellm:4000", api_key="sk-key")
            tracker.get_key_spend("sk-vk")

            _, kwargs = mock_get.call_args
            assert kwargs["params"]["key"] == "sk-vk"
