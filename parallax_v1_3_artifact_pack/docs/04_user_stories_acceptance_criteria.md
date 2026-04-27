# 04 — User Stories and Acceptance Criteria

## US-001 — Create or choose an activity

As a user, I want to create or choose an activity without worrying about perfect naming, so that I can start observing time quickly.

Acceptance criteria:

- User can create an activity with a display name.
- User can search existing activities.
- Similar names produce suggestions, not silent merges.
- Activity creation works offline if the client has local persistence.
- API returns canonical `activity_id`.

Mapped phases: 1, 6.

## US-002 — Time a whole-task run

As a user, I want to time an activity from start to finish, so that I can learn how long it actually takes.

Acceptance criteria:

- User can start, pause, resume, and complete a run.
- Wall time and active time are visible or derivable.
- Source events are append-safe and idempotent.
- Timer survives app relaunch and network loss.
- Completing a run leads to review.

Mapped phases: 1, 2, 8.

## US-003 — Capture what happened during a run

As a user, I want to quickly say what changed, so that the app understands why a run took longer or felt different.

Acceptance criteria:

- User can capture text annotation during a run.
- Voice and quick-chip modes are represented in the contract.
- Raw annotation saves immediately.
- Annotation links to timer position and checkpoint when available.
- Interpretation can be pending without blocking timing.

Mapped phases: 3, 4.

## US-004 — Review what counted

As a user, I want to decide what counted as active work and what should be learned, so that the app does not train on misleading data.

Acceptance criteria:

- Review summarizes wall time, active time, friction, start latency, and checkpoint totals.
- User can mark run as useful, unusual, partial, active-only, friction-only, evidence-only, or discarded.
- Review persists a `model_update_decision`.
- Stats update only according to review decision.
- User can correct spans and extracted events.

Mapped phases: 2, 4.

## US-005 — Distinguish active work from friction

As a user, I want detours, waiting, interruptions, and side quests to be separated from active work, so that estimates are honest.

Acceptance criteria:

- Resource detour defaults to wall-only.
- Interruption defaults to wall-only.
- Waiting is review-dependent when parallel work is possible.
- Side quest does not update the original activity baseline by default.
- All defaults are user-correctable.

Mapped phases: 2, 4.

## US-006 — Track checkpoints

As a user, I want to optionally break a recurring activity into phases, so that I can see where time expands.

Acceptance criteria:

- User can define checkpoints before a run.
- User can skip setup.
- Checkpoint runs record start/completion.
- Checkpoint stats appear in Activity Profile once sufficient data exists.
- Checkpoint edits do not corrupt prior reviewed runs.

Mapped phase: 5.

## US-007 — Track start latency

As a user, I want the app to separate trouble starting from time spent doing the task, so that I can plan more realistically.

Acceptance criteria:

- User can record intended start.
- Actual start can be compared to intended start.
- Start latency appears separately from active duration.
- App avoids nagging if user does not want start intent capture.
- Ask About Time can answer questions about quick-once-started activities.

Mapped phase: 5.

## US-008 — Learn preflight checks

As a user, I want repeated detours to become useful checks, so that I can reduce avoidable friction.

Acceptance criteria:

- Repeated resource detours aggregate into resource dependencies.
- Suggested checks include evidence and can be accepted/hidden/snoozed.
- Preflight checks appear only when relevant.
- Checks never imply blame.

Mapped phase: 6.

## US-009 — Ask grounded questions about time

As a user, I want to ask plain-language questions about my timing history, so that I can understand patterns.

Acceptance criteria:

- Answer includes sample size, time window, confidence, computed facts, evidence cards, and limitations.
- LLM explanation cannot invent facts.
- User can open evidence and correct source runs/events.
- Privacy settings control raw quote use.
- Low-data answers are cautious.

Mapped phase: 7.

## US-010 — Control raw context privacy

As a privacy-conscious user, I want clear control over raw notes, transcripts, audio, embeddings, and exports.

Acceptance criteria:

- Raw context retention setting exists.
- Audio retention defaults off.
- Cloud LLM fallback defaults off.
- Sensitive raw notes are not embedded unless explicitly allowed.
- Export, redact, and delete workflows exist.
- Normal logs do not contain raw notes or prompts.

Mapped phases: 3, 4, 7.

## US-011 — Operate offline

As a user without reliable connectivity, I want timing and notes to continue working.

Acceptance criteria:

- Start/pause/resume/complete can be queued offline.
- Raw annotations can be queued offline.
- Idempotent replay prevents duplicates.
- Sync status is visible.
- AI enrichment waits until connectivity returns.

Mapped phases: 1, 3, 8.

## US-012 — Correct the system

As a user, I want to fix interpretations, events, and activity identity, so that Parallax becomes more accurate.

Acceptance criteria:

