# Phase 7 Grounded Ask About Time

This note records the Phase 7 implementation boundary for grounded temporal
queries. The canonical source remains
`parallax_v1_3_artifact_pack/docs/03_phased_implementation_plan.md`.

## Scope

Phase 7 implements grounded Ask About Time only:

- deterministic query intent classification;
- activity resolution from explicit `activity_id` or activity names in questions;
- reviewed-run SQL aggregation for duration and delay questions;
- evidence bundle and evidence item persistence;
- baseline retrieval document creation through native PostgreSQL FTS;
- constrained deterministic answer text from computed facts;
- query grounding smoke/eval coverage.

Optional pgvector embeddings, ParadeDB, richer model narration, and model-serving
hardening remain later-phase work.

## Architecture

Routes remain thin in `services/api/parallax_api/routes/temporal.py`. The
application service resolves activity scope and applies mutation replay in
`services/api/parallax_api/services/temporal_service.py`.

Pure query planning helpers live in
`services/api/parallax_api/domain/temporal_query.py`. Postgres persistence and
SQL aggregation live in
`services/api/parallax_api/repositories/postgres_temporal_query.py`, which is
delegated to by `PostgresTemporalRepository` so prediction and feature-vector
logic do not absorb query-specific responsibilities.

## Verification

Phase 7 is proven by `make phase7-smoke`, which:

- creates reviewed timing runs with resource friction;
- asks duration and delay questions;
- checks computed facts, confidence, sample size, window, limitations, and
  evidence cards;
- checks query-grounding eval fixture requirements;
- verifies backing `evidence_bundle`, `evidence_item`, `retrieval_document`, and
  `outbox_event` rows.
