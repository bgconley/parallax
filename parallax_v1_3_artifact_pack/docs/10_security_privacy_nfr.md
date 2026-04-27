# 10 — Security, Privacy, and Nonfunctional Requirements

## Security posture

Parallax handles sensitive personal context. Security and privacy are product requirements, not add-ons.

## Data sensitivity

Sensitive data includes:

- raw context notes;
- transcripts;
- audio;
- embeddings;
- exact timing patterns;
- location hints;
- activity names that reveal routines;
- model prompts and outputs;
- query answers that quote evidence.

## Authentication and authorization

P0 implementation may use a simple private-alpha auth provider, but the backend must be designed around authenticated user scope.

Requirements:

- API infers `user_id` from auth context.
- Every query is user-scoped.
- Cross-user data isolation tests are mandatory.
- Service-to-service credentials are separate from user auth.
- Model endpoints are internal only.

## Secrets

- No secrets in repository.
- `.env.example` documents variables without real values.
- Production/staging secrets come from a secret manager or environment injection.
- Logs must not print secrets.

## Raw context handling

- Raw context is never written to normal application logs.
- Raw context can be retained, redacted, or deleted according to privacy settings.
- `context_capture_policy` is the server-side control plane for location, radio,
  motion, and device context capture. Client OS permissions do not authorize
  capture unless this policy also enables it.
- Audio retention defaults off.
- Cloud LLM fallback defaults off.
- Sensitive/private notes are not embedded by default.
- Raw quotes in Ask answers are opt-in.
- Context-specific delete scopes must cover location context, radio context, place
  context, and context-derived feature vectors. Deleting or redacting any context
  source must invalidate retrieval documents, evidence items, and feature vectors
  derived from it.

## Encryption

- Use TLS for network ingress.
- Encrypt backups.
- Prefer encrypted object storage or encrypted volumes for raw audio/export artifacts.
- Database-at-rest encryption depends on deployment environment and should be documented.

## Audit logging

Audit log should capture:

- privacy setting changes;
- context capture policy changes;
- export/delete/redaction requests;
- activity merges;
- correction events;
- admin/service access where applicable;
- model fallback use.

Audit logs should not include raw sensitive payloads.

## Reliability requirements

- Timer source actions must be accepted without model availability.
- Duplicate mutation replay must not double-count.
- Workflow retries must be idempotent.
- Derived projections can lag but must recover.
- App must recover active runs after client relaunch.
- Backups and restore tests are required before alpha.

## Observability requirements

Track:

- API latency and error rates;
- event append latency;
- idempotency duplicate rate;
- workflow backlog;
- extraction schema-valid rate;
- model latency and repair count;
- query grounding eval pass rate;
- backup freshness;
- object storage errors.

## Accessibility requirements

- Minimum touch target: 44 pt.
- Preferred touch target: 48 pt.
- Dynamic Type support required.
- High contrast support required.
- Color-only semantic states are disallowed.
- Reduced motion alternatives required.
- Primary mobile screens should avoid dense tables.

## Performance requirements

P0 targets:

- event append p95 under 300 ms on local network;
- activity list p95 under 500 ms;
- session retrieval p95 under 500 ms;
- review save p95 under 750 ms excluding async recomputation;
- context annotation save p95 under 500 ms excluding model processing;
- extraction can be async with progress/pending state;
- query answers can return pending for complex jobs.

## Maintainability requirements

- Contracts are versioned.
- Schema changes require migrations.
- Enum changes require compatibility review.
- Generated code must be reproducible.
- Tests must cover contracts, sync, privacy, counting semantics, and query grounding.
- Architectural deviations require ADRs.

## Backup and restore requirements

- PostgreSQL backup must be database-aware.
- WAL archiving or equivalent is required before alpha.
- Object storage backup required.
- Restore test required before alpha.
- Backup retention must account for privacy deletion policy.
- Export/delete workflows must document backup implications.


## v1.3 location, radio, and ambient context privacy requirements

Location, Wi-Fi, BLE, UWB, cell, motion, and device-state context are personal data and must be treated as privacy-sensitive even when approximate.

### Requirements

- Sensor permissions must be requested feature-by-feature, not all at first launch.
- Timing must work with all sensor permissions denied.
- Raw SSID, BSSID, MAC address, beacon identifier, UWB peer identifier, and cell identifiers must not be stored by default.
- Radio identifiers must be salted per user before durable storage unless encrypted short-retention raw storage is explicitly enabled.
- `redacted_display_label` may store only user-provided or explicitly redacted
  safe labels; raw radio identifiers belong only in encrypted short-retention
  artifacts when policy allows them.
- Sensitive place labels must require user confirmation.
- Raw precise coordinates must support retention limits, export, redaction, and deletion.
- Context snapshots must record permission state and retention policy.
- Logs must not include raw coordinates, raw radio identifiers, or raw place labels.
- Background location collection requires explicit user-enabled workflow and prominent disclosure.
- Context-derived features must be invalidated or regenerated after privacy setting changes.

### Privacy acceptance tests

- Deny all permissions and complete the timing vertical slice.
- Enable approximate place only and verify precise coordinates are absent.
- Enable and then redact place context; verify observations, features, retrieval docs, and evidence are updated.
- Attempt to log raw radio identifiers and verify scrubbing.
- Confirm that a place labeled private is not exposed in Ask About Time without permission.