- Extracted event can be confirmed, corrected, ignored, split, or merged.
- Timeline span can be reclassified.
- Activity aliases can be accepted/rejected.
- Correction history is auditable.
- Corrections trigger recomputation.

Mapped phases: 4, 6.

## US-013 — Use a warm, non-judgmental interface

As a user, I want the app to feel calm and supportive, so that observing time does not feel like surveillance.

Acceptance criteria:

- Copy avoids shame, scorekeeping, and productivity theater.
- UI uses warm native surfaces, soft cards, and readable hierarchy.
- One primary action per screen.
- Color is never the only semantic signal.
- Accessibility and Dynamic Type states pass.

Mapped phase: 8.

## US-014 — Hand off design to code

As an implementation team, we want design, schemas, samples, and components to align.

Acceptance criteria:

- Figma frames/components use Parallax naming.
- UI state maps to canonical domain state.
- Sample payloads validate against JSON schemas where applicable.
- Component inventory includes empty, loading, offline, pending, and needs-review states.
- Design handoff includes acceptance gates.

Mapped phase: 8.


## US-015 — Capture from real-world surfaces

As a user with my hands full, I want to start, stop, or annotate a run from the easiest available surface, so that timing works in messy real life.

Acceptance criteria:

- Manual app button capture works.
- Lock-screen/widget capture is represented in contracts.
- Watch capture is represented in contracts.
- Voice and quick-chip capture create durable local events before network or AI processing.
- Each capture records `capture_method` and `capture_trigger`.
- A capture can succeed with no location or radio permissions.

Mapped phases: 1, 3, 8.

## US-016 — Preserve context at timing boundaries

As a user, I want the app to remember useful context around start, pause, resume, checkpoint, annotation, and completion events, so that review and estimates can explain why time varied.

Acceptance criteria:

- A `capture_context_snapshot` can be attached to timing events and annotations.
- Snapshot creation is idempotent and offline-safe.
- Snapshot includes permission state and provenance.
- Missing/stale context is represented explicitly rather than guessed.
- Context does not silently change duration totals.

Mapped phases: 3, 4, 5.

## US-017 — Use place context without feeling invasive

As a privacy-conscious user, I want place-aware estimates only when I permit them, and I want to confirm or correct places.

Acceptance criteria:

- User can disable location context globally and per run.
- User can use approximate/coarse location or manual place selection.
- Inferred place candidates require confirmation before sensitive labels are stored.
- Raw coordinates and radio identifiers follow retention/redaction policy.
- Activity Profile can show place-conditioned ranges only from permitted/reviewed data.

Mapped phases: 3, 5, 7, 8.

## US-018 — Detect likely forgotten timers

As a user, I want the app to notice when a timer probably kept running too long, so that my baselines do not get polluted.

Acceptance criteria:

- Long idle gaps, place transitions, unusual wall/active ratios, and impossible event sequences can flag review.
- The app asks the user where the run should have ended instead of silently trimming.
- Corrections produce audited spans and recomputed stats.
- Sensor evidence is shown in human terms, such as "place changed" or "long inactive gap."

Mapped phases: 2, 4, 5.

## US-019 — Reconstruct after the fact

As a user, I want to fix or reconstruct a run after the fact, so that imperfect capture is still useful.

Acceptance criteria:

- User can add review notes, split spans, mark side quests, and correct end times.
- Corrected spans preserve source history.
- Reconstructed runs have lower confidence until reviewed.
- The model learns only according to the review decision.

Mapped phases: 2, 4, 5.

## US-020 — Learn context-aware estimates

As a user, I want the app to learn that the same task may take different time in different contexts, so that estimates become realistic.

Acceptance criteria:

- Activity Profile can condition summaries by work mode, actor mode, place category, and checkpoint when enough data exists.
- Low-sample contexts borrow from broader activity stats rather than overfitting.
- Predictions include sample size, confidence, and limitations.
- Discarded/unreviewed/private-excluded runs do not train contextual estimates.

Mapped phases: 5, 7, 9.

## US-021 — Control radio and sensor privacy

As a user, I want explicit control over Wi-Fi, BLE, UWB, motion, and location-derived context, so that the app is useful without becoming creepy.

Acceptance criteria:

- Permissions are requested only when an enabled feature needs them.
- Raw radio identifiers are not stored by default.
- Sensor retention policy is visible and enforceable.
- Export/redact/delete covers context snapshots and observations.
- Timing still works if every sensor permission is denied.

Mapped phases: 3, 7, 8.

## US-022 — Evaluate capture burden

As a product owner, I want the app to measure whether prompts and context suggestions are useful, so that the app does not nag or overfit.

Acceptance criteria:

- Prompt outcomes include accepted, corrected, ignored, hidden, snoozed, and retired.
- False-positive place/timer-review prompts are tracked.
- Suggestion precision is a release metric.
- Prompt frequency can be capped by user and feature.

Mapped phases: 6, 7, 9.
