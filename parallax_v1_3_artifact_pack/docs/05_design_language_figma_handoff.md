# 05 — Design Language and Figma Handoff Specification

This document tells a Figma-capable agent or designer how to execute the Parallax design task from the existing mockup direction without requiring this text generator to modify the Figma file directly.

## Design objective

Parallax should feel warm, native, adult, calm, and correctable. It should feel like the user and the app are observing reality together, not like the app is grading productivity.

The UI should support focused timing and reflective learning. It should never drift into a dense analytics dashboard, timesheet, generic planner, or chatbot shell.

## Reference mockups

The original mockup references are included under:

```text
examples/reference_mockups/
```

Use them as directional references, not exact UI contracts. Promote the timing, review, and breakdown patterns. De-emphasize broad daily planning.

## Visual language

Use:

- warm off-white canvas;
- soft elevated cards;
- native iOS proportions;
- SF/system typography;
- continuous radii;
- subtle separators;
- generous breathing room;
- semantic chips with icons/text;
- restrained color;
- visible evidence and correction affordances.

Avoid:

- dense tables on primary mobile screens;
- cold metric dashboards;
- gamified productivity scoring;
- AI mascots;
- generic chat-first framing;
- color-only state communication;
- hidden correction paths.

## Design tokens

Use `contracts/design/design_tokens.json` as the canonical design-token source. It defines color, type, spacing, radii, shadow, motion, haptics, and accessibility constraints.

Critical semantic colors:

- active work: primary blue role;
- wall/elapsed: blue soft role;
- checkpoints: lilac role;
- resource/setup detour: sage role;
- interruption/start latency: amber role;
- waiting/privacy: teal role;
- sensitive/private: privacy role plus icon/text redundancy.

Do not rely on color alone. Every semantic chip must include text and/or icon.

## Typography

Use the iOS system font. Suggested hierarchy:

- Large title for screen identity.
- Title 2/3 for cards and primary modules.
- Body for explanations and key content.
- Footnote/caption for evidence, limitations, metadata, and sync state.

Numeric timing values should be legible and calm. Do not make timer numbers look like a workout app unless the current screen is actively timing.

## Component system

Required components:

- `ActivityRow`
- `ActivityProfileHero`
- `PersonalRangeChip`
- `TimingLauncherCard`
- `TimingInstrument`
- `CurrentCheckpointCard`
- `SayWhatHappenedButton`
- `ContextCaptureSheet`
- `ContextInterpretationCard`
- `RunTimeline`
- `RunTimelineItem`
- `ReviewSummaryCard`
- `CountTreatmentCard`
- `InclusionDecisionControl`
- `EvidenceBackedAnswerCard`
- `QueryEvidenceCard`
- `PreflightCheckCard`
- `StartLatencyCard`
- `WorkModeSelector`
- `PrivacySettingCard`
- `SyncStatusPill`
- `CorrectionActionSheet`

Each component must have default, loading/pending, empty, offline/cached, high-contrast, and Dynamic Type stress variants if the state is relevant.

## Required screen set

Create these as a connected prototype:

1. Temporal Home
2. Activity Library
3. Activity Profile
4. Activity Identity / Merge Sheet
5. Timing Launcher
6. Checkpoint Setup
7. Timing Session
8. Context Capture Sheet
9. Start Latency / Transition Capture
10. Run Timeline / Run Detail
11. Timing Review
12. Ask About Time
13. Query Evidence Detail
14. Weekly Calibration
15. Today Lite
16. Privacy / Raw Context Settings
17. Work Mode Settings
18. Offline / Sync / Degraded States

## Screen-level requirements

### Temporal Home

Purpose: entry point, unresolved runs, recent activities, and next useful action.

Above the fold:

- current running session if one exists;
- recently used activities;
- one calm prompt such as "What are you timing?";
- sync/status pill only when relevant.

Do not make Home the primary planning dashboard.

### Activity Profile

Purpose: the primary learning surface.

Show:

- activity name and aliases;
- personal active and wall ranges;
- sample size and confidence;
- "quick once started" signal when start latency is high but active duration is stable;
- common friction cards;
- preflight checks;
- checkpoints;
- recent reviewed runs;
- Ask shortcut scoped to activity.

### Timing Launcher

Purpose: start timing with minimal friction.

Show:

- selected activity;
- recent personal range if available;
- up to three default measurement modes;
- optional "I mean to start this now/later";
- optional checkpoint setup;
- primary CTA: Start timing.

