# Phase 6 API Enrichment Research

This note records the Phase 5 seam review, full API-purpose pass, and external
API/UX research used to decide how the canonical v1.3 API should be enriched
before Phase 6 implementation resumes. It does not change the canonical OpenAPI.

## Canonical Phase 6 Scope

Phase 6 depends on Phases 2-5 and has two goals:

- Activity identity: reduce fragmented histories through aliases,
  relationships, merge/split affordances, and audit records.
- Preflight learning: turn repeated resource friction into useful checks that
  can be accepted, hidden, snoozed, or retired.

The current contract already has rows and schemas for aliases, relationships,
resource dependencies, and preflight checks, but the API surface is incomplete
for user decisions and merge/split UX.

## Phase 5 Seams That Matter

Phase 5 is not isolated from Phase 6. It created the timing features that Phase
6 identity and preflight work must preserve:

- Checkpoint templates and runs feed phase-level duration and can expose where a
  run expanded.
- Start latency and transition latency must remain separate from active
  duration even when activities are merged or related.
- Temporal feature vectors include activity relationship clusters, preflight
  state, resource dependency hits, and repeated friction signals.
- `RecomputeActivityProfileWorkflow` already names alias merge as a trigger and
  aggregates friction/preflight candidates.

Phase 6 should therefore treat identity changes as profile/vector invalidation
events, not simple metadata edits.

## Current API Purpose Map

| API surface | Backend purpose | Frontend/UX purpose |
|---|---|---|
| `GET /v1/health`, `/ready`, `/live`, `/version` | Runtime and deployment health/readiness/version checks. | App startup diagnostics and operator proof. |
| `POST /v1/activities` | Create an activity anchor with mutation replay. | User names a repeated activity without perfect taxonomy. |
| `GET /v1/activities` | Search/list user-scoped activities. | Activity Library search and launcher selection. |
| `POST /v1/activities/resolve` | Read-only name/alias resolver. | Suggest existing activities before creating duplicates. |
| `GET /v1/activities/{activity_id}` | Load one activity. | Activity details and navigation targets. |
| `POST /v1/activities/{activity_id}/aliases` | Persist an alias row. | Confirm that another phrase means this activity. |
| `POST /v1/activities/{activity_id}/relationships` | Persist activity relationship metadata. | Explain part-of, variant, sequence, or related activity links. |
| `GET /v1/activities/{activity_id}/profile` | Load learned stats/profile projection. | Activity Profile: ranges, confidence, friction, checks, evidence. |
| `POST /v1/timing/sessions` | Create a timing run. | Start timing an activity. |
| `GET /v1/timing/sessions/{session_id}` | Reconstruct session projection. | Resume/review a run after app relaunch or sync. |
| `POST /v1/timing/sessions/{session_id}/events` | Append idempotent timing event. | Pause, resume, checkpoint, detour, and correction actions. |
| `POST /v1/timing/sessions/{session_id}/event-spans` | Create/correct derived spans. | Timeline correction and split/reclassify interactions. |
| `POST /v1/timing/sessions/{session_id}/complete` | Close a run and derive completion event. | Finish timing and enter review. |
| `POST /v1/timing/sessions/{session_id}/review` | Save model inclusion decision. | Decide what this run teaches Parallax. |
| `POST /v1/timing/sessions/{session_id}/discard` | Save discard decision. | Drop misleading timing while preserving required audit. |
| `POST /v1/timing/sessions/{session_id}/annotations` | Persist raw context annotation. | "Say what happened" during or after a run. |
| `GET /v1/timing/annotations/{annotation_id}` | Load context annotation. | Show extraction status and evidence. |
| `POST /v1/timing/annotations/{annotation_id}/extract` | Queue/run extraction workflow. | Interpret notes into candidate spans/friction/checks. |
| `POST /v1/timing/extracted-events/{event_id}/confirm` | Confirm or ignore a candidate. | Lightweight correction of AI interpretation. |
| `POST /v1/timing/extracted-events/{event_id}/correct` | Persist corrected candidate and correction history. | Fix misread spans, resources, places, or count policy. |
| `GET /v1/activities/{activity_id}/checkpoints` | Load checkpoint templates. | Configure/reuse repeated phases. |
| `PUT /v1/activities/{activity_id}/checkpoints` | Replace checkpoint template set. | Edit phase checklist for future runs. |
| `GET /v1/activities/{activity_id}/preflight-checks` | List existing preflight checks. | Show checks in Activity Profile and launcher. |
| `POST /v1/activities/{activity_id}/preflight-checks` | Create a check row. | User creates or confirms a manual check. |
| `POST /v1/temporal/predictions` | Create grounded time estimate. | Show "how long will this take?" before starting. |
| `POST /v1/temporal/predictions/{prediction_id}/outcome` | Record prediction result. | Learn calibration after the run. |
| `POST /v1/temporal/query` | Queue grounded time answer. | Ask About Time. |
| `GET /v1/temporal/query/{answer_id}` | Load answer/evidence. | Display answer, confidence, and limitations. |
| `GET/PUT /v1/privacy/settings` | Load/update privacy settings. | User controls raw data, transcripts, embeddings, cloud fallback. |
| `GET/PATCH /v1/privacy/context-capture-policy` | Load/update sensor/context capture policy. | User controls place/radio/motion/device context. |
| `POST /v1/privacy/redact` | Redact scoped sensitive data. | Remove raw/private content. |
| `POST /v1/privacy/export` | Request export workflow. | User data export. |
| `POST /v1/privacy/delete` | Request deletion workflow. | User data deletion. |
| `POST /v1/sync/push` | Apply offline mutation batch. | Mobile sync after offline use. |
| `GET /v1/sync/pull` | Pull changes since cursor. | Keep client state current. |
| `POST /v1/timing/sessions/{session_id}/capture-context` | Store context snapshot. | Attach place/device/radio context to a run. |
| `GET /v1/timing/sessions/{session_id}/capture-context` | List context snapshots. | Review evidence and debug capture. |
| `GET /v1/timing/sessions/{session_id}/review-flags` | List review flags. | Surface possible forgotten timers/anomalies. |
| `PATCH /v1/timing/review-flags/{flag_id}` | Resolve review flag state. | Accept/dismiss anomaly prompts. |
| `POST /v1/places` | Create/confirm place. | User place naming and correction. |
| `GET /v1/places` | List places. | Place settings and profile evidence. |
| `POST /v1/places/resolve` | Read-only place resolver. | Confirm inferred place candidates. |
| `PATCH /v1/places/{place_id}` | Update/confirm place. | Correct name, category, aliases, sensitivity. |
| `POST /v1/analytics/feature-vectors/recompute` | Queue feature-vector recompute. | Rebuild context-conditioned estimates after policy or data changes. |

