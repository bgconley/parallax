# Parallax Canonical Artifact Pack v1.3

Generated: 2026-04-26

Parallax is a temporal-first personal intelligence application. Its product promise is:

**Time what you do. Say what happened. Learn what really takes the time.**

This pack replaces the earlier naming and alignment drafts. **Parallax** is the canonical product/app name. The earlier product placeholders and retired names must not appear in new product-facing code, schemas, endpoints, UI copy, package names, repository paths, Docker image names, environment variable prefixes, or Figma frame names.

## What this bundle is

This is the source-of-truth handoff bundle for an agentic coder implementing Parallax end to end. It aligns the product thesis, design language, database schema, API contracts, event/job contracts, JSON schemas, infrastructure posture, testing strategy, phased implementation plan, timing analytics model, real-world capture workflows, and geospatial/radio context posture into one coherent v1.3 package.

The bundle intentionally treats the backend/domain model as canonical and treats UI state as a projection of domain state. The UI may use humane labels such as "run", "say what happened", "detour", and "useful run"; implementation contracts use the canonical names and enums in `contracts/`, `database/`, and `docs/02_temporal_domain_model.md`.

## Required reading order

1. `AGENT_START_HERE.md`
2. `docs/01_app_system_spec.md`
3. `docs/02_temporal_domain_model.md`
4. `docs/03_phased_implementation_plan.md`
5. `database/README.md`
6. `contracts/openapi/parallax_api_v1_3.yaml`
7. `contracts/events/parallax_event_contracts_v1_3.yaml`
8. `contracts/jobs/parallax_workflows_v1_3.yaml`
9. `docs/05_design_language_figma_handoff.md`
10. `docs/18_timing_analytics_and_context_intelligence.md`
11. `docs/19_capture_workflows_and_sensor_fusion.md`
12. `docs/20_mobile_location_radio_privacy_reference.md`
13. `docs/21_current_platform_and_extension_references.md`
14. `docs/22_v1_3_gap_closure_summary.md`
15. `docs/23_agentic_implementation_guardrails.md`
16. `docs/12_testing_qa_release_rollback.md`

## Canonical technical choices

The v1.3 baseline is:

- Python/FastAPI/Pydantic API service.
- Temporal workflow engine for durable asynchronous workflows.
- PostgreSQL as the system of record.
- Native PostgreSQL full-text search for baseline lexical search.
- pgvector for embedding-backed retrieval when the retrieval phase begins.
- ParadeDB/`pg_search` as an optional richer search profile behind a feature flag.
- TimescaleDB as an optional analytics profile behind a feature flag, not the source of truth for timing correctness.
- Optional PostGIS profile for place/radius queries once the baseline context model is validated.
- Geospatial, radio, motion, and device context as user-controlled auxiliary evidence, not passive surveillance.
- MinIO or S3-compatible object storage for optional audio, exports, attachments, model artifacts, and evaluation artifacts.
- Docker Compose first; k3s only after operational pressure justifies it.
- Figma/iOS design execution guided by the design language and mockup references in this pack.

## Non-negotiable implementation rules

- Use `user_id` as the canonical identity field in backend/database contracts. Do not use `account_id` in domain schemas.
- Do not collapse active time, wall time, friction time, start latency, transition latency, recovery time, or context-derived uncertainty into a single unqualified duration.
- Store timer source actions as idempotent, append-safe events.
- Derive spans, summaries, predictions, and query answers from source events plus user review/corrections.
- Save raw context annotations immediately, even offline.
- Treat raw notes, transcripts, audio, embeddings, and timing patterns as privacy-sensitive.
- LLMs may interpret, narrate, and propose. They must not own numeric truth or silently update duration baselines.
- Every mutating API call must carry a mutation envelope.
- Resolver POST endpoints are explicitly read-only exceptions; creation/confirmation
  flows use documented mutation-envelope endpoints.
- Query answers must include evidence, sample size, time window, confidence, and limitations.
- User correction is part of the product model, not an edge case.

## Bundle structure

```text
parallax_v1_3_artifact_pack/
  README.md
  AGENT_START_HERE.md
  MANIFEST.txt
  docs/
  database/
  contracts/
  infrastructure/
  scripts/
  examples/
  tests_or_eval/
  source_inputs/
```

## Validation

This pack includes `scripts/validate_pack.py`. The generated validation report is in `VALIDATION_REPORT.md`.

The validation pass checks manifest accuracy, non-empty core files, parseability of JSON/YAML/Python files, required SQL file presence/order, required contract files, retired-name leakage, and ZIP completeness when a ZIP path is available. After extracting the pack into an implementation repository, use `scripts/validate_pack.py --skip-zip-check`; when validating a rebuilt archive, use `--zip-path`. SQL is syntax-reviewed structurally but was not executed against a live PostgreSQL instance in this generation environment.

## v1.3 additions

This pack adds timing analytics and ambient-context readiness that were not deep enough in v1.2:

- capture context snapshots;
- place/geospatial/radio/device observation tables;
- user-scoped place inference and correction;
- context-aware feature vectors;
- real-world capture scenario workflows;
- location/radio/motion privacy policy;
- optional PostGIS and Timescale context profiles;
- explicit context capture policy and timing review flag contracts;
- separated optional profile SQL under `database/optional_profiles/`;
- additional user stories and acceptance criteria for context-aware capture and estimates.
