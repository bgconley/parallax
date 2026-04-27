# 16 — Requirements Traceability Matrix

| Requirement | Source | Canonical artifact | Phase | Test/eval |
|---|---|---|---:|---|
| Parallax naming only | User direction | README, AGENT_START_HERE, validation | 0 | retired-name scan |
| Offline-safe timing | Product core | API sync spec, DB migrations, OpenAPI | 1 | offline sync tests |
| Active/wall/friction separation | Product core | domain model, SQL schema | 1–2 | temporal semantics matrix |
| User-controlled model learning | Product core | model_update_decision schema/API | 2 | review API tests |
| Context annotation capture | Product core | annotation schema/API | 3 | annotation integration tests |
| Structured extraction | AI workflow | extraction schema/jobs | 4 | context extraction evals |
| Correction audit trail | Trust model | temporal_correction table/API | 4 | correction tests |
| Checkpoints | UI/backend requirement | checkpoint tables/API | 5 | checkpoint E2E tests |
| Start latency | Temporal objective | start_latency table/API/profile | 5 | start latency tests |
| Activity identity | Data quality | alias/relationship schema/API | 6 | alias/merge tests |
| Preflight checks | Learning objective | resource/preflight schema/API | 6 | preflight eval cases |
| Grounded Ask | Product core | query API/evidence schemas | 7 | query grounding evals |
| Privacy controls | Safety | privacy settings/export/delete | 3–7 | privacy review checklist |
| Evidence-backed answers | Trust model | evidence_bundle/query_answer | 7 | query grounding evals |
| Design language | UX objective | design handoff/tokens | 8 | design QA rubric |
| Optional pgvector | Retrieval | retrieval migration/queries | 7–9 | retrieval evals |
| Optional ParadeDB | Search profile | optional migration/query notes | 9 | extension matrix |
| Optional TimescaleDB | Analytics profile | optional migration/query notes | 9 | extension matrix |
| Backup/restore | Operations | infra docs/runbooks | 0–alpha | restore drill |
| Accessibility | Nonfunctional | design/NFR/test checklist | 8 | accessibility checklist |


| Requirement | Source | Implementation artifacts | Tests/evals | Phase |
|---|---|---|---|---|
| Context snapshots around timing events | US-016 | `capture_context_snapshot`, OpenAPI capture-context endpoint | idempotent snapshot replay | 3 |
| Context capture policy | US-016/US-021 | `context_capture_policy`, privacy/context-capture-policy API | server-policy-disables-signal tests | 3 |
| Real-world multi-surface capture | US-015 | capture method enum, UI variants, event contracts | capture workflow scenario matrix | 3/8 |
| Place-aware estimates | US-017/US-020 | `user_place`, `inferred_place_observation`, `temporal_feature_vector` | context prediction evals | 5/7 |
| Forgotten timer detection | US-018 | `timing_review_flag`, timeline recompute | forgotten-timer scenario evals | 3/5 |
| Radio/sensor privacy | US-021 | retention policy, hash storage, redaction | sensor privacy matrix | 3/7 |
| Prompt burden control | US-022 | prompt outcome fields, observability metrics | prompt false-positive evals | 6/9 |