## External Research Signals

API design:

- Use `PATCH` for ordinary partial resource updates, but not for lifecycle state
  transitions with side effects.
- State fields should be output-only from normal update methods; transitions
  should use explicit custom methods.
- Custom methods are appropriate when the API needs vocabulary matching user
  intent, especially for actions with side effects.
- PATCH operations should be atomic when used.

Reminder/preflight UX:

- Reminder products expose automatic, custom, recurring, and location-triggered
  reminders, plus user-controlled snooze intervals.
- Snoozed reminders must be persisted and rescheduled; losing them undermines
  trust.
- Notifications and prompts need relevance, urgency discipline, in-app controls,
  and per-notification suppression.
- User-group feedback repeatedly asks for fast snooze/reschedule actions,
  clear Done-vs-Snooze semantics, and fewer irrelevant "no action needed"
  prompts.

Merge/split UX:

- High-signal merge workflows use compare, value selection, preview/refine,
  final confirmation, ownership/permission checks, and a visible audit trail.
- Parallax should use a soft/audited merge first: preserve source activity and
  timing history, redirect/cluster for analytics, and recompute profile
  projections. Raw timing events should not be rewritten silently.

## Contract Gaps

The current canonical surface cannot satisfy Phase 6 as written:

1. Preflight checks have states, but no API operation changes a check from
   suggested/active to hidden, snoozed, or retired.
2. Preflight has no `suggested` or `pending` state, so "suggested then accepted"
   is not representable without treating unconfirmed suggestions as active.
