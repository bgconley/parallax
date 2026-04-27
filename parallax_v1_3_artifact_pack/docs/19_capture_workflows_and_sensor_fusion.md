# 19 — Capture Workflows, Real-World Scenarios, and Sensor Fusion

This document turns timing capture into an implementable workflow model. It is intended for product, UI, mobile, backend, and agentic coding work.

## Capture principles

1. Timing source actions must be available even with no network, no AI, and no sensor permissions.
2. Every capture path must create append-safe source events.
3. Ambient context is auxiliary evidence, not truth.
4. The user must be able to see, correct, and disable inferred context.
5. Capture must be fast enough for hands-busy, messy, interrupted real life.
6. Privacy must be understandable at the moment of permission and review.

## Canonical capture methods

| Method | Example | Data created | UX requirement |
|---|---|---|---|
| `manual_timer_button` | User taps Start/Done | timing event + context snapshot | fastest path; no sensor requirement |
| `quick_chip` | "Waiting", "Interruption", "Detour" | annotation or span candidate + snapshot | one-tap, undoable |
| `voice` | "Had to go upstairs for the sponge" | annotation + optional transcript + snapshot | save audio/text before interpretation |
| `lock_screen_widget` | Start/finish from lock screen | timing event + minimal snapshot | no deep navigation |
| `watch` | Capture from Apple Watch/Wear OS | timing event/annotation + device metadata | resilient to phone not open |
| `shortcut` | Siri/Shortcuts/Android shortcut | timing event/annotation | must preserve idempotency |
| `nfc_tag` | Tap near garage/kitchen bench | timing event + place hint | user-configured only |
| `calendar_import` | Planned start/activity from calendar | intent/session draft | opt-in, never train without review |
| `review_reconstruction` | User fixes after the fact | correction + spans | review-first, explicit uncertainty |
| `background_signal` | place transition or geofence | context snapshot only unless user opted into prompt | no silent task timing |

## Capture workflow states

A timing capture can pass through these conceptual states:

1. `observed`: client saw a user action or eligible system signal.
2. `persisted_locally`: client wrote durable local event/snapshot.
3. `queued_for_sync`: event is ready for idempotent replay.
4. `accepted_by_api`: server accepted mutation.
5. `reconciled`: timeline reconstruction has consumed it.
6. `interpreted`: extraction or place inference ran, if applicable.
7. `needs_review`: confidence or privacy requires user confirmation.
8. `reviewed`: user confirmed/corrected/ignored.
9. `learned`: model inclusion rules allowed analytics update.

The UI should surface only the state that affects the user: saved, syncing, needs review, corrected, or ignored.

## Real-world scenario matrix

### Hands are wet, dirty, or full

Examples: dishes, garage work, cooking, laundry.

Required behavior:

- lock-screen/watch/widget capture;
- large one-tap quick chips;
- voice capture that saves immediately;
- no dependency on AI interpretation before save;
- clear undo.

Useful context:

- place hint;
- motion state;
- connected Wi-Fi or coarse radio fingerprint;
- last-known location;
- time since prior step.

### User is moving between places

Examples: errands, car-to-house transition, commute, dog walk.

Required behavior:

- start and completion should store location accuracy and motion state when allowed;
- transition latency separated from activity duration;
- place change during an active timer should flag review only when it materially affects timing;
- no continuous tracking unless the user explicitly enabled an activity that needs it.

Useful context:

- fused location / GPS;
- geofence or visit event;
- motion state;
- distance from prior place;
- coarse route class, not raw route history by default.

### User forgets to stop the timer

Required behavior:

- detect suspicious duration, place transition, long idle period, lock/background state, or impossible sequence;
- ask in review: "Looks like the timer may have kept running. Where should it have ended?";
- support trimming the session and marking bad-timer spans;
- prevent silent baseline pollution.

Useful context:

- last active event;
- app/device state;
- significant location change;
- motion state;
- radio cluster change;
- screen/foreground status where available and allowed.

### User starts late or avoids starting

Required behavior:

- intended start can be captured without forcing a timer;
- actual start separated as start latency;
- nudges are optional and fatigue-aware;
- ask questions like "Which tasks are quick once I start?"

Useful context:

- time of day;
- place;
- previous activity;
- deadline proximity;
- interruption count;
- user energy window if configured.

### User does nested work or side quests

Required behavior:

- user can quickly mark side quest/interruption;
- side quest defaults to wall-only for original activity;
- nested sessions can be linked but not conflated;
- review can split spans.

Useful context:

- quick chip timestamp;
- annotation;
- place stability or transition;
- device/app state.

### User is in a privacy-sensitive place

Examples: medical appointment, school, client site, religious venue, private home.

Required behavior:

- location context can be disabled per run/place;
- private place labels are user-defined;
- raw location/radio data should have short retention or derived-only storage by default;
- Ask About Time must respect raw quote and location visibility settings.

Useful context:

- privacy class;
- coarse place category if user confirmed;
- no raw coordinates unless explicitly allowed.

### User has no permissions enabled

Required behavior:

- timing still works;
- no broken UI states;
- estimates fall back to activity-only stats;
- capture context records permission unavailable status;
- app explains optional benefits without nagging.

Useful context:

- manual work mode;
- user-selected place;
- time of day;
- annotation text.

## Sensor fusion model

### Capture snapshot timing

Capture a context snapshot at these points:

- session created;
- session started;
- session paused/resumed;
- session completed;
- checkpoint started/completed;
- annotation captured;
- quick chip captured;
- review correction saved;
- optional geofence/visit/radio signal if the user enabled prompts.

### Snapshot composition

A snapshot should contain:

- local timestamp;
- monotonic timestamp when available;
- capture method;
- trigger;
- client device ID;
- permission states;
- foreground/background/locked state;
- low-cost last-known location when available;
- precise location only when useful and permitted;
- radio fingerprints only under explicit policy;
- motion state if permitted;
- inferred place candidate;
- privacy/retention policy.

### Fusion rules

1. Trust user source events over sensors.
2. Prefer lower-power context first.
3. Store provenance and accuracy for every observation.
4. Do not mix observations with different timestamps without recording the offset.
5. A place inference requires evidence and confidence.
6. A location transition can flag review, but cannot end a timer by itself unless the user opted into an automation.
7. Sensor observations older than the configured freshness window must be marked stale.
8. Approximate/coarse data is acceptable for context; precise coordinates should be exceptional.

## UI/UX implications

Add these UI states and screens:

- capture method selector in settings;
- context privacy settings;
- "saved with limited context" state;
- "needs review because context changed" banner;
- place confirmation chip: "Was this at Kitchen / Garage / Other?";
- unobtrusive permission explainer;
- location/radio retention settings;
- per-run "ignore context for this run";
- review card showing why the app thinks a run was unusual.

Never show raw sensor jargon to the user unless in advanced settings. Say "place changed", not "radio fingerprint cluster changed".

## Backend implications

The backend must support:

- `context_capture_policy` as the server-authoritative capture/retention control;
- `capture_context_snapshot` persistence;
- geospatial observation persistence;
- radio observation persistence;
- inferred place observation persistence;
- user place confirmation/correction;
- context feature vector generation;
- privacy-aware redaction/deletion;
- idempotent capture replay;
- persisted `timing_review_flag` prompts when context affects review;
- timeline recompute triggers when user corrections affect derived projections.

## Non-goals for alpha

Do not build a full passive lifelogger. Do not track raw routes by default. Do not infer sensitive place labels automatically. Do not train on passive observations without user-reviewed timing sessions.
