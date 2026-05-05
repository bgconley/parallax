# Phase 9 App Remediation Implementation Spec

## Target Architecture

Replace the single fixture-shaped runtime with a real app store:

- `ParallaxAppStore` or equivalent `@MainActor ObservableObject`
  - owns runtime mode, activity list, selected activity, current timing session,
    pending review session, latest profile, preflight checks, checkpoints, query
    answer, sync queue state, and user-facing errors;
  - composes `ParallaxAPIClient`, local stores, and mutation sequence store;
  - exposes intent methods used by views.
- `ParallaxAPIClient`
  - keeps existing request builders;
  - adds missing canonical request builders and typed helpers for:
    `GET /v1/activities`, `GET /v1/activities/{id}`,
    `GET /v1/activities/{id}/profile`,
    `GET/PUT /v1/activities/{id}/checkpoints`,
    `GET /v1/activities/{id}/preflight-checks`,
    `GET /v1/activities/{id}/resource-dependencies`,
    `GET /v1/timing/sessions/{id}`,
    `GET /v1/temporal/query/{answer_id}`;
  - decodes typed DTOs matching OpenAPI names and enum values.
- Local persistence
  - keeps pending event, pending preflight, pending sync mapping, and mutation
    sequence stores;
  - adds a lightweight app-state/activity cache for selected activity and local
    activities created while offline;
  - separates preview/demo fixture storage from runtime storage.
- View models/views
  - views render projections from real state;
  - demo factory methods move to preview/test-only fixtures;
  - no runtime view owns literal scenario data.

Do not invent backend endpoints. If a screen needs recent session history, use
`ActivityProfile.recent_sessions` where available, local current/review sessions,
or a documented empty state. The current OpenAPI has create/get timing session
endpoints, not a general list-session endpoint.

## Runtime Configuration

Refactor `ParallaxRuntimeConfig`:

- Required for connected mode:
  - `PARALLAX_API_BASE_URL`
  - `PARALLAX_AUTH_MODE`
  - auth material for the selected mode
  - `PARALLAX_DEVICE_ID`
- Optional UAT seed inputs:
  - `PARALLAX_ACTIVITY_ID`
  - `PARALLAX_ACTIVITY_NAME`
  - `PARALLAX_PREFLIGHT_CHECK_TEXT`
- If no seed inputs exist, do not synthesize an activity. Launch empty/create
  state.
- If no API config exists, launch local-first mode with empty/create state and
  clear offline/sync messaging.
- `PARALLAX_DEMO_STATE` and `PARALLAX_DEMO_DRAWER` are preview/UAT-only. They
  must not force runtime demo data.

## Data Model Additions

Add Swift DTOs in `ParallaxCore` aligned to OpenAPI:

- `ActivityDTO`
- `TimingSessionDTO`
- `TimingEventDTO`
- `TimingEventSpanDTO`
- `ActivityProfileDTO`
- `ActivityStatsDTO`
- `PreflightCheckDTO`
- `CheckpointTemplateDTO`
- `ResourceDependencyDTO`
- `TemporalQueryAnswerDTO`
- `TemporalQueryEvidenceDTO`
- `TimingReviewFlagDTO`

Keep canonical enum raw values from `ParallaxDomain.swift`. If a backend field is
unknown or optional, preserve it as optional data rather than mapping to fixture
defaults.

Add app projections in `ParallaxApp`:

- `ActivitySummaryProjection`
- `TimingLauncherProjection`
- `TimingSessionProjectionModel`
- `TimingReviewProjection`
- `TemporalHomeProjection`
- `DrawerProjection`
- `SyncQueueProjection`
- `AskTimeProjection`

Projection structs may produce friendly labels, but they must always derive from
real DTO/local state or explicit empty-state values.

## Implementation Slices

### Slice 0: Failing Contract Tests

Add tests before implementation:

- runtime config without seed activity returns no activity defaults;
- app store starts empty on clean launch;
- creating an arbitrary activity name persists and selects that name;
- starting timing for a dynamic activity queues `session_started`;
- quick capture stores arbitrary typed text;
- Ask About Time connected path builds/sends `TemporalQueryRequest`;
- runtime source string leak guard fails if banned fixture strings appear in
  non-fixture app files;
- visible button action guard fails on empty button closures.

Allowed fixture locations:

- `parallax_v1_3_artifact_pack/examples/**`
- `apps/ios/Tests/**/ExamplePayloadTests.swift`
- explicitly named preview fixture files, for example
  `apps/ios/Sources/ParallaxApp/PreviewFixtures.swift`
- design handoff JSON and historical docs.

### Slice 1: Core API And DTO Layer

Extend `ParallaxAPIClient` with missing read helpers and typed decode helpers.
Keep request-builder tests for canonical paths and mutation envelopes.

Required helpers:

- `listActivitiesRequest(q:limit:)`
- `getActivityRequest(activityId:)`
- `getActivityProfileRequest(activityId:)`
- `listCheckpointsRequest(activityId:)`
- `putCheckpointsRequest(activityId:mutation:checkpoints:)`
- `listPreflightChecksRequest(activityId:)`
- `listResourceDependenciesRequest(activityId:)`
- `getTimingSessionRequest(sessionId:)`
- `getTemporalQueryAnswerRequest(answerId:)`

