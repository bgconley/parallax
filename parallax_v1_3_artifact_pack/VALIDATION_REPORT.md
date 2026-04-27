# Validation Report — Parallax v1.3 Artifact Pack

Generated: 2026-04-26

Revision pass: 2026-04-26

## Result

**VALIDATION PASSED**

This report covers the regenerated `parallax_v1_3_artifact_pack/` folder and the corresponding `parallax_v1_3_artifact_pack.zip` bundle.

The revision passes resolve implementation-handoff drift found during full-pack
review: API server base path double-prefix risk, context snapshot link drift
across SQL/OpenAPI/JSON Schema/Pydantic contracts, optional migration ordering
ambiguity, design token version metadata, missing transition/context fields in
derived response schemas, mutation-envelope gaps, missing context-capture policy
contracts, missing timing-review-flag persistence/API contracts, context snapshot
create-request linkage gaps, privacy export/delete coverage gaps, ambiguous radio
label semantics, validator extraction ergonomics, and optional Timescale percentile
profile caveats. The pack also makes the retrieval migration create baseline
PostgreSQL full-text search tables without requiring pgvector.

## Scope validated

The v1.3 pack was created as a gap-closure update to the v1.2 canonical handoff. The update specifically adds:

- timing analytics and context-intelligence requirements;
- capture-method-specific workflow requirements;
- mobile location, Wi-Fi, BLE, beacon, motion, and device-context guidance;
- context snapshot, context-capture policy, geospatial observation, radio observation, device context, inferred place, timing review flag, and temporal feature vector schemas;
- ordered SQL migrations for the baseline context model and timing review flags plus separated optional PostGIS, ParadeDB, and TimescaleDB profile scripts;
- OpenAPI endpoints for capture-context snapshots, context-capture policy, place resolution, place management, timing review flags, and feature-vector recomputation;
- explicit context-specific privacy delete scopes and SQL examples for context export/redaction/deletion;
- user stories and acceptance criteria for real-world capture scenarios;
- evaluation matrices for capture workflow, geospatial inference, privacy, and contextual timing features.

## Checks performed

- ZIP exists at `parallax_v1_3_artifact_pack.zip`.
- ZIP contents match every file in `parallax_v1_3_artifact_pack/`.
- `MANIFEST.txt` matches the generated file tree, file sizes, and SHA-256 hashes.
- Required core files exist and are non-empty.
- JSON files parse successfully.
- JSON Schema files pass Draft 2020-12 schema checks.
- v1.3 example payloads validate against their corresponding JSON schemas where direct schema mapping exists.
- YAML files parse successfully.
- Python files parse successfully with `ast.parse`.
- Shell scripts pass basic shell syntax checks.
- Ordered baseline SQL migration files exist for required prefixes `0001` through `0008`, `0011`, `0014`, plus dev seed `9999`.
- Optional profile SQL files exist under `database/optional_profiles/` for prefixes `0009`, `0010`, `0012`, and `0013`.
- SQL files are structurally plausible: terminate with semicolons and pair `BEGIN;`/`COMMIT;` where used.
- Retired naming patterns were scanned from source-facing text files.
- OpenAPI, JSON Schema, event contracts, workflow contracts, design tokens, infrastructure files, examples, mockup references, and eval files are present.
- v1.3 context additions were checked for cross-artifact presence in docs, SQL, OpenAPI, JSON Schema, Pydantic-compatible contracts, event contracts, workflow contracts, examples, tests/evals, source alignment notes, and the gap-closure summary.
- OpenAPI server URLs were checked against `/v1` path declarations to avoid `/v1/v1` client-generation drift.
- JSON Schema and OpenAPI component property/required sets were checked for direct schema mappings.
- SQL, JSON Schema, OpenAPI, and Pydantic-compatible enum values were checked for conflicts where names overlap.
- Context snapshot linkage is represented as both a server-resolved `capture_context_snapshot_id` and an offline-safe `capture_context_snapshot_ref`.
- Mutation-envelope enforcement was checked across mutating OpenAPI operations, with explicit read-only exemptions for activity/place resolver POST endpoints.
- `context_capture_policy` and `timing_review_flag` are represented across SQL, OpenAPI, JSON Schema, Pydantic-compatible contracts, docs, examples, and test guidance.
- `CreateCaptureContextSnapshotRequest` includes optional `checkpoint_run_id` and `user_place_id` linkage fields.
- Radio observation contracts use `redacted_display_label` with explicit prohibition on raw radio identifiers.
- `scripts/validate_pack.py` supports extracted-folder use through advisory default ZIP checks plus `--zip-path`, `--skip-zip-check`, and `--require-zip`.

## Internal consistency notes

- Product name is canonicalized as **Parallax**.
- `user_id` remains the canonical identity field in backend/database contracts.
- UI state remains a projection of the backend/domain model.
- Timing correctness remains based on append-safe source events and derived spans, not direct model output.
- Context capture is auxiliary evidence, not a replacement for explicit timing events.
- Out-of-order offline replay uses `capture_context_snapshot_ref` until a direct snapshot foreign key can be resolved.
- Geospatial/radio/device observations are permission-gated and retention-scoped.
- Radio labels must be user-provided or explicitly redacted safe labels; raw SSID,
  BSSID, MAC, beacon, UWB peer, and cell identifiers are not valid display labels.
- `context_capture_policy` is the server-authoritative capture and retention gate for optional sensor context.
- `timing_review_flag` rows are review prompts and do not mutate source timing facts.
- Optional PostGIS, TimescaleDB, ParadeDB, and pgvector paths are documented as feature profiles rather than baseline dependencies.
- Extension-only PostGIS, TimescaleDB, and ParadeDB SQL lives outside the baseline migration namespace in `database/optional_profiles/`.
- Migration `0007_retrieval_pgvector.sql` keeps baseline lexical retrieval usable without pgvector and creates vector embedding tables only when the extension can be enabled.

## Tooling environment note

The validation command returned exit code `0` and printed `VALIDATION PASSED` on stdout.

## Validation limits

- SQL was not executed against a live PostgreSQL, PostGIS, pgvector, ParadeDB, or TimescaleDB instance in this artifact-generation environment.
- OpenAPI/YAML/JSON files were parsed for syntax and structural plausibility; the OpenAPI document was not run through every downstream code generator.
- Mobile platform APIs and permissions are documented using current references at pack generation time, but the implementation agent must re-check platform documentation during implementation.
- Figma was not modified directly. The pack includes design language, tokens, reference mockups, mobile capture workflow guidance, and Figma handoff instructions for a Figma-capable implementation agent.
- Optional PostGIS, ParadeDB, and TimescaleDB migrations are intentionally profile scripts and require compatibility testing before use in the target database image.
- Optional Timescale profiles `0009` and `0013` use exact `percentile_cont`
  continuous-aggregate expressions in this artifact. Live-test those expressions
  against the selected Timescale/Tiger image before enabling, or switch the
  continuous-aggregate path to Timescale Toolkit approximate percentile aggregates.

## Recommended next validation by implementation agent

1. Run the repository bootstrap from `docs/03_phased_implementation_plan.md`.
2. Apply migrations `0001` through `0006` and `0008` to a clean local PostgreSQL database.
3. Apply migration `0007` for retrieval smoke tests; run it once without pgvector and once with pgvector when available.
4. Apply migration `0011` after the core timing/event tables are available.
5. Apply migration `0014` after `0011` when implementing persisted timing review flags.
6. Apply optional profiles only in matching compatibility environments:
   `0009` for Timescale analytics, `0010` for ParadeDB search, `0012` for PostGIS,
   and `0013` for Timescale context analytics.
7. Run OpenAPI code generation for the chosen implementation stack.
8. Validate v1.3 sample payloads against JSON schemas.
9. Execute the first timing vertical-slice test with all mobile sensor permissions denied.
10. Execute the first context-aware timing review test with coarse location enabled and raw radio capture disabled.
11. Run `scripts/validate_pack.py --skip-zip-check` after extracting into an implementation repository, or `--zip-path` when validating a specific rebuilt archive.
