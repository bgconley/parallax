# 01 — Complete App and System Specification

## Product identity

**Parallax** is a temporal-first personal intelligence app. It helps a person observe how long real activities take under real conditions, understand the difference between active work and friction, and build trustworthy personal timing ranges over time.

The core sentence is:

**Time what you do. Say what happened. Learn what really takes the time.**

Parallax is deliberately not a timesheet, not a productivity scoreboard, not a general daily planner, and not a chatbot-first executive-function app. The application is anchored on the temporal loop: choose an activity, time it, capture context when reality changes, review what counted, decide what the system should learn, and later ask grounded questions about the observed history.

## Primary user problems

Users often misestimate time because ordinary activities contain hidden temporal structure:

- an activity may be quick once started but hard to begin;
- active work may be stable while wall time varies widely;
- missing supplies, waiting, interruptions, and detours may dominate elapsed time;
- repeated activities may fragment under slightly different names;
- reviews and estimates can feel judgmental if the app treats every delay as failure;
- AI summaries are not trustworthy unless tied to evidence and correction.

Parallax solves these problems by modeling activities as repeated observations rather than abstract tasks. It separates active duration, wall duration, friction, start latency, transition latency, checkpoints, context annotations, extracted events, review decisions, and evidence.

## Primary product loop

The flagship v1 loop is:

```text
Choose or create activity
  -> choose measurement mode
  -> optionally record intended start or checkpoints
  -> start timing
  -> capture "say what happened" notes during changes
  -> finish the run
  -> review active/wall/friction/start-latency treatment
  -> decide what the app should learn
  -> see Activity Profile update
  -> ask grounded questions about timing history
```

The loop must work offline through finish and review draft. AI enrichment and query narration can wait for connectivity.

## Core user-facing surfaces

### Temporal Home

A calm entry surface that shows recently timed activities, currently running or unresolved runs, and a small number of next useful actions. It is not a dense dashboard.

### Activity Library

A searchable list of activities with alias handling and merge/split affordances. The library helps avoid fragmented histories.

### Activity Profile

The primary learning surface. It shows personal active and wall ranges, sample size, confidence, common friction, start latency, checkpoint patterns, preflight checks, recent reviewed runs, and evidence links.

### Timing Launcher

The start surface for an activity. It lets the user choose a measurement mode, see recent range context, optionally set intended start, optionally configure checkpoints, and begin.

### Checkpoint Setup

A lightweight optional setup flow for activities with repeated phases. Checkpoints are editable and skippable.

### Timing Session

The flagship operational surface. It shows elapsed wall time, active time, current checkpoint, running state, pause/resume, finish, and a prominent "Say what happened" action. It must support running, paused, waiting, detour, interruption, side quest, abandoned/resumed, and forgot-to-stop correction states.

### Context Capture Sheet

A low-friction voice/text/chip sheet that preserves raw context immediately. Interpretation is asynchronous. The sheet must show when interpretation is pending, uncertain, or needs confirmation.

### Run Timeline and Event Correction

A reviewable timeline of source events and derived spans. Users can edit, split, merge, reclassify, ignore, or confirm system interpretations. Corrections are persisted and auditable.

### Timing Review

The learning gate. It summarizes elapsed wall time, active work, friction, start latency, checkpoints, and anomalies. The user chooses what the run teaches: useful normal run, unusual but useful, partial, active-only, friction-only, evidence-only, discard timing but keep note, or discard all.

### Ask About Time

A grounded natural-language query layer. It answers questions using deterministic facts plus selected evidence. Answers must include sample size, time window, confidence, limitations, and evidence cards.

### Privacy and Raw Context Settings

Controls for raw-note retention, transcript/audio retention, embedding of sensitive notes, raw quotes in answers, cloud model fallback, export, redaction, and delete.

## Core domain objects