3. Snooze has no `snoozed_until`, making the state non-actionable.
4. Resource dependencies exist in SQL but have no user-visible API shape.
5. Alias and relationship creation exist, but there is no list or decision
   surface for suggested aliases/relationships.
6. Merge/split is named in the phase plan and partly supported by activity
   columns, but no API contract defines preview, commit, audit output, or
   rollback/reversal limits.
7. Event contracts include `preflight.check_suggested` but not check decisions,
   resource dependency aggregation, alias rejection, relationship decisions,
   activity merge, or split planning/commit.
8. Offline sync specs only cover existing alias/relationship/preflight create
   operations, not Phase 6 decisions.

## Recommended Canonical API Enrichment

Use explicit domain-action endpoints, following Parallax's existing action
subpath style (`/review`, `/discard`, `/confirm`, `/correct`) rather than
introducing colon-style custom methods only for Phase 6.

### Activity Identity

Add:

- `GET /v1/activities/{activity_id}/aliases`
- `POST /v1/activities/{activity_id}/aliases/{alias_id}/decision`
- `GET /v1/activities/{activity_id}/relationships`
- `POST /v1/activities/{activity_id}/relationships/{relationship_id}/decision`
- `POST /v1/activities/{activity_id}/merge-preview`
- `POST /v1/activities/{activity_id}/merge`
- `POST /v1/activities/{activity_id}/split-preview`

Defer `POST /v1/activities/{activity_id}/split` unless the canonical phase text
is amended to require actual split commit behavior in Phase 6. A split preview
and UX contract are enough for the named Phase 6 deliverable; split commit can
be a later deeper correction phase because it implies session reassignment and
statistics recomputation.

Core schemas:

- `ActivityAliasDecisionRequest`: `mutation`, `decision: accept|reject`,
  `reason`, `evidence`.
- `ActivityRelationshipDecisionRequest`: same decision shape; add relationship
  `state: suggested|confirmed|rejected`.
- `ActivityMergePreviewRequest`: source/target, optional alias/relationship
  handling preferences. Read-only exception must be documented like resolvers.
- `ActivityMergeRequest`: `mutation`, `target_activity_id`, optional
  `preserve_source_activity: true`, `reason`.
- `ActivityIdentityChange`: id, change_type, source/target activity ids,
  affected session counts, created aliases/relationships, audit id, created_at.

Merge semantics:

- Soft merge by default.
- Keep historical `timing_session.activity_id` values unchanged.
- Set source activity `status='merged'` and `merged_into_activity_id`.
- Create `same_as` or `alias_of` relationship as appropriate.
- Profile and query code should follow the activity relationship cluster.
- Emit audit/outbox events and queue profile/feature-vector recompute.

### Resource Dependencies and Preflight

Add:

- `GET /v1/activities/{activity_id}/resource-dependencies`
- `POST /v1/activities/{activity_id}/preflight-checks/{check_id}/decision`

Amend `PreflightCheck`:

- Add `state: suggested|active|snoozed|hidden|retired`.
- Interpret `active` as accepted/enabled.
- Add `snoozed_until: date-time|null`.
- Add `source_dependency_id: uuid|null`.
- Add compact evidence fields: `evidence_count`, `evidence_summary`,
  `last_decided_at`, and optional `decision_reason`.

Core schemas:

- `ResourceDependency`: existing SQL fields plus evidence count/window and
  `suggest_precheck`.
- `PreflightCheckDecisionRequest`: `mutation`, `decision:
  accept|hide|snooze|retire`, `snoozed_until` required only for snooze,
  optional `reason`.

Preflight semantics:

- Aggregator creates or updates resource dependencies from confirmed/reviewed
  friction evidence.
- Threshold crossing creates a `PreflightCheck` in `suggested` state with
  evidence, not an immediately active check.
- User-created checks are `active`.
- `accept` transitions `suggested|snoozed|hidden` to `active`.
- `hide` suppresses the suggestion without deleting evidence.
- `snooze` suppresses until `snoozed_until`.
- `retire` disables an active check without deleting history.

## Implementation Boundary Recommendation

Before Phase 6 code, split responsibilities instead of growing the existing
metadata module:

- Keep routes thin, but move identity endpoints to
  `routes/activity_identity.py` and preflight endpoints to
  `routes/activity_preflight.py` under the same `/v1/activities` prefix.
