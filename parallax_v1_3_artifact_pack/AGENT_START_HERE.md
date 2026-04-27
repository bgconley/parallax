# Agent Start Here — Parallax v1.3

You are implementing **Parallax**, a temporal-first personal intelligence app. Your first task is not to code. Your first task is to internalize this artifact pack, verify it is coherent, and create an execution plan that follows these documents unless you identify a concrete technical flaw.

## Source-of-truth hierarchy

Use this precedence order when files appear to overlap:

1. `AGENT_START_HERE.md`
2. `docs/01_app_system_spec.md`
3. `docs/02_temporal_domain_model.md`
4. `database/migrations/*.sql`
   (`database/optional_profiles/*.sql` only when the matching optional profile is enabled)
5. `contracts/openapi/parallax_api_v1_3.yaml`
6. `contracts/json_schema/*.schema.json`
7. `contracts/events/parallax_event_contracts_v1_3.yaml`
8. `contracts/jobs/parallax_workflows_v1_3.yaml`
9. `docs/18_timing_analytics_and_context_intelligence.md`
10. `docs/19_capture_workflows_and_sensor_fusion.md`
11. `docs/20_mobile_location_radio_privacy_reference.md`
12. `docs/03_phased_implementation_plan.md`
13. `docs/22_v1_3_gap_closure_summary.md`
14. `docs/23_agentic_implementation_guardrails.md`
15. Design guidance, examples, tests, and runbooks

If implementation reality requires changing a contract, update the affected artifact and add an ADR before treating the implementation as the new truth.

`contracts/pydantic/parallax_contracts_v1_3.py` is a convenience scaffold only.
OpenAPI and JSON Schema remain canonical for implementation and code generation.

## What to build first

Build the temporal substrate before AI features.

The first vertical slice is:

1. Repository skeleton and local runtime.
2. Core migrations through `0006_reviews_predictions_evidence.sql`.
3. API health/version/auth stub.
4. Activity create/list/get.
5. Timing session create/start/event append/complete/get.
6. Run review and simple activity stats snapshot.
7. Contract tests proving offline/idempotent replay does not double-count.
8. Minimal UI or API client proof that a user can time one activity, finish it, review it, and see a personal range.

Do not begin model serving, Ask About Time, contextual ML, PostGIS, ParadeDB, or Timescale hardening before the core temporal loop and context privacy posture are reliable.

## Required implementation posture

Parallax is not a timesheet, not a generic planner, and not a chatbot with timers attached. The app is about making lived time observable and correctable. The implementation should reflect that:

- The timer works offline.
- The event log is append-safe.
- Review controls model inclusion.
- Context capture saves raw notes safely before interpretation.
- LLM-derived objects are candidates until validated and confirmed when needed.
- Activity Profile and Ask About Time are evidence-backed projections.

## Naming rules

The project name is **Parallax**. Use:

- `parallax` for package, database, Docker, dataset, environment, and service names.
- `Parallax` for product-facing copy.
- `PARALLAX_` for environment variable prefixes.
- `api.parallax.local` and `schemas.parallax.local` for local contract examples.

Do not introduce older placeholders or retired names in new files. The only acceptable use of "Temporal" is for the Temporal workflow engine or as the adjective "temporal-first".

## Before coding, produce this kickoff plan

Produce the following in your coding conversation:

1. Artifact comprehension summary.
2. Source-of-truth file map.
3. Safe implementation assumptions.
4. Implementation blockers, if any.
5. Contradictions found, if any.
6. Repository initialization plan.
7. First-sprint implementation plan.
8. Test-first strategy for the first sprint.
9. Migration/bootstrap order for DB, services, queues, storage, and UI.
10. Definition of done for the first working vertical slice.

Then implement Phase 0 and Phase 1 from `docs/03_phased_implementation_plan.md`.

## Hard stop conditions

Stop and request artifact update if any of these occur:

- A schema enum conflicts with the OpenAPI enum.
- An API request/response cannot be represented by the JSON schemas.
- A mutating endpoint cannot carry a mutation envelope or a resolver endpoint needs
  to write data.
- A proposed implementation would let LLM output directly update duration baselines.
- A proposed implementation would store raw notes, transcripts, prompts, or audio in normal logs.
- A mobile capture path bypasses `context_capture_policy`.
- A proposed migration would drop or rewrite raw context without export/delete handling.
- A feature requires optional PostGIS, ParadeDB, pgvector, or TimescaleDB before the baseline Postgres path works.

## v1.3 implementation emphasis

The implementation agent must treat context capture as auxiliary evidence. Build timing first, then context snapshots, then place/context inference, then contextual analytics. Do not build passive background tracking as the first implementation. The first context-aware vertical slice should prove that timing works with all permissions denied, then prove that optional approximate place context improves review without compromising privacy.
