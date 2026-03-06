"""
GenAIOps demo application.

Demonstrates:
- Chat completions via the LiteLLM proxy (OpenAI-compatible)
- Distributed tracing with Langfuse
- Prompt management via the Langfuse SDK
- Cost tracking via LiteLLM's spend API
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

load_dotenv()

from app.utils.llm_client import create_llm_client
from app.utils.tracing import TracingClient
from app.utils.cost_tracker import CostTracker


# ── helpers ──────────────────────────────────────────────────────────────────

def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        print(f"[warn] {name} is not set — skipping example that requires it.")
        return ""
    return value


# ── examples ─────────────────────────────────────────────────────────────────

def example_basic_chat() -> None:
    """Send a basic chat completion through the LiteLLM proxy."""
    print("\n" + "=" * 60)
    print("EXAMPLE 1 — Basic chat completion via LiteLLM proxy")
    print("=" * 60)

    client = create_llm_client()
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is LLMOps in one sentence?"},
            ],
            max_tokens=100,
        )
        content = response.choices[0].message.content
        print(f"Model   : {response.model}")
        print(f"Response: {content}")
        usage = response.usage
        if usage:
            print(f"Tokens  : prompt={usage.prompt_tokens}, completion={usage.completion_tokens}")
    except Exception as exc:
        print(f"[error] Chat completion failed: {exc}")


def example_with_tracing() -> None:
    """Chat completion with explicit Langfuse tracing."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2 — Chat completion with Langfuse tracing")
    print("=" * 60)

    pk = _require_env("LANGFUSE_PUBLIC_KEY")
    sk = _require_env("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")

    if not pk or not sk:
        return

    tracer = TracingClient(public_key=pk, secret_key=sk, host=host)
    client = create_llm_client()

    with tracer.trace(name="demo-chat", user_id="demo-user") as trace:
        span = tracer.span(trace, name="llm-call", input_data={"question": "What is RAG?"})
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant."},
                    {"role": "user", "content": "Explain Retrieval-Augmented Generation briefly."},
                ],
                max_tokens=150,
                extra_headers={"X-Langfuse-Trace-Id": trace.id},
            )
            answer = response.choices[0].message.content
            tracer.end_span(span, output_data={"answer": answer})
            print(f"Trace ID : {trace.id}")
            print(f"Response : {answer}")
        except Exception as exc:
            tracer.end_span(span, output_data={"error": str(exc)})
            print(f"[error] Traced chat failed: {exc}")

    # Flush buffered events to Langfuse
    tracer.flush()
    print("Langfuse trace flushed.")


def example_prompt_management() -> None:
    """Fetch a prompt from Langfuse and use it in a chat completion."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3 — Prompt management via Langfuse")
    print("=" * 60)

    pk = _require_env("LANGFUSE_PUBLIC_KEY")
    sk = _require_env("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")

    if not pk or not sk:
        return

    tracer = TracingClient(public_key=pk, secret_key=sk, host=host)
    client = create_llm_client()

    # Attempt to fetch a managed prompt; fall back to a hard-coded default.
    prompt_text = tracer.get_prompt(
        prompt_name="demo-system-prompt",
        fallback="You are a helpful assistant specialised in cloud-native AI systems.",
    )
    print(f"System prompt: {prompt_text}")

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt_text},
                {"role": "user", "content": "What is LiteLLM used for?"},
            ],
            max_tokens=120,
        )
        print(f"Response: {response.choices[0].message.content}")
    except Exception as exc:
        print(f"[error] Prompt-managed chat failed: {exc}")


def example_cost_tracking() -> None:
    """Display spend summary and per-model metrics from LiteLLM."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4 — Cost tracking via LiteLLM spend API")
    print("=" * 60)

    base_url = os.getenv("APP_LITELLM_BASE_URL", "http://localhost:4000")
    master_key = _require_env("LITELLM_MASTER_KEY")
    if not master_key:
        return

    tracker = CostTracker(base_url=base_url, api_key=master_key)

    spend = tracker.get_spend_summary()
    if spend:
        print("Spend summary:")
        for key, value in spend.items():
            print(f"  {key}: {value}")
    else:
        print("No spend data returned (proxy may not be reachable).")

    metrics = tracker.get_model_metrics()
    if metrics:
        print("\nPer-model metrics:")
        for entry in metrics[:5]:   # show first 5 rows
            print(f"  {entry}")
    else:
        print("No model metrics returned.")


# ── entry-point ───────────────────────────────────────────────────────────────

def main() -> None:
    print("GenAIOps-OSS demo")
    print("LiteLLM + Langfuse integration showcase")

    example_basic_chat()
    example_with_tracing()
    example_prompt_management()
    example_cost_tracking()

    print("\nDemo complete.")


if __name__ == "__main__":
    main()
