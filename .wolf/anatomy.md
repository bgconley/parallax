# anatomy.md

> Auto-maintained by OpenWolf. Last scanned: 2026-05-04T01:27:30Z
> Files: manual Phase 9 update | Anatomy hits: 0 | Misses: 0

## ./

- `.dockerignore` — Docker build exclusions for local metadata, caches, and artifact zip (~30 tok)
- `.env.example` — Phase 0 runtime environment, ZFS bind paths, and Parallax-specific host ports (~180 tok)
- `AGENTS.md` — Repository Guidelines (~833 tok)
- `CLAUDE.md` — OpenWolf (~57 tok)
- `Makefile` — validation, lint/test, migration, phase smoke, security, release, and Compose lifecycle targets (~170 tok)
- `docker-compose.yml` — root Compose include for Phase 0 runtime (~20 tok)
- `pyproject.toml` — Python 3.12 dependency and lint/test configuration (~160 tok)

## .github/workflows/

- `ci.yml` — Phase 0 CI: uv sync, ruff, pytest, contract validation, Compose render (~110 tok)

## .claude/

- `settings.json` (~441 tok)

## .claude/rules/

- `openwolf.md` (~313 tok)

## parallax_v1_3_artifact_pack/

- `AGENT_START_HERE.md` — Agent Start Here — Parallax v1.3 (~1277 tok)
- `CHECKSUMS.sha256` (~3549 tok)
- `MANIFEST.txt` — Parallax v1.3 artifact manifest (~3602 tok)
- `README.md` — Project documentation (~1446 tok)
- `VALIDATION_REPORT.md` — Validation Report — Parallax v1.3 Artifact Pack (~2178 tok)
- `VERSION.txt` (~16 tok)

## parallax_v1_3_artifact_pack/contracts/design/

- `design_tokens.css` — Styles: 83 vars (~1006 tok)
- `design_tokens.json` (~1561 tok)
- `README.md` — Project documentation (~89 tok)

## parallax_v1_3_artifact_pack/contracts/events/

- `parallax_event_contracts_v1_3.yaml` (~1523 tok)

## parallax_v1_3_artifact_pack/contracts/jobs/

- `parallax_workflows_v1_3.yaml` (~1807 tok)

## parallax_v1_3_artifact_pack/contracts/json_schema/

- `activity_profile.schema.json` (~16666 tok)
- `activity.schema.json` (~1947 tok)
- `capture_context_snapshot.schema.json` (~1089 tok)
- `common.schema.json` (~2522 tok)
- `context_capture_policy.schema.json` (~557 tok)
- `device_context_observation.schema.json` (~588 tok)
- `extracted_context_event.schema.json` (~2268 tok)
- `geospatial_observation.schema.json` (~614 tok)
- `inferred_place_observation.schema.json` (~452 tok)
- `model_update_decision.schema.json` (~1874 tok)
- `mutation_envelope.schema.json` (~1811 tok)
- `preflight_check.schema.json` (~1978 tok)
- `privacy_settings.schema.json` (~1968 tok)
- `radio_observation.schema.json` (~680 tok)
- `temporal_context_annotation.schema.json` (~2256 tok)
- `temporal_feature_vector.schema.json` (~544 tok)
- `temporal_prediction.schema.json` (~2162 tok)
- `temporal_query_answer.schema.json` (~2154 tok)
- `timing_event_span.schema.json` (~2099 tok)
- `timing_event.schema.json` (~2107 tok)
- `timing_review_flag.schema.json` (~490 tok)
- `timing_session.schema.json` (~7786 tok)
- `user_place.schema.json` (~478 tok)
- `workflow_payloads.schema.json` (~1857 tok)

## parallax_v1_3_artifact_pack/contracts/openapi/

- `parallax_api_v1_3.yaml` (~37370 tok)

## parallax_v1_3_artifact_pack/contracts/pydantic/

- `parallax_contracts_v1_3.py` — Pydantic-compatible core and context contracts for Parallax v1.3. (~6707 tok)

## parallax_v1_3_artifact_pack/database/

- `README.md` — Project documentation (~1000 tok)

## parallax_v1_3_artifact_pack/database/migrations/

- `0001_extensions_and_enums.sql` — Parallax v1.3 migration 0001 (~1196 tok)
- `0002_identity_privacy_audit.sql` — Parallax v1.3 migration 0002 (~679 tok)
- `0003_activity_identity.sql` — Parallax v1.3 migration 0003 (~709 tok)
- `0004_timing_core.sql` — Parallax v1.3 migration 0004 (~2537 tok)
- `0005_context_extraction_preflight.sql` — Parallax v1.3 migration 0005 (~1919 tok)
- `0006_reviews_predictions_evidence.sql` — Parallax v1.3 migration 0006 (~1892 tok)
- `0007_retrieval_pgvector.sql` — Parallax v1.3 migration 0007 (~958 tok)
- `0008_jobs_sync_model_audit.sql` — Parallax v1.3 migration 0008 (~1144 tok)
- `0011_capture_context_geospatial_sensor_fusion.sql` — Parallax v1.3 migration 0011 (~3788 tok)
- `0014_timing_review_flags.sql` — Parallax v1.3 migration 0014 (~457 tok)
- `9999_seed_dev_data.sql` — Parallax v1.3 migration 9999 (~291 tok)

## parallax_v1_3_artifact_pack/database/optional_profiles/

- `0009_timescale_optional_analytics_profile.sql` — Parallax v1.3 migration 0009 (~622 tok)
- `0010_paradedb_optional_search_profile.sql` — Parallax v1.3 migration 0010 (~123 tok)
- `0012_postgis_optional_geospatial_profile.sql` — Parallax v1.3 migration 0012 (~542 tok)
- `0013_timescale_capture_context_profile.sql` — Parallax v1.3 migration 0013 (~610 tok)

## database/

- `README.md` — root database helper README for baseline migrations versus optional profiles (~140 tok)

## database/optional_profiles/

- `0009_timescale_optional_analytics_profile.sql` — root-copied optional Timescale analytics shadow profile; excluded from baseline migrations (~622 tok)
- `0010_paradedb_optional_search_profile.sql` — root-copied optional ParadeDB BM25 retrieval profile (~123 tok)
- `0012_postgis_optional_geospatial_profile.sql` — root-copied optional PostGIS geography/GiST profile preserving numeric lat/lon baseline (~542 tok)
- `0013_timescale_capture_context_profile.sql` — root-copied optional Timescale capture-context shadow analytics profile (~610 tok)

## parallax_v1_3_artifact_pack/database/queries/

- `activity_profile.sql` — Activity Profile query examples. (~306 tok)
- `ask_about_time_queries.sql` — Ask About Time deterministic fact examples. (~338 tok)
- `context_geospatial_queries.sql` — Parallax v1.3 context/geospatial query examples. (~562 tok)
- `privacy_export_delete_queries.sql` — Privacy export/redaction/delete examples. (~2226 tok)
- `search_retrieval_queries.sql` — Retrieval examples. (~213 tok)
- `timing_semantics_examples.sql` — Timing semantics examples. (~237 tok)

## parallax_v1_3_artifact_pack/database/rollback/

- `README.md` — Project documentation (~218 tok)

## parallax_v1_3_artifact_pack/docs/

- `00_pack_summary.md` — 00 — Pack Summary (~897 tok)
- `01_app_system_spec.md` — 01 — Complete App and System Specification (~2432 tok)
- `02_temporal_domain_model.md` — 02 — Temporal Domain Model (~3390 tok)
- `03_phased_implementation_plan.md` — 03 — Phased Implementation Plan (~4273 tok)
- `04_user_stories_acceptance_criteria.md` — 04 — User Stories and Acceptance Criteria (~2701 tok)
- `05_design_language_figma_handoff.md` — 05 — Design Language and Figma Handoff Specification (~2347 tok)
- `06_architecture_runtime.md` — 06 — Architecture and Runtime Specification (~1541 tok)
- `07_data_model_semantics.md` — 07 — Data Model and Temporal Semantics (~1744 tok)
- `08_api_and_offline_sync_spec.md` — 08 — API and Offline Sync Specification (~1556 tok)
- `09_ai_ml_retrieval_and_eval_spec.md` — 09 — AI, Retrieval, and Evaluation Specification (~1518 tok)
- `10_security_privacy_nfr.md` — 10 — Security, Privacy, and Nonfunctional Requirements (~1535 tok)
- `11_observability_operations_runbook.md` — 11 — Observability, Operations, and Runbooks (~1206 tok)
- `12_testing_qa_release_rollback.md` — 12 — Testing, QA, Evaluation, Release, Migration, and Rollback Strategy (~1176 tok)
- `13_repository_layout_coding_standards.md` — 13 — Repository Layout and Coding Standards (~851 tok)
- `14_adrs.md` — 14 — Architectural Decision Records Summary (~1436 tok)
- `15_risk_register_open_questions.md` — 15 — Risk Register and Open Questions (~1060 tok)
- `16_traceability_matrix.md` — 16 — Requirements Traceability Matrix (~773 tok)
- `17_agentic_coder_review_and_drift_prompts.md` — 17 — Agentic Coder Kickoff, Review, and Drift-Control Prompts (~1084 tok)
- `18_timing_analytics_and_context_intelligence.md` — 18 — Timing Analytics and Context Intelligence (~2441 tok)
- `19_capture_workflows_and_sensor_fusion.md` — 19 — Capture Workflows, Real-World Scenarios, and Sensor Fusion (~2188 tok)
- `20_mobile_location_radio_privacy_reference.md` — 20 — Mobile Location, Radio Context, and Privacy Reference (~1650 tok)
- `21_current_platform_and_extension_references.md` — 21 — Current Platform and Extension Reference Links (~683 tok)
- `22_v1_3_gap_closure_summary.md` — 22 — v1.3 Gap Closure Summary (~1576 tok)
- `23_agentic_implementation_guardrails.md` — 23 — Agentic Implementation Guardrails (~1628 tok)

