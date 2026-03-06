# GenAIOps-OSS

A production-ready, open-source **LLMOps stack template** that combines:

- **[LiteLLM](https://docs.litellm.ai/)** — unified LLM API gateway, virtual keys, cost allocation, model access management
- **[Langfuse](https://langfuse.com/)** — LLM observability, evaluation, prompt management, and dataset creation

Deploy once, connect any LLM provider, control costs and access, and get full observability — all from a single `docker compose up`.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Your Application                            │
│          (uses standard OpenAI SDK pointed at LiteLLM)             │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ OpenAI-compatible API  (port 4000)
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      LiteLLM Proxy                                   │
│  • Unified API for OpenAI / Azure / Anthropic / Ollama / …          │
│  • Virtual keys & team budgets                                       │
│  • Model access control & rate limiting                              │
│  • Cost tracking & spend logs                                        │
│  • Redis caching                                                     │
└─────┬──────────────────────────┬───────────────────────────────┬─────┘
      │ forwards requests        │ spend / metrics               │ traces
      ▼                          ▼                               ▼
  LLM Providers            PostgreSQL (litellm db)        Langfuse Server
  (OpenAI, Azure,                                              (port 3000)
   Anthropic, Ollama)                                     ┌────────────────┐
                                                          │  Langfuse UI   │
                                                          │  • Traces      │
                                                          │  • Evaluations │
                                                          │  • Prompts     │
                                                          │  • Datasets    │
                                                          └───────┬────────┘
                                                                  │
                                      ┌───────────────────────────┼───────────────┐
                                      ▼                           ▼               ▼
                               PostgreSQL                    ClickHouse         MinIO
                              (langfuse db)                (analytics store) (blob store)
```

### Services at a glance

| Service          | Image                                  | Default Port | Purpose                       |
|------------------|----------------------------------------|:------------:|-------------------------------|
| litellm          | `ghcr.io/berriai/litellm:main-latest`  | 4000         | LLM API gateway               |
| langfuse-server  | `langfuse/langfuse:3`                  | 3000         | Observability UI & API        |
| langfuse-worker  | `langfuse/langfuse-worker:3`           | —            | Background job processor      |
| postgres         | `postgres:16-alpine`                   | 5432 (internal) | Relational store           |
| clickhouse       | `clickhouse/clickhouse-server:24.12`   | 8123 (internal) | Analytics / event store    |
| redis            | `redis:7-alpine`                       | 6379 (internal) | Cache & queue               |
| minio            | `minio/minio:latest`                   | 9000 / 9001  | S3-compatible blob storage    |

---

## Quick Start

### Prerequisites

- Docker ≥ 24 and Docker Compose v2
- An API key for at least one LLM provider (OpenAI, Azure, Anthropic, or a local Ollama install)

### 1 — Clone and configure

```bash
git clone https://github.com/your-org/GenAIOps-OSS.git
cd GenAIOps-OSS
cp .env.example .env
```

Edit `.env` and fill in your real values:

```bash
# Required — change ALL placeholder values
LITELLM_MASTER_KEY=sk-litellm-your-secret-key
LITELLM_SALT_KEY=a-random-32-character-string-here
LANGFUSE_NEXTAUTH_SECRET=another-32-char-random-string
LANGFUSE_SALT=yet-another-random-salt

# At least one LLM provider key
OPENAI_API_KEY=sk-...
```

> **Security**: never commit `.env` to version control. The `.gitignore` already excludes it.

### 2 — Start the stack

```bash
docker compose up -d
```

First run downloads all images (~3 GB) and runs database migrations — allow ~2 minutes.

Check that everything is healthy:

```bash
docker compose ps
```

### 3 — Access the services

| Service       | URL                        | Default credentials           |
|---------------|----------------------------|-------------------------------|
| LiteLLM API   | <http://localhost:4000>    | Bearer `LITELLM_MASTER_KEY`   |
| LiteLLM UI    | <http://localhost:4000/ui> | `admin` / `LITELLM_MASTER_KEY`|
| Langfuse UI   | <http://localhost:3000>    | Create account on first visit |
| MinIO Console | <http://localhost:9001>    | `MINIO_ROOT_USER` / password  |

### 4 — Run the demo app

```bash
cd app
pip install -r requirements.txt
python main.py
```

---

## Creating Virtual Keys for Cost Allocation

Virtual keys let you assign budgets and track spend per team, project, or user.

```bash
# Create a virtual key for a team with a monthly $50 budget
curl -X POST http://localhost:4000/key/generate \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "team_id": "team-engineering",
    "max_budget": 50,
    "budget_duration": "monthly",
    "models": ["gpt-4o-mini", "gpt-3.5-turbo"],
    "metadata": {"project": "customer-chat"}
  }'
```

See [docs/cost-allocation.md](docs/cost-allocation.md) for full details.

---

## Model Access Management

Control which models each virtual key or team can access:

```bash
# Create a read-only research key restricted to cheap models
curl -X POST http://localhost:4000/key/generate \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "models": ["gpt-4o-mini", "claude-3-haiku"],
    "tpm_limit": 100000,
    "rpm_limit": 100
  }'
```

See [docs/model-access-management.md](docs/model-access-management.md) for full details.

---

## Observability

Every request through LiteLLM is automatically traced in Langfuse.  Open
<http://localhost:3000> to see:

- **Traces** — full request/response detail per call
- **Metrics** — latency, token usage, cost over time
- **Evaluations** — attach human or LLM-generated quality scores
- **Sessions** — group traces into user sessions

See [docs/observability.md](docs/observability.md) for full details.

---

## Project Structure

```
GenAIOps-OSS/
├── docker-compose.yml          # Orchestrates all services
├── .env.example                # Environment variables template
├── litellm/
│   ├── Dockerfile              # Extends LiteLLM image with config
│   └── config.yaml             # LiteLLM proxy configuration
├── app/
│   ├── main.py                 # Demo script (run with python main.py)
│   ├── requirements.txt
│   ├── utils/
│   │   ├── llm_client.py       # OpenAI client factory for LiteLLM proxy
│   │   ├── tracing.py          # Langfuse tracing helpers
│   │   └── cost_tracker.py     # LiteLLM spend API client
│   └── examples/
│       ├── chat_completion.py  # Multi-model chat example
│       ├── evaluation.py       # LLM-as-a-judge evaluation
│       └── prompt_management.py# Langfuse prompt CRUD
├── tests/
│   ├── conftest.py             # pytest fixtures
│   ├── test_utils.py           # Unit tests (no external services)
│   └── requirements.txt
├── scripts/
│   └── init-postgres.sh        # Creates litellm + langfuse databases
└── docs/
    ├── architecture.md
    ├── configuration.md
    ├── cost-allocation.md
    ├── model-access-management.md
    ├── observability.md
    ├── evaluation.md
    └── prompt-management.md
```

---

## Configuration Reference

See [docs/configuration.md](docs/configuration.md) for a full reference of `litellm/config.yaml`.

---

## Running Tests

```bash
pip install -r tests/requirements.txt -r app/requirements.txt
pytest tests/ -v
```

Tests are fully offline — all external services are mocked.

---

## Contributing

1. Fork the repository and create a feature branch.
2. Make your changes and add tests where appropriate.
3. Run `pytest tests/ -v` to verify all tests pass.
4. Open a pull request with a clear description of the change.

Please keep commits focused: one logical change per commit.

---

## License

[MIT](LICENSE)