# 12 — Testing, QA, Evaluation, Release, Migration, and Rollback Strategy

## Test pyramid

### Unit tests

Cover:

- enum mappings;
- Pydantic validation;
- timing reconstruction;
- span count policy;
- model inclusion logic;
- privacy filters;
- deterministic statistics;
- query intent parsing where deterministic.

### Integration tests

Cover:

- migrations;
- API endpoints;
- idempotency and duplicate replay;
- Temporal workflow dispatch;
- Postgres transactions;
- object storage operations;
- retrieval document lifecycle.

### Contract tests

Cover:

- OpenAPI schema generation;
- JSON Schema validation;
- event/job contracts;
- request/response examples;
- UI view-model mapping.

### End-to-end tests

Cover:

- first vertical slice;
- context annotation and extraction;
- run review and recomputation;
- Activity Profile update;
- grounded query with evidence;
- export/delete workflow.

## Required semantic tests

Use `tests_or_eval/temporal_semantics_test_matrix.csv` as the seed matrix.

Core scenarios:

- clean whole-task run;
- pause/resume;
- resource detour;
- interruption;
- waiting;
- side quest;
- forgot-to-stop;
- partial run;
- assisted run;
- start latency;
- transition latency;
- checkpoint expansion;
- annotation correction.

## LLM evaluation

Use golden JSONL files in `tests_or_eval/`.

Metrics:

- schema validity;
- category accuracy;
- count policy accuracy;
- confidence tier calibration;
- sensitive-data detection;
- hallucinated fact rate;
- evidence reference validity;
- privacy quote violation rate.

## Release stages

### Developer prototype

Goal: prove first vertical slice.

Gate:

- migrations through Phase 2;
- activity/session/review APIs;
- contract tests;
- no raw logging;
- local Compose.

### Private alpha

Goal: real user testing with privacy controls.

Gate:

- context capture;
- review correction;
- basic Activity Profile;
- backup/restore;
- export/delete;
- accessibility pass;
- cross-user isolation pass.

### Expanded alpha

Goal: structured extraction and grounded Ask.

Gate:

- eval pass thresholds;
- model fallback policy;
- evidence bundle audit;
- correction loop;
- opt-in privacy controls.

### Beta

Goal: operational hardening and optional extension profiles.

Gate:

- optional search/analytics profiles measured;
- SLO dashboards;
- k3s readiness if needed;
- incident runbooks exercised.

## Migration strategy

- Use ordered migrations.
- Never alter enum values casually; add compatible values and deprecate old values if needed.
- Never drop raw context without export/delete migration.
- Every migration has a rollback note or irreversible marker.
- Test migrations on a copy of realistic data before alpha/beta.

## Rollback strategy

### Code rollback

Use previous image/version if database schema remains compatible.

### Migration rollback

Use rollback scripts only before user data depends on the migration. For irreversible migrations, restore from backup or run compensating migration.

### Workflow rollback

Disable feature flag for workflow trigger. Existing workflows should either complete under old handler or be marked for replay with a migration handler.

### Model rollback

Switch prompt/schema/model version via config. Do not delete model invocation rows.

### Contract rollback

If API contract changes break clients, restore previous endpoint behavior or introduce versioned compatibility.

## QA checklist

Before handing any phase to the next phase:

- Acceptance criteria pass.
- Contract examples validate.
- User scoping tests pass.
- Privacy checks pass.
- Timing semantics tests pass.
- Observability events emitted.
- Documentation updated.
- ADR added if architecture changed.


## v1.3 timing/context QA additions

New test families:

- capture context schema validation;
- all-permissions-denied timing vertical slice;
- context capture policy disables capture despite granted OS permission;
- approximate-location-only flow;
- raw radio identifier scrubbing;
- location/radio/place/context-feature delete scope invalidation;
- idempotent context snapshot replay;
- timing event arrives before context snapshot;
- context snapshot arrives before timing event reconciliation;
- possible forgotten timer review flag;
- review flag resolve/dismiss flow does not mutate timing totals;
- user-confirmed place creation/correction/redaction;
- contextual feature vector eligibility;
- PostGIS optional migration smoke test when enabled;
- Timescale context-profile optional migration smoke test when enabled.

Release gate addition:

No alpha release should claim place-aware or context-aware estimates until place inference, privacy redaction, and contextual calibration evals pass.