## parallax_v1_3_artifact_pack/examples/payloads/

- `sample_activity_profile_response.json` (~435 tok)
- `sample_capture_context_snapshot.json` (~1176 tok)
- `sample_context_capture_policy.json` (~174 tok)
- `sample_create_place_request.json` (~156 tok)
- `sample_place_change_forgotten_timer_scenario.json` (~170 tok)
- `sample_sponge_detour_run.json` (~394 tok)
- `sample_sync_push.json` (~266 tok)
- `sample_temporal_feature_vector.json` (~290 tok)
- `sample_temporal_query_answer.json` (~299 tok)
- `sample_timing_review_flag.json` (~208 tok)

## parallax_v1_3_artifact_pack/examples/reference_mockups/

- `README.md` — Project documentation (~115 tok)

## parallax_v1_3_artifact_pack/infrastructure/caddy/

- `Caddyfile.example` (~28 tok)

## parallax_v1_3_artifact_pack/infrastructure/compose/

- `docker-compose.parallax.prototype.yml` — Docker Compose: 9 services (~694 tok)

## parallax_v1_3_artifact_pack/infrastructure/object_storage/

- `object_storage_plan.md` — Object Storage Plan (~273 tok)

## parallax_v1_3_artifact_pack/infrastructure/zfs/

- `create_parallax_datasets.sh` (~334 tok)
- `zfs_dataset_plan.md` — ZFS Dataset Plan (~375 tok)

## parallax_v1_3_artifact_pack/scripts/

- `bootstrap_dev.sh` (~116 tok)
- `generate_manifest.py` — digest, main (~236 tok)
- `validate_pack.py` — sha, parse_manifest, resolve_openapi_ref, schema_requires_mutation + 2 more (~2812 tok)

## packages/db/parallax_db/

- `migrations.py` — baseline migration discovery order excluding optional profiles, including Phase 3 context/review migrations (~90 tok)
- `runner.py` — baseline SQL migration application and current schema smoke checks through Phase 3 (~330 tok)

## scripts/

- `apply_gpu_node_permissions.sh` — permission-only application for `/srv/parallax` runtime trees (~125 tok)
- `apply_migrations.py` — repo-root runnable baseline migration CLI with optional schema smoke checks (~120 tok)
- `phase2_smoke.py` — GPU-node Phase 2 review/profile acceptance smoke covering review, discard, spans, stats snapshots, and SQL proof (~560 tok)
- `phase3_smoke.py` — GPU-node Phase 3 context capture acceptance smoke covering annotations, capture policy/snapshots, places, review flags, and SQL proof (~760 tok)
- `phase9_smoke.py` — Docker-backed Phase 9 optional-extension smoke for pgvector HNSW, ParadeDB BM25, PostGIS ST_DWithin/GiST, Timescale continuous aggregates, backup/restore, and k3s static checks (~1500 tok)
- `setup_gpu_node_storage.sh` — GPU-node ZFS dataset, repo checkout, venv directory, and permission bootstrap (~205 tok)

## infra/k3s/base/

- `parallax-namespace.yaml` — k3s namespace, secret contract, and production config map for Parallax (~190 tok)
- `parallax-storage.yaml` — local-path PVCs for Postgres data/WAL, objects, and logs (~160 tok)
- `parallax-data-plane.yaml` — ClusterIP Postgres, Redis, and MinIO services/workloads with probes and storage mounts (~720 tok)
- `parallax-app-plane.yaml` — ClusterIP Temporal/API/worker/model endpoint manifests with secret wiring and health probes (~760 tok)

## docs/architecture/

- `phase9_optional_extension_hardening.md` — Phase 9 scope, Firecrawl-backed extension notes, re-embedding/dual-read plan, k3s boundary, and verification contract (~850 tok)

## tests/

- `test_phase9_optional_extension_hardening.py` — Phase 9 structural tests for optional profile placement, Makefile wiring, k3s manifest contracts, PostGIS preservation, and re-embedding docs (~360 tok)

