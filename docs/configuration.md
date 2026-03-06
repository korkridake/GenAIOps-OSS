# LiteLLM Configuration Reference

This document is the full reference for `litellm/config.yaml`.

## Top-Level Keys

| Key                | Purpose                                        |
|--------------------|------------------------------------------------|
| `model_list`       | Declare models the proxy exposes               |
| `router_settings`  | Control how requests are routed across models  |
| `litellm_settings` | SDK-level settings (callbacks, caching, etc.)  |
| `general_settings` | Proxy server settings (auth, database, etc.)   |

---

## `model_list`

A list of model definitions.  Each entry exposes a `model_name` (what callers use) and maps it to one or more `litellm_params` (what LiteLLM forwards to the provider).

### Common litellm_params

| Parameter     | Description                                              |
|---------------|----------------------------------------------------------|
| `model`       | `provider/model-id` string, e.g. `openai/gpt-4o`        |
| `api_key`     | API key; use `os.environ/KEY_NAME` to read from env      |
| `api_base`    | Override base URL (required for Azure, Ollama)           |
| `api_version` | API version (Azure only)                                 |
| `rpm`         | Per-model requests-per-minute limit                      |
| `tpm`         | Per-model tokens-per-minute limit                        |

### OpenAI Example

```yaml
- model_name: gpt-4o
  litellm_params:
    model: openai/gpt-4o
    api_key: os.environ/OPENAI_API_KEY
```

### Azure OpenAI Example

```yaml
- model_name: azure/gpt-4o
  litellm_params:
    model: azure/gpt-4o
    api_key: os.environ/AZURE_API_KEY
    api_base: os.environ/AZURE_API_BASE
    api_version: os.environ/AZURE_API_VERSION
```

### Anthropic Example

```yaml
- model_name: claude-3-5-sonnet
  litellm_params:
    model: anthropic/claude-3-5-sonnet-20241022
    api_key: os.environ/ANTHROPIC_API_KEY
```

### Ollama (local) Example

```yaml
- model_name: ollama/llama3.2
  litellm_params:
    model: ollama/llama3.2
    api_base: http://host.docker.internal:11434
```

### Load Balancing Across Multiple Deployments

You can list the same `model_name` multiple times to load-balance across providers:

```yaml
- model_name: gpt-4o
  litellm_params:
    model: openai/gpt-4o
    api_key: os.environ/OPENAI_API_KEY

- model_name: gpt-4o
  litellm_params:
    model: azure/gpt-4o
    api_key: os.environ/AZURE_API_KEY
    api_base: os.environ/AZURE_API_BASE
    api_version: "2024-02-01"
```

---

## `router_settings`

```yaml
router_settings:
  enable_pre_call_checks: true     # validate params before forwarding
  routing_strategy: least-busy     # options: simple-shuffle, least-busy, latency-based-routing, usage-based-routing
  num_retries: 3                   # retry failed calls
  retry_after: 5                   # seconds to wait between retries
  allowed_fails: 3                 # mark deployment unhealthy after N failures
  cooldown_time: 60                # seconds to cool down a failing deployment
```

### Routing Strategies

| Strategy                  | Description                                          |
|---------------------------|------------------------------------------------------|
| `simple-shuffle`          | Random selection (default)                           |
| `least-busy`              | Route to deployment with fewest in-flight requests   |
| `latency-based-routing`   | Route to deployment with lowest average latency      |
| `usage-based-routing`     | Balance by token usage                               |

---

## `litellm_settings`

```yaml
litellm_settings:
  success_callback: ["langfuse"]   # called after every successful request
  failure_callback: ["langfuse"]   # called after every failed request

  # Langfuse integration
  langfuse_public_key: os.environ/LANGFUSE_PUBLIC_KEY
  langfuse_secret_key: os.environ/LANGFUSE_SECRET_KEY
  langfuse_host: os.environ/LANGFUSE_HOST

  drop_params: true      # silently drop unsupported parameters
  set_verbose: false     # enable debug logging

  # Redis caching
  cache: true
  cache_params:
    type: redis
    host: redis
    port: 6379
    ttl: 600           # cache TTL in seconds
```

### Supported Callbacks

| Callback    | Purpose                              |
|-------------|--------------------------------------|
| `langfuse`  | Observability & tracing              |
| `prometheus`| Expose metrics at `/metrics`         |
| `datadog`   | Send metrics/logs to Datadog         |
| `slack`     | Send alerts to Slack                 |
| `s3`        | Write logs to S3                     |

---

## `general_settings`

```yaml
general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY   # admin key for /key, /team, /spend endpoints
  database_url: os.environ/DATABASE_URL        # PostgreSQL for spend logs & virtual keys
  store_model_in_db: true                      # persist model list to DB
  disable_spend_logs: false                    # set true to skip spend logging
  max_parallel_requests: 100                   # global concurrency limit
  request_timeout: 600                         # seconds before proxy times out
```

---

## Adding a New Model

1. Add an entry to `model_list` in `litellm/config.yaml`.
2. Add the required environment variables to `.env`.
3. Rebuild the LiteLLM container:

```bash
docker compose build litellm
docker compose up -d litellm
```

Alternatively, add models at runtime via the API without restarting:

```bash
curl -X POST http://localhost:4000/model/new \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "my-new-model",
    "litellm_params": {
      "model": "openai/gpt-4o",
      "api_key": "sk-..."
    }
  }'
```
