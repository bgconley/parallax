# 15 — Risk Register and Open Questions

## Risk register

| ID | Risk | Severity | Likelihood | Mitigation | Owner |
|---|---|---:|---:|---|---|
| R-001 | App becomes a generic time tracker | High | Medium | Keep Activity/Run/Context/Review/Ask loop as scope lock | Product/Engineering |
| R-002 | LLM misclassification updates wrong patterns | High | Medium | Schema validation, confidence tiers, review gates, correction | AI/Backend |
| R-003 | Raw context privacy leak | Critical | Medium | No raw logs, retention controls, encryption, export/delete | Backend/Ops |
| R-004 | Offline replay double-counts events | Critical | Medium | Mutation envelope, idempotency log, semantic replay tests | Backend |
| R-005 | Activity identity fragments histories | Medium | High | Alias suggestions, merge/split UX, audit trail | Product/UI/Backend |
| R-006 | Early estimates create false precision | High | Medium | sample size, confidence labels, limitations, p50/p80 ranges | Estimator/Product |
| R-007 | Optional DB extensions create operational drag | Medium | Medium | Baseline Postgres first; optional feature flags | Backend/Ops |
| R-008 | Review flow too burdensome | High | Medium | Progressive disclosure, defaults, story-first review | UI/Product |
| R-009 | Ask answers hallucinate facts | High | Medium | deterministic facts, evidence bundles, query grounding evals | AI/Backend |
| R-010 | Design/code state drift | Medium | Medium | UI projections from canonical schemas, contract tests | UI/Backend |

## Open questions that do not block Phase 0–2

1. Which private-alpha auth provider will be used?
2. Which mobile local persistence library will be selected?
3. Which local context extraction model will be first?
4. Which embedding model/dimension will be first?
5. Will cloud LLM fallback exist in private alpha or remain developer-only?
6. What exact backup tool will be used: pgBackRest, WAL-G, or another equivalent?
7. Which hardware target will host local models first?
8. What is the alpha default for raw note retention after extraction?
9. How much Today Lite should be exposed before Activity Profile is mature?
10. What exact thresholds should promote confidence from medium to high?

## Decisions already settled

- Product name is Parallax.
- Backend/domain contracts are canonical.
- `user_id` is canonical.
- Postgres is source truth.
- Timer source actions work offline.
- Review controls model learning.
- Raw context is privacy-sensitive.
- LLMs do not own numeric predictions.
- Ask answers require evidence.
- Optional ParadeDB/Timescale profiles are not P0 dependencies.


## v1.3 added risks

| Risk | Severity | Mitigation |
|---|---|---|
| Context capture feels invasive | High | Permission ladder, transparent copy, per-run disable, privacy-first defaults. |
| Raw radio/location data leaks | High | Salted hashes, encryption, short retention, log scrubbing, redaction tests. |
| Place inference creates sensitive labels | High | User confirmation required for sensitive labels; no global place graph in alpha. |
| Sensor signals overrule user timing | High | Sensors can flag review but cannot silently own durations. |
| Contextual ML overfits low-sample contexts | Medium | Hierarchical fallback, confidence labels, sample thresholds, calibration evals. |
| Battery drain from capture | Medium | Event-boundary snapshots, low-power/last-known first, no continuous tracking by default. |
| Platform permission churn | Medium | Feature flags, platform-specific permission abstraction, current-docs review during implementation. |
| Optional extensions complicate ops | Medium | Baseline Postgres remains sufficient; optional PostGIS/Timescale profiles gated and tested. |

## v1.3 open questions

- Which mobile platform is implemented first: iOS, Android, or cross-platform?
- What is the first non-primary capture surface: lock-screen widget, watch, shortcut, or voice?
- Should alpha enable approximate place by default after explanation, or require explicit settings activation?
- What is the initial raw location retention duration: never, 24 hours, 7 days, or user-selected?
- Which context-conditioned estimate appears first in Activity Profile: work mode, place category, or checkpoint?
