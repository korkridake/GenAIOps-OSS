# Cost Allocation with LiteLLM

LiteLLM tracks spend at every level — global, team, virtual key, and user — and
enforces budget limits automatically.

## Concepts

| Concept        | Description                                                           |
|----------------|-----------------------------------------------------------------------|
| **Master key** | Super-admin key; can call all models, manage keys/teams, view spend   |
| **Virtual key**| Scoped key assigned to a team/user; has optional budget & model limits|
| **Team**       | Group of virtual keys sharing a budget                                |
| **User**       | Individual tracked within a team                                      |

---

## Creating Teams

```bash
curl -X POST http://localhost:4000/team/new \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "team_alias": "engineering",
    "max_budget": 200,
    "budget_duration": "monthly",
    "models": ["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet"]
  }'
```

Response includes `team_id` — save it for use when creating virtual keys.

---

## Creating Virtual Keys

### Basic key with no budget limit

```bash
curl -X POST http://localhost:4000/key/generate \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"team_id": "team_abc123"}'
```

### Key with monthly budget and model restriction

```bash
curl -X POST http://localhost:4000/key/generate \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "team_id": "team_abc123",
    "key_alias": "backend-service",
    "max_budget": 50,
    "budget_duration": "monthly",
    "models": ["gpt-4o-mini"],
    "tpm_limit": 500000,
    "rpm_limit": 500,
    "metadata": {
      "project": "search-api",
      "environment": "production"
    }
  }'
```

### Key with per-request spend limit

```bash
curl -X POST http://localhost:4000/key/generate \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "max_budget": 5,
    "budget_duration": "daily",
    "max_parallel_requests": 10
  }'
```

---

## Viewing Spend

### Global spend summary

```bash
curl http://localhost:4000/spend/logs \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY"
```

### Per-key spend

```bash
curl "http://localhost:4000/key/info?key=sk-..." \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY"
```

### Per-team spend

```bash
curl "http://localhost:4000/team/info?team_id=team_abc123" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY"
```

### Per-model metrics

```bash
curl http://localhost:4000/model/metrics \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY"
```

### Spend by date range

```bash
curl "http://localhost:4000/spend/logs?start_date=2024-01-01&end_date=2024-01-31" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY"
```

---

## Budget Enforcement

When a virtual key or team exceeds its budget:

- LiteLLM returns HTTP `429 Too Many Requests` with the message `Budget exceeded`.
- The spend counter resets automatically at the start of each `budget_duration` period.
- You can reset it manually:

```bash
curl -X POST http://localhost:4000/key/update \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"key": "sk-...", "spend": 0}'
```

---

## Budget Duration Options

| Value       | Resets every          |
|-------------|-----------------------|
| `daily`     | 24 hours              |
| `weekly`    | 7 days                |
| `monthly`   | Calendar month        |
| `yearly`    | Calendar year         |

---

## Using the Python CostTracker Utility

```python
from app.utils.cost_tracker import CostTracker

tracker = CostTracker(
    base_url="http://localhost:4000",
    api_key="sk-litellm-master-key",
)

# Global spend
print(tracker.get_spend_summary())

# Per-model
for model in tracker.get_model_metrics():
    print(model)

# Specific key
print(tracker.get_key_spend("sk-my-virtual-key"))

# Team
print(tracker.get_team_spend("team_abc123"))
```

---

## Integrating with Observability

Every spend event is automatically sent to Langfuse as part of the request trace.
You can filter traces in Langfuse by `metadata.spend` or build dashboards showing
cost per user session.