- Split `ActivityMetadataService` into focused services:
  `ActivityIdentityService`, `CheckpointService`, and `PreflightLearningService`
  or equivalent cohesive modules.
- Keep persistence in repository classes named by domain, not a larger generic
  activity repository. Avoid adding resource-dependency aggregation to route
  handlers or generic utilities.
- Add sync operation specs for all new mutating decisions so offline clients can
  perform the same user-visible actions.

## Minimum Canonical Correction Set

Before implementation, update the canonical artifact pack and local copies
together:

1. OpenAPI paths and schemas for identity decisions, merge/split preview/merge,
   resource dependency listing, and preflight decisions.
2. JSON Schema for `PreflightCheck`, `ActivityAlias`, `ActivityRelationship`,
   resource dependencies, and new request/response objects.
3. SQL migration for preflight `suggested`, `snoozed_until`,
   `source_dependency_id`, relationship decision state, and identity change
   audit rows if audit metadata is not sufficient.
4. Event contract additions:
   `activity.alias_decided`, `activity.relationship_decided`,
   `activity.merged`, `preflight.check_decided`,
   `resource_dependency.updated`.
5. Workflow contract notes that activity identity changes and preflight
   decisions queue profile/feature-vector recompute where relevant.
6. Sync operation specs for all new mutating operations.
7. Phase 6 smoke covering:
   alias suggestion acceptance/rejection, soft merge audit and preserved
   historical sessions, sponge-detour dependency aggregation, and preflight
   accept/hide/snooze/retire transitions.

## Conclusion

The right minimum API enrichment is not a generic `PATCH` alone. Phase 6 needs
explicit user-decision operations for identity and preflight state transitions,
plus a soft merge contract and resource-dependency read surface. This closes the
acceptance gate without pulling optional later-phase modeling or UI depth
forward.

## Research Sources

Local canonical artifacts:

- `parallax_v1_3_artifact_pack/docs/03_phased_implementation_plan.md`
- `parallax_v1_3_artifact_pack/docs/01_app_system_spec.md`
- `parallax_v1_3_artifact_pack/docs/02_temporal_domain_model.md`
- `parallax_v1_3_artifact_pack/docs/04_user_stories_acceptance_criteria.md`
- `parallax_v1_3_artifact_pack/docs/18_timing_analytics_and_context_intelligence.md`
- `parallax_v1_3_artifact_pack/docs/23_agentic_implementation_guardrails.md`
- `parallax_v1_3_artifact_pack/contracts/openapi/parallax_api_v1_3.yaml`
- `parallax_v1_3_artifact_pack/contracts/events/parallax_event_contracts_v1_3.yaml`
- `parallax_v1_3_artifact_pack/contracts/jobs/parallax_workflows_v1_3.yaml`
- `parallax_v1_3_artifact_pack/database/migrations/0001_extensions_and_enums.sql`
- `parallax_v1_3_artifact_pack/database/migrations/0003_activity_identity.sql`
- `parallax_v1_3_artifact_pack/database/migrations/0005_context_extraction_preflight.sql`

External sources captured with Firecrawl and/or browser:

- Google AIP-134, Standard methods: Update: https://google.aip.dev/134
- Google AIP-136, Custom methods: https://google.aip.dev/136
- Google AIP-216, States: https://google.aip.dev/216
- RFC 5789, PATCH Method for HTTP: https://datatracker.ietf.org/doc/html/rfc5789
- Apple Human Interface Guidelines, Managing notifications:
  https://developer.apple.com/design/human-interface-guidelines/managing-notifications
- Todoist Help, Introduction to reminders:
  https://www.todoist.com/help/articles/introduction-to-reminders-9PezfU
- Doist Engineering, local notification scheduler:
  https://www.doist.dev/implementing-a-local-notification-scheduler-in-todoist-ios/
- Watermark, Resolving Duplicates with Compare and Merge:
  https://support.watermarkinsights.com/hc/en-us/articles/5526225267099-Resolving-Duplicates-with-Compare-and-Merge
- Reddit user-group examples from `r/todoist` and `r/ticktick` on snooze,
  persistent reminders, and notification noise.
