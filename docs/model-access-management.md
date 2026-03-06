# Model Access Management

LiteLLM's virtual key system lets you enforce fine-grained model access control
across teams and applications without exposing provider credentials.

## How It Works

```
Provider credentials (OpenAI key, Azure key, …)
         │
         ▼  stored securely in LiteLLM config / environment
┌─────────────────────┐
│    LiteLLM Proxy    │
│                     │
│  Master key ──────── admin access to all models
│  Team A key ──────── access to [gpt-4o-mini, claude-3-haiku]
│  Team B key ──────── access to [gpt-4o, azure/gpt-4o]
│  CI/CD key ─────────  access to [gpt-3.5-turbo] only
└─────────────────────┘
```

Applications never see provider API keys — they only ever hold a LiteLLM
virtual key that you can revoke or re-scope at any time.

---

## Restricting Models per Virtual Key

```bash
# Key that can only call cheap models
curl -X POST http://localhost:4000/key/generate \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "key_alias": "frontend-app",
    "models": ["gpt-4o-mini", "claude-3-haiku"],
    "metadata": {"app": "customer-portal"}
  }'
```

If the key holder tries to call `gpt-4o`, LiteLLM returns `HTTP 403`.

---

## Restricting Models per Team

```bash
curl -X POST http://localhost:4000/team/new \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "team_alias": "data-science",
    "models": ["gpt-4o", "claude-3-5-sonnet"],
    "max_budget": 500,
    "budget_duration": "monthly"
  }'
```

All virtual keys in the team inherit this model restriction.

---

## Rate Limiting

Control request throughput at key or team level:

```bash
curl -X POST http://localhost:4000/key/generate \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "rpm_limit": 60,
    "tpm_limit": 100000,
    "max_parallel_requests": 5
  }'
```

| Parameter              | Description                              |
|------------------------|------------------------------------------|
| `rpm_limit`            | Requests per minute                      |
| `tpm_limit`            | Tokens per minute                        |
| `max_parallel_requests`| Maximum concurrent in-flight requests    |

---

## Updating Key Permissions

```bash
# Expand a key to include a new model
curl -X POST http://localhost:4000/key/update \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "sk-my-virtual-key",
    "models": ["gpt-4o-mini", "claude-3-haiku", "gpt-4o"]
  }'
```

---

## Revoking a Key

```bash
curl -X POST http://localhost:4000/key/delete \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"keys": ["sk-my-virtual-key"]}'
```

---

## Listing All Keys

```bash
curl http://localhost:4000/key/list \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY"
```

---

## Allow-Lists and Block-Lists

You can configure model-level allow/block lists in `litellm/config.yaml`:

```yaml
general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
  # Prevent any key from calling these models unless explicitly granted
  blocked_models:
    - gpt-4o   # require explicit grant per key
```

---

## Best Practices

1. **Never share the master key** with application code. Create virtual keys with the minimum required permissions.
2. **Set budgets on every team key** to prevent surprise bills.
3. **Use `key_alias` and `metadata`** to record which service/project owns each key — makes auditing easy.
4. **Rotate keys** by creating a new key, updating the application secret, then revoking the old key.
5. **Use `max_parallel_requests`** to prevent a single misbehaving service from consuming all capacity.