### Timing Session

Purpose: flagship runtime surface.

Show:

- elapsed wall time;
- active time;
- current checkpoint or whole-task label;
- pause/resume;
- finish;
- prominent "Say what happened";
- current open friction state if waiting/detour/interruption/side quest is active;
- offline status when relevant.

The user should not need to classify every interruption manually. Natural language capture is preferred.

### Context Capture Sheet

Purpose: capture reality without breaking flow.

Show:

- text input;
- voice input state if implemented;
- quick chips for common states;
- privacy class selector only when needed;
- saved/pending/interpreting state;
- interpretation card when available;
- confirm/edit/ignore actions for uncertain events.

### Timing Review

Purpose: user-controlled learning gate.

Show in this order:

1. What happened summary.
2. Active/wall/friction/start-latency totals.
3. Timeline highlights.
4. Count-treatment controls for ambiguous spans.
5. Inclusion decision.
6. "What Parallax will learn" preview.
7. Save review CTA.

The review should feel like a short story, not a form.

### Ask About Time

Purpose: grounded query, not open chat.

Show:

- question input;
- recent scoped suggestions;
- answer card with sample size, window, confidence, facts, evidence, limitations;
- evidence cards;
- correction/action affordance.

Never show an answer without evidence state, even when evidence is thin.

### Privacy Settings

Purpose: clear control over sensitive data.

Show settings for:

- raw context retention;
- audio retention;
- transcript retention;
- cloud model fallback;
- embedding sensitive notes;
- raw quotes in answers;
- export;
- redact;
- delete.

Each setting must explain consequences in plain language.

## State requirements

Every primary screen must include:

- default;
- empty/sparse data;
- offline/cached;
- sync pending;
- AI pending/interpreting when relevant;
- needs review;
- high contrast;
- Dynamic Type stress;
- reduced motion notes.

Timing and context screens additionally require:

- running;
- paused;
- waiting active;
- interruption active;
- detour active;
- side quest active;
- abandoned/resumed;
- forgot-to-stop correction;
- unresolved interpretation.

## Figma naming

Use this naming convention:

```text
Parallax / <Surface> / <State> / <Breakpoint or Device>
```

Examples:

- `Parallax / Timing Session / Running / iPhone`
- `Parallax / Timing Review / Needs Event Confirmation / iPhone`
- `Parallax / Activity Profile / Sparse Data / iPhone`
- `Parallax / Ask About Time / Low Confidence Answer / iPhone`

Component names should use:

```text
Parallax/<ComponentName>/<Variant>
```

## UX acceptance gates

A design pass is acceptable only if:

- the flagship loop is understandable without narration;
- timing session is visually promoted as a primary surface;
- review clearly controls model learning;
- active/wall/friction distinctions are visible;
- evidence appears behind answers;
- raw-context privacy controls are discoverable;
- correction affordances are visible;
- offline and pending states are designed;
- Dynamic Type and high contrast variants exist;
- no retired product naming appears.


## v1.3 capture/context design additions

The Figma-capable agent should add design coverage for context-aware capture without making the app feel like a tracker.

### Required new frames or variants

- Timing session with "saved with limited context" status.
- Timing session with "place changed — review suggested" banner.
- Quick capture chip row: Detour, Waiting, Interrupted, Side quest, Forgot timer.
- Voice capture while timer is running.
- Lock-screen/widget capture concept frame.
- Watch capture concept frame.
- Context privacy settings.
- Place confirmation bottom sheet.
- Per-run "ignore context for this run" control.
- Review card explaining why a run is unusual.

### Copy guidance

Use human terms:

- "place context";
- "approximate place";
- "saved without location";
- "looks like the place changed";
- "confirm where this happened";
- "forget this context".

Avoid technical terms in normal UI:

- GPS;
- BSSID;
- BLE scan;
- radio fingerprint;
- sensor fusion;
- precise geolocation.

### Visual language

Context should appear as supportive evidence, not surveillance. Use low-emphasis evidence chips, explainable review cards, and clear controls. Do not put map-first UI at the center of Parallax. The timer, activity, and review decision remain primary.

### Acceptance gate for Figma handoff

The design handoff must show how a user can:

1. Start a run with no permissions.
2. Start a run with approximate place context.
3. Capture a voice detour with hands busy.
4. Review a possible forgotten timer.
5. Confirm or ignore an inferred place.
6. Disable context capture for a run.