## services/api/

- `Dockerfile` — Phase 0 API image using uv and non-root UID 10001 (~80 tok)

## services/api/parallax_api/

- `healthcheck.py` — container healthcheck client for `/v1/health` (~65 tok)
- `main.py` — FastAPI app factory and dependency wiring (~70 tok)

## services/api/parallax_api/routes/

- `context.py` — thin Phase 3 route layer for annotations, context capture policy/snapshots, places, and review flags (~420 tok)

## services/api/parallax_api/domain/

- `activity_stats.py` — pure Activity Profile percentile, confidence, limitation, and top-friction calculation (~210 tok)
- `review_decisions.py` — canonical review-decision to model-inclusion/status/run-quality policy helpers (~115 tok)
- `timing_spans.py` — pure timing-event span derivation and active/wall/friction total calculation (~430 tok)

## services/api/parallax_api/repositories/

- `context_repository.py` — in-memory Phase 3 context annotations, policies, snapshots, places, and review flags repository (~520 tok)
- `postgres_context_repository.py` — PostgreSQL Phase 3 context repository and row mapping for context tables (~970 tok)
- `postgres_profile_repository.py` — PostgreSQL Activity Profile recomputation and profile loading from reviewed sessions/stats snapshots (~280 tok)
- `profile_repository.py` — in-memory Activity Profile recomputation and loading for unit/API tests (~140 tok)

## services/api/parallax_api/schemas/

- `context.py` — Pydantic DTOs for Phase 3 context annotations, capture policy/snapshots, places, and review flags (~460 tok)
- `profile.py` — Pydantic DTOs for Activity Profile stats and response shape (~85 tok)

## services/api/parallax_api/services/

- `context_service.py` — Phase 3 context orchestration, mutation replay, privacy policy filtering, place handling, and review flags (~750 tok)
- `profile_service.py` — thin Activity Profile service that maps missing profile/activity to 404 (~45 tok)
- `health.py` — Postgres/Redis runtime health checks behind a small service interface (~130 tok)

## services/api/tests/

- `test_health.py` — API health/version tests with injected health checkers (~120 tok)
- `test_phase2_review_profile.py` — Phase 2 API acceptance tests for review/discard decisions, span counts, replay, and Activity Profile stats (~530 tok)
- `test_phase3_context_capture.py` — Phase 3 API acceptance tests for annotations, policy filtering, snapshots, places, review flags, and sync replay (~720 tok)

## services/worker/

- `Dockerfile` — Phase 0 worker image using uv and non-root UID 10001 (~80 tok)

## services/worker/parallax_worker/

- `__init__.py` — worker package marker (~10 tok)
- `main.py` — minimal Phase 0 worker process bootstrap (~70 tok)

## tests/

- `test_phase0_bootstrap.py` — Phase 0 bootstrap regression tests for artifact hygiene, Compose, CI, migrations, and script runnable path (~230 tok)

## docs/architecture/

- `phase0_bootstrap.md` — Phase 0 scope, runtime paths, service boundaries, and verification commands (~220 tok)
- `phase2_review_profile.md` — Phase 2 implemented endpoint subset, architecture, counting semantics, and verification gate (~150 tok)
- `phase3_context_capture.md` — Phase 3 implemented endpoint subset, privacy policy behavior, Phase 4 seams, and verification gate (~170 tok)

## docs/superpowers/plans/

- `2026-04-28-phase-2-review-profile.md` — Detailed Phase 2 implementation plan and acceptance mapping (~520 tok)
- `2026-04-28-phase-3-context-capture.md` — Detailed Phase 3 implementation plan, TDD checklist, and Phase 2/4 seam mapping (~750 tok)

## parallax_v1_3_artifact_pack/source_inputs/

- `source_alignment_summary.md` — Source Artifact Alignment Summary (~494 tok)

## parallax_v1_3_artifact_pack/tests_or_eval/

- `accessibility_checklist.md` — Accessibility Checklist (~107 tok)
- `capture_workflow_scenario_matrix.csv` (~197 tok)
- `context_extraction_eval_cases.jsonl` (~176 tok)
- `geospatial_context_eval_cases.jsonl` (~153 tok)
- `privacy_review_checklist.md` — Privacy Review Checklist (~228 tok)
- `query_grounding_eval_cases.jsonl` (~118 tok)
- `release_gate_checklist.md` — Release Gate Checklist (~224 tok)
- `sensor_privacy_test_matrix.csv` (~132 tok)
- `temporal_semantics_test_matrix.csv` (~371 tok)
- `test_plan.md` — Test and QA Plan (~183 tok)
- `timing_analytics_feature_tests.csv` (~81 tok)