Existing mutating helpers remain the canonical route for create/start/event,
complete, review, discard, annotations, extracted-event confirm/correct,
preflight, query, and review flags.

### Slice 2: App Store And Launch

Create the app store and route `ParallaxNativeApp` through it:

- clean launch loads config and local cache;
- connected launch fetches activities;
- no activities shows create/select state;
- if UAT seed activity is provided, resolve/create it only through the canonical
  activity API or local cache, never by static defaults;
- selected activity is persisted;
- app root navigation is data-driven:
  - no activity: Activity create/select;
  - draft/ready: Temporal Home;
  - running/paused: Timing Session;
  - completed unreviewed: Timing Review;
  - reviewed/discarded: Temporal Home with latest run summary.

### Slice 3: Activity Create/Select

Build a real Activity Library/Create flow:

- text input for activity name;
- optional measurement mode selection;
- create button calls/queues `POST /v1/activities`;
- list supports backend `GET /v1/activities` and local cached activities;
- selecting an activity loads profile, checkpoints, preflight checks, and
  resource dependencies when connected.

No example rows are allowed in the runtime list.

### Slice 4: Timing Launcher And Session

Launcher:

- displays selected activity name;
- displays profile stats if present;
- displays "no reviewed runs yet" when sample size is zero or profile missing;
- measurement mode is selectable;
- Start timing creates a local session and, in connected mode, creates/ensures a
  remote session through `/v1/timing/sessions`;
- no static range, sample count, or checkpoint labels.

Session:

- timer values derive from start/pause/resume timestamps;
- `Pause` appends `session_paused`;
- `Resume` appends `session_resumed`;
- `Finish` calls/queues `completeTimingSession`;
- `Interruption`, `Waiting`, `Resource detour`, `Side quest`, and `Note` use
  user-entered text or chosen span type, never fixed "sponge" data;
- checkpoint rows come from real checkpoint templates or an empty state.

### Slice 5: Dynamic Drawers

Replace fixed drawer copy with `DrawerProjection` data:

- step detail drawer uses selected/current checkpoint;
- friction evidence drawer uses selected annotation/extracted event or asks for
  user text if no extracted event exists;
- forgotten timer drawer appears only from a real review flag or user-initiated
  timer correction;
- review decision drawer maps directly to `ModelUpdateDecision`;
- preflight drawer uses real `PreflightCheckDTO` IDs;
- checkpoint setup drawer edits real checkpoint templates.

Nested drawer actions:

- complete/pause/skip/move/note: mutate current run/checkpoint state and queue
  canonical timing events;
- confirm/correct/ignore extracted evidence: call extracted-event APIs when a
  backend event ID exists, otherwise queue equivalent user-correction evidence;
- preflight accept/snooze/hide/retire: require a real check ID;
- view runs: opens profile/evidence filtered to the selected check;
- save/discard review decisions: call review/discard APIs.

### Slice 6: Review

Review screen derives all metrics from the current local/remote session:

- activity name;
- elapsed wall seconds;
- active seconds;
- detour/waiting/interruption seconds when known;
- profile estimate comparison when profile stats exist;
- "outside usual range" only when computed from profile stats;
- review flags loaded from `/v1/timing/sessions/{session_id}/review-flags`.

Buttons must be functional:

- Save to model: review decision drawer or direct `.saveUsefulRun`;
- Mark unusual: `.markUnusual`;
- Discard: `.discardTimingKeepNote` or `.discardAll` with explicit UI copy.

### Slice 7: Profile, Ask, Privacy, Sync

Activity Profile:

- loads `GET /v1/activities/{id}/profile`;
- shows no-data, low-confidence, and sampled states;
- shows preflight checks and recent sessions only from API/local data.

Ask About Time:

- text input for arbitrary question;
- optional selected activity context;
- connected path calls `POST /v1/temporal/query`;
- displays `TemporalQueryAnswer` status, answer, confidence, sample size,
  evidence summaries, and limitations;
- raw quotes remain off by default.

Privacy:

- use the context-capture policy endpoints where available;
- otherwise show current local policy and backend-unavailable state;
- no static "keep raw notes" claim unless backed by policy.

Sync:

- shows actual pending event/preflight counts and recent failures;
- retry calls pending sync;
- stale idempotency conflicts produce actionable error state and never delete
  unrelated queued data.

### Slice 8: Fixture Isolation And Source Cleanup

Move all example scenario data into preview/test-only helpers. The runtime source
guard must reject banned strings in:

- `apps/ios/App/**`
- `apps/ios/Sources/ParallaxApp/**`
- `apps/ios/Sources/ParallaxCore/**`

unless the file is an explicitly named preview fixture. Tests may still use
artifact-pack example payloads to validate mapping, but runtime tests should use
arbitrary names such as generated `UAT Activity <uuid>`.

### Slice 9: Backend/GPU UAT

Run UAT against the GPU node as the deployment-like backend:

- create a unique activity name;
- create timing session;
- pause/resume;
- capture a unique note;
- record a dynamic detour;
- finish;
- review save;
- ask a time question;
- inspect backend database/API state for the exact dynamic activity and note;
- assert banned fixture strings were not created.

Mac-only Swift tests are necessary but not sufficient for phase completion.
