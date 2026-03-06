# Architecture Overview

This document describes the architecture of the GenAIOps-OSS stack and how the services interact.

## System Diagram

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                            CLIENT APPLICATIONS                                │
│                                                                               │
│   Python/Node/curl  →  OpenAI SDK (base_url=http://localhost:4000/v1)        │
└────────────────────────────────┬──────────────────────────────────────────────┘
                                 │
                    HTTP (OpenAI-compatible REST API)
                                 │
                                 ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                         LITELLM PROXY  (:4000)                                │
│                                                                               │
│  ┌────────────────────────────────────────────────────────────────────────┐   │
│  │  Request lifecycle                                                      │   │
│  │  1. Validate bearer token (virtual key / master key)                   │   │
│  │  2. Check model access permissions                                     │   │
│  │  3. Check budget limits                                                 │   │
│  │  4. Check Redis cache → serve cached response if hit                   │   │
│  │  5. Select provider via routing strategy (least-busy)                  │   │
│  │  6. Forward to provider (OpenAI / Azure / Anthropic / Ollama / …)     │   │
│  │  7. Stream / return response                                            │   │
│  │  8. Log spend to PostgreSQL                                             │   │
│  │  9. Emit trace event to Langfuse (success_callback)                    │   │
│  └────────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│  Config: litellm/config.yaml                                                  │
└──────┬──────────────┬──────────────────────┬──────────────────────────────────┘
       │              │                      │
       │ SQL           │ Cache               │ Traces / spans
       ▼              ▼                      ▼
┌──────────┐    ┌──────────┐       ┌────────────────────────────────────────────┐
│ Postgres │    │  Redis   │       │          LANGFUSE SERVER  (:3000)          │
│ (litellm │    │ (:6379)  │       │                                            │
│  schema) │    └──────────┘       │  ┌──────────────────────────────────────┐  │
└──────────┘                       │  │  Web UI                              │  │
                                   │  │  • Trace explorer                    │  │
┌──────────┐                       │  │  • Evaluation dashboard              │  │
│ Postgres │◄──────────────────────│  │  • Prompt management                 │  │
│ (langfuse│  migrations + queries  │  │  • Dataset management               │  │
│  schema) │                       │  └──────────────────────────────────────┘  │
└──────────┘                       │                                            │
                                   │  ┌──────────────────────────────────────┐  │
┌────────────────┐                 │  │  REST / SDK API                      │  │
│  ClickHouse    │◄────────────────│  │  • /api/public/traces                │  │
│  (analytics)   │  event batches   │  │  • /api/public/scores                │  │
└────────────────┘                 │  │  • /api/public/prompts               │  │
                                   │  └──────────────────────────────────────┘  │
┌────────────────┐                 └────────────────┬───────────────────────────┘
│     MinIO      │◄────────────────────────────────── S3 blob storage
│  (:9000/:9001) │  (trace payload blobs)
└────────────────┘

┌────────────────────────────────────────────────────────────────────────────────┐
│                       LANGFUSE WORKER (background)                             │
│  Reads jobs from Redis queue; processes async evaluation runs, dataset        │
│  exports, and ClickHouse ingestion.                                            │
└────────────────────────────────────────────────────────────────────────────────┘
```

## Data Flows

### 1. Chat Completion Request

```
App → LiteLLM (validate key, check budget, route)
    → Redis (cache lookup)
    → LLM Provider (OpenAI/Azure/Anthropic/Ollama)
    ← Response returned to App
    → PostgreSQL (spend log written)
    → Langfuse (trace event emitted via callback)
```

### 2. Langfuse Trace Ingestion

```
LiteLLM callback → Langfuse API (POST /api/public/ingestion)
                 → Event written to MinIO (large payloads)
                 → Redis queue (async processing)
Langfuse Worker  → Reads queue → writes to ClickHouse (analytics)
                              → writes to PostgreSQL (metadata)
```

### 3. Prompt Management

```
Developer → Langfuse UI (create/edit prompt)
          → PostgreSQL (prompt version stored)
App       → Langfuse SDK (get_prompt)
          ← Compiled prompt text returned
          → LiteLLM (chat completion with compiled prompt)
```

## Networking

All services communicate on the internal `genaiops` Docker bridge network.
Only the following ports are published to the host:

| Port | Service          | Purpose                             |
|------|------------------|-------------------------------------|
| 4000 | LiteLLM          | LLM API gateway (OpenAI-compatible) |
| 3000 | Langfuse         | Web UI and public API               |
| 9000 | MinIO            | S3-compatible object storage        |
| 9001 | MinIO Console    | MinIO admin web UI                  |

## Storage Volumes

| Volume           | Used by               | Contents                         |
|------------------|-----------------------|----------------------------------|
| `postgres_data`  | postgres              | LiteLLM + Langfuse relational data|
| `clickhouse_data`| clickhouse            | Langfuse analytics / event data  |
| `redis_data`     | redis                 | Cache + job queues               |
| `minio_data`     | minio                 | Trace payload blobs              |