- User
- User device
- Activity
- Activity alias
- Activity relationship
- Timing session
- Timing event
- Timing event span
- Checkpoint template
- Checkpoint run
- Context annotation
- Extracted context event
- Resource dependency
- Preflight check
- Start latency observation
- Transition observation
- Model update decision
- Activity stats snapshot
- Temporal prediction
- Prediction outcome
- Evidence bundle
- Evidence item
- Temporal query answer
- Retrieval document
- Embedding
- Model invocation
- Workflow run
- Client mutation log
- Audit log

## Measurement modes

- `estimate_only`: estimate without running a timer.
- `whole_task`: time one whole activity.
- `checkpointed`: time named phases/checkpoints.
- `routine`: time a repeatable flow using previous defaults.
- `calibration`: guess first and compare after.
- `passive`: capture completion/outcome with minimal timing instrumentation.

The default v1 mode is `whole_task`. The app should not force users into checkpoint setup.

## Temporal measurements

### Wall time

Clock time from session start to finish. Wall time includes active work, pauses, waiting, interruptions, detours, setup expansion, and side quests until the user edits boundaries.

### Active time

Time actively spent doing the intended activity or checkpoint. Active time generally excludes waiting, interruptions, unrelated side quests, and resource detours unless the user marks them as intrinsic.

### Friction time

Time that explains why wall time exceeded active work or why the activity changed shape. Friction includes resource detours, waiting, interruptions, setup expansion, decision loops, attention drift, body/energy events, environmental friction, and scope changes.

### Start latency

Time between intended start and actual start. It is not active work and should not pollute the activity duration baseline.

### Transition latency

Time between finishing one activity/phase and starting the next. It can be modeled separately from both source and target activity duration.

## Trust model

Parallax becomes trustworthy by showing how it knows what it knows. Every derived insight must be traceable to reviewed sessions, annotations, extracted events, stats snapshots, and evidence bundles. The app must preserve correction paths. It should display uncertainty honestly instead of creating false precision.

## Data truth hierarchy

1. User-authored source data: timing events, annotations, explicit review decisions, corrections.
2. System-generated source metadata: server receipt time, workflow status, model invocation audit.
3. Derived structured events: extracted context events and spans.
4. Derived summaries: stats snapshots, predictions, preflight suggestions.
5. Narrated answers: LLM-generated text grounded in computed facts and evidence.

Only the first two categories are source truth. Categories 3–5 are correctable projections.

## MVP boundary

The v1 MVP must include the temporal loop. It does not need broad planning, calendar import, caregiver collaboration, community benchmarks, advanced scheduling, or automated life coaching. Today Lite can exist as an entry surface but must remain secondary to Activity, Run, Context, Review, and Ask.

## Success criteria

Parallax is directionally successful when a user can truthfully say:

- "I know how long this usually takes me."
- "I can see why this run was different."
- "The app separates doing the task from getting ready, waiting, and getting derailed."
- "I can correct it when it gets something wrong."
- "Its answers show evidence instead of guessing."
- "It does not make me feel judged."


## v1.3 timing/context intelligence expansion

Parallax should be implemented as a temporal-first app with ambient context awareness, not as passive surveillance. The timing loop remains primary: time what the user does, capture what happened, review what counted, and learn from reviewed evidence.

v1.3 expands the system objective in four ways:

1. Capture context at the moment of timing actions.
2. Infer user-scoped place and environment only when permitted.
3. Use context to explain variance and reduce review burden.
4. Use context-aware analytics to predict more honestly without silently training on ambiguous data.

### Context objective

For a timing session, Parallax should be able to answer:

- Did this happen in the usual place or a different place?
- Was the user stationary, moving, or transitioning?
- Did the run cross a place boundary that may indicate a forgotten timer?
- Is this activity usually faster at one place/work mode than another?
- Is start latency place/time/context dependent?
- Are repeated detours location-specific?
- Was the capture low-confidence because sensors were unavailable or stale?

### Non-objective

Parallax is not a passive lifelogger. It should not collect continuous raw routes, raw radio environments, foreground app histories, or sensitive place labels by default. The implementation must support meaningful value with all sensor permissions denied.
