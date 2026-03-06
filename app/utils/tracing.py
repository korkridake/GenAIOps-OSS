"""
Langfuse tracing utilities.

Wraps the Langfuse Python SDK to provide a simple, context-manager-friendly
interface for creating traces, spans, and scores.
"""

from __future__ import annotations

import contextlib
import os
from typing import Any, Generator

from langfuse import Langfuse
from langfuse.model import ModelUsage


class TracingClient:
    """Thin wrapper around the Langfuse SDK.

    Args:
        public_key: Langfuse public key (``pk-lf-...``).
        secret_key: Langfuse secret key (``sk-lf-...``).
        host:       Langfuse server URL.
    """

    def __init__(
        self,
        public_key: str | None = None,
        secret_key: str | None = None,
        host: str | None = None,
    ) -> None:
        self._client = Langfuse(
            public_key=public_key or os.environ.get("LANGFUSE_PUBLIC_KEY", ""),
            secret_key=secret_key or os.environ.get("LANGFUSE_SECRET_KEY", ""),
            host=host or os.environ.get("LANGFUSE_HOST", "http://localhost:3000"),
        )

    # ── traces ────────────────────────────────────────────────────────────────

    @contextlib.contextmanager
    def trace(
        self,
        name: str,
        user_id: str | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> Generator[Any, None, None]:
        """Context manager that creates a Langfuse trace and yields it.

        The trace is automatically ended when the context exits.
        """
        t = self._client.trace(
            name=name,
            user_id=user_id,
            session_id=session_id,
            metadata=metadata or {},
            tags=tags or [],
        )
        try:
            yield t
        finally:
            t.update(status_message="completed")

    # ── spans ─────────────────────────────────────────────────────────────────

    def span(
        self,
        trace: Any,
        name: str,
        input_data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        """Create and return a span attached to *trace*."""
        return trace.span(name=name, input=input_data or {}, metadata=metadata or {})

    def end_span(self, span: Any, output_data: dict[str, Any] | None = None) -> None:
        """Finalise *span* with optional output."""
        span.end(output=output_data or {})

    def generation(
        self,
        trace: Any,
        name: str,
        model: str,
        prompt: list[dict[str, str]],
        completion: str,
        usage: ModelUsage | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        """Record a generation event on *trace*."""
        return trace.generation(
            name=name,
            model=model,
            input=prompt,
            output=completion,
            usage=usage,
            metadata=metadata or {},
        )

    # ── scoring ───────────────────────────────────────────────────────────────

    def score(
        self,
        trace_id: str,
        name: str,
        value: float,
        comment: str | None = None,
    ) -> None:
        """Attach a numeric score to an existing trace."""
        self._client.score(
            trace_id=trace_id,
            name=name,
            value=value,
            comment=comment,
        )

    # ── prompt management ─────────────────────────────────────────────────────

    def get_prompt(self, prompt_name: str, fallback: str = "") -> str:
        """Fetch a text prompt from Langfuse by name.

        Returns *fallback* if the prompt does not exist or the server is
        unreachable, so the application degrades gracefully.
        """
        try:
            prompt = self._client.get_prompt(prompt_name)
            return prompt.prompt  # type: ignore[attr-defined]
        except Exception:
            return fallback

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def flush(self) -> None:
        """Flush all buffered events to the Langfuse server."""
        self._client.flush()

    def shutdown(self) -> None:
        """Flush and shut down the background event processor."""
        self._client.flush()
