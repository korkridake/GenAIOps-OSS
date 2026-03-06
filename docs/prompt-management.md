# Prompt Management with Langfuse

Langfuse provides version-controlled, collaborative prompt management.
Prompts are stored centrally and fetched at runtime, so you can update
them without redeploying your application.

## Core Concepts

| Concept     | Description                                                           |
|-------------|-----------------------------------------------------------------------|
| **Prompt**  | A named, versioned text template (supports Mustache `{{variable}}`)   |
| **Version** | Immutable snapshot of a prompt; new edits create a new version        |
| **Label**   | Tag applied to a version (`production`, `staging`, `latest`)          |
| **Config**  | Optional JSON metadata (model, temperature, max_tokens) per version   |

---

## Creating a Prompt via SDK

```python
from langfuse import Langfuse

lf = Langfuse()

lf.create_prompt(
    name="customer-support",
    prompt=(
        "You are a helpful support agent for {{company}}. "
        "Respond in a {{tone}} tone. "
        "Always reference the customer's issue number {{ticket_id}}."
    ),
    labels=["production"],
    config={
        "model": "gpt-4o-mini",
        "temperature": 0.3,
        "max_tokens": 500,
    },
)
```

---

## Creating a Prompt via the UI

1. Open <http://localhost:3000>
2. Navigate to **Prompts → New Prompt**
3. Enter name, template text, and optional config
4. Click **Save** to create version 1
5. Promote to production by adding the `production` label

---

## Fetching and Compiling a Prompt

```python
from langfuse import Langfuse

lf = Langfuse()

# Always fetches the version labelled 'production'
prompt = lf.get_prompt("customer-support")

# Compile with variable substitution
system_message = prompt.compile(
    company="Acme Corp",
    tone="friendly",
    ticket_id="#12345",
)

print(system_message)
# → "You are a helpful support agent for Acme Corp. Respond in a friendly
#    tone. Always reference the customer's issue number #12345."
```

### Fetch a specific version

```python
prompt = lf.get_prompt("customer-support", version=3)
```

### Fetch by label

```python
prompt = lf.get_prompt("customer-support", label="staging")
```

---

## Using Managed Prompts in Chat Completions

```python
from langfuse import Langfuse
from app.utils.llm_client import create_llm_client

lf = Langfuse()
client = create_llm_client()

prompt_obj = lf.get_prompt("customer-support")
system_msg = prompt_obj.compile(company="Acme", tone="professional", ticket_id="#99")

# Link the prompt version to the Langfuse trace automatically
with prompt_obj.observe() as trace:
    response = client.chat.completions.create(
        model=prompt_obj.config.get("model", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": "My order hasn't arrived."},
        ],
    )
    trace.update(output=response.choices[0].message.content)

lf.flush()
```

Langfuse links the prompt version to the trace so you can track which
prompt version produced which outputs.

---

## Graceful Fallback

Always provide a fallback in case Langfuse is unreachable:

```python
from app.utils.tracing import TracingClient

tracer = TracingClient()
system_msg = tracer.get_prompt(
    "customer-support",
    fallback="You are a helpful assistant.",
)
```

---

## Versioning Strategy

| Scenario               | Recommended approach                                   |
|------------------------|--------------------------------------------------------|
| Minor wording tweak    | Edit prompt → new version → promote `production` label |
| A/B test               | Two prompts with different names; split traffic in code |
| Rollback               | Re-apply `production` label to a previous version      |
| Promote staging→prod   | Move `production` label from old version to new        |

---

## Prompt Metrics

Langfuse links every trace to the prompt version that generated it.
In **Prompts → [name] → Metrics** you can see:

- Volume of requests per version
- Average latency per version
- Average cost per version
- Score distributions per version

This makes it straightforward to compare quality and cost before promoting
a new prompt version to production.
