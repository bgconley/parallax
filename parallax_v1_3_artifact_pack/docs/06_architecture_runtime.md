# 06 — Architecture and Runtime Specification

## Architecture summary

Parallax uses a service-oriented backend with a simple Compose-first runtime. The source-of-truth database is PostgreSQL. The API service handles validation, authentication, idempotency, lightweight reads/writes, and workflow dispatch. Durable background work is handled by Temporal workflows. AI/model services are internal and never exposed publicly.

## Services

### `parallax-api`

FastAPI/Pydantic service.

Responsibilities:

- authenticate requests;
- enforce user scoping;
- validate request/response models;
- enforce mutation envelope/idempotency;
- enforce explicit read-only resolver behavior for activity/place resolution;
- enforce context capture policy before accepting optional sensor context;
- perform lightweight transactional writes;
- dispatch workflows;
- expose OpenAPI contract;
- return source and projection data.

Non-responsibilities:

- long-running LLM calls;
- expensive embedding backfills;
- stats recomputation beyond small synchronous reads;
- public exposure of model endpoints.

### `parallax-worker`

Temporal worker service.

Responsibilities:

- process context annotations;
- finalize timing runs;
- recompute activity profiles;
- answer temporal queries;
- export/delete data;
- refresh retrieval documents;
- run eval batches.

### `parallax-ai-orchestrator`

Product-aware model boundary.

Responsibilities:

- select model role and prompt version;
- apply privacy filters;
- validate structured output;
- perform repair loops;
- log model invocation metadata;
- enforce local/cloud fallback policy.

### `parallax-estimator`

Can be a worker module initially. Computes robust statistics, confidence labels, personal ranges, and prediction snapshots.

### `parallax-query-worker`

Can be a worker module initially. Handles query intent classification, deterministic facts, evidence retrieval, optional reranking, answer narration, and answer validation.

### `postgres`

System-of-record database. Baseline is PostgreSQL with `pgcrypto`, `citext`, and later `pgvector` for retrieval. ParadeDB, PostGIS, and TimescaleDB SQL lives under `database/optional_profiles/` and is opt-in.

### `redis`

Cache, lightweight queue coordination, and rate limiting. It is not source truth.

### `temporal-server`

Temporal workflow engine. It coordinates durable background work. The timer itself must not depend on Temporal being available.

### `minio`

S3-compatible object storage for optional audio, exports, attachments, model artifacts, and eval artifacts.

### `caddy`

Ingress/reverse proxy. Exposes API only. Does not expose model endpoints.

### Optional model-serving services

- `vllm-context`: context extraction and narration model.
- `vllm-narrator`: larger answer narration/checkpoint suggestion model if separate.
- `tei-embeddings`: embedding model service.

## Request lifecycle

### Mutating request

1. Client sends request with auth and mutation envelope.
2. API validates schema and user scope.
3. API checks `client_mutation_log`.
4. If duplicate, previous result is returned.
5. If new, API writes source data in a transaction.
6. API records mutation result hash.
7. API emits outbox event or starts workflow when needed.
8. API returns accepted result.

`POST /v1/activities/resolve` and `POST /v1/places/resolve` are read-only POST
exceptions. They follow the read lifecycle and must not dispatch workflows or
write domain rows.

### Context extraction lifecycle

1. Annotation is saved immediately.
2. API returns without waiting for model.
3. Workflow loads annotation.
4. Privacy filters run.
5. AI orchestrator calls selected model.
6. Output validates against schema.
7. Candidate events are persisted.
8. Confidence policy decides auto-log, confirmation, or review.
9. Activity profile recompute may be queued after confirmation/review.

### Query answer lifecycle

1. User asks a question.
2. Query worker classifies intent and resolves activity aliases.
3. Deterministic facts are computed from reviewed source data.
4. Evidence bundle is assembled.
5. Optional retrieval/reranking selects supporting items.
6. LLM narrates only the facts/evidence payload.
7. Answer schema validates.
8. Answer and evidence are persisted.
9. User can open evidence and correct source data.

## Data consistency model

The event log is append-safe. Derived projections are eventually consistent. User-facing screens should expose pending/recomputing states instead of blocking source actions.

## Deployment stages

### Local prototype

Docker Compose with single Postgres, Redis, Temporal, MinIO, API, worker, and optional model services.

### Private alpha

Compose or small k3s deployment with encrypted backups, observability, auth, and model endpoints on private networks only.

### Hardened self-hosted deployment

k3s with persistent volumes, backup automation, secrets management, model scheduling, and service monitoring.

## Runtime constraints

- API p95 for simple reads/writes: target under 300 ms locally, under 750 ms over private network.
- Timing event append must be low-latency and independent of LLM/model availability.
- Context extraction can be asynchronous and slower.
- Query narration can be asynchronous or return pending for complex questions.
- All services must be restart-safe.


## v1.3 context ingestion architecture

Add a context ingestion path alongside the timing event path.

Recommended components:

- Mobile/local capture layer: creates timing events, annotations, and context snapshots.
- API mutation layer: validates idempotent capture payloads.
- Context normalizer: normalizes location/radio/device observations and applies privacy policy.
- Place inference worker: clusters permitted observations into user-scoped place candidates.
- Feature vector worker: creates privacy-filtered `temporal_feature_vector` rows.
- Timeline review worker: flags possible forgotten timers or material context changes.
- Analytics worker: computes contextual activity stats after review.

The context ingestion path must be non-blocking. A timing event may be accepted before its context snapshot is processed.
