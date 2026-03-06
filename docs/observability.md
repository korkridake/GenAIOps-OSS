# Observability with LiteLLM and Langfuse

Every request that flows through the LiteLLM proxy is automatically traced in
Langfuse.  This document explains how the integration works and how to use the
observability features.

## How Tracing Works

```
App → LiteLLM proxy
         │
         ├── (success) → success_callback: ["langfuse"]
         │                   │
         └── (failure) → failure_callback: ["langfuse"]
                              │
                              ▼
                    POST /api/public/ingestion
                              │
                              ▼
                    Langfuse (stores trace)
```

LiteLLM populates each Langfuse trace with:

| Field          | Value                                    |
|----------------|------------------------------------------|
| `name`         | `litellm-completion`                     |
| `input`        | Messages array sent to the provider      |
| `output`       | Completion returned by the provider      |
| `model`        | Model name used                          |
| `usage`        | Token counts (prompt + completion)       |
| `cost`         | Estimated cost in USD                    |
| `latency`      | End-to-end latency in milliseconds       |
| `metadata`     | Virtual key alias, team ID, user ID, etc.|

---

## Viewing Traces

Open <http://localhost:3000> and navigate to **Traces**.

Each trace shows:
- The full prompt and completion
- Token usage and estimated cost
- Latency waterfall
- Any evaluation scores attached

---

## Adding Custom Traces from Your Application

Use the `TracingClient` utility to create richer traces that include
application-level context (user sessions, multi-step workflows, etc.).

```python
from app.utils.tracing import TracingClient

tracer = TracingClient()   # reads from env vars

with tracer.trace(name="customer-query", user_id="user-42", session_id="sess-1") as trace:
    span = tracer.span(trace, name="retrieval", input_data={"query": "..."})
    docs = retrieval_function(query)
    tracer.end_span(span, output_data={"doc_count": len(docs)})

    span2 = tracer.span(trace, name="llm-call", input_data={"docs": docs})
    response = llm_call(docs)
    tracer.end_span(span2, output_data={"answer": response})

tracer.flush()
```

---

## Correlating LiteLLM Calls with Application Traces

Pass the Langfuse trace ID as a custom header so LiteLLM's auto-trace nests
inside your application trace:

```python
client = create_llm_client()

with tracer.trace(name="my-workflow") as trace:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[...],
        extra_headers={"X-Langfuse-Trace-Id": trace.id},
    )
```

---

## Metrics Dashboard

Langfuse aggregates:

- **Requests over time** — volume by model, key, or user
- **Latency percentiles** — p50 / p95 / p99 per model
- **Token usage** — input vs. output tokens
- **Cost** — cumulative and per-request cost

Navigate to **Dashboard** in the Langfuse UI.

---

## Sessions

Group related traces into a session (e.g. a multi-turn conversation):

```python
with tracer.trace(name="turn-1", session_id="conv-abc") as t1:
    ...

with tracer.trace(name="turn-2", session_id="conv-abc") as t2:
    ...
```

Both traces appear under the same session in the Langfuse UI.

---

## Filtering and Searching Traces

In the Langfuse UI you can filter by:

- `model` — which LLM was used
- `user_id` — traces for a specific end-user
- `session_id` — all turns in a conversation
- `metadata.*` — any key/value in the trace metadata
- Date range, latency range, cost range

---

## Exporting Traces

Traces can be exported as datasets for fine-tuning or offline evaluation:

1. Filter the traces you want in the UI
2. Click **Add to Dataset**
3. Download the dataset as JSON or use the SDK

---

## Prometheus Metrics (Optional)

To expose a `/metrics` endpoint for Prometheus scraping, add to `litellm/config.yaml`:

```yaml
litellm_settings:
  success_callback: ["langfuse", "prometheus"]
  failure_callback: ["langfuse", "prometheus"]
```

Then scrape `http://localhost:4000/metrics`.
