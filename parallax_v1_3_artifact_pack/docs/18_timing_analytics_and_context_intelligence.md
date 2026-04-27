# 18 — Timing Analytics and Context Intelligence

This document closes a v1.3 gap: Parallax must understand not only *how long* an activity took, but also the temporal, spatial, environmental, and behavioral context that made the run normal, unusually easy, unusually hard, or misleading.

The goal is not surveillance. The goal is user-controlled temporal awareness. The system should collect the minimum context needed to explain time honestly, expose what it inferred, and let the user correct or disable it.

## What v1.2 had

The v1.2 pack correctly separated:

- source timing events;
- derived spans;
- wall time;
- active time;
- start latency;
- transition latency;
- friction categories;
- model inclusion decisions;
- evidence-backed answers.

That is enough for a reliable timing app, but not enough for a deeply useful personal timing intelligence system.

## What v1.3 adds

v1.3 adds a context-intelligence layer around timing. The key addition is the `capture_context_snapshot`: a point-in-time observation bundle captured near a timing event, annotation, checkpoint transition, run start, run completion, or user correction.

A context snapshot can include:

- capture method and trigger;
- permission state;
- app foreground/background/locked state;
- coarse or precise geospatial observation;
- inferred place;
- radio environment fingerprint;
- device motion/activity state;
- local clock/circadian features;
- optional calendar/task context;
- optional weather/ambient context if explicitly enabled;
- privacy and retention treatment.

Context snapshots are not timing truth. They are explanatory evidence and feature inputs.

## Timing analytics ontology

Parallax must treat these quantities as distinct:

| Quantity | Meaning | Source | Can update activity duration baseline? |
|---|---|---|---|
| `wall_seconds` | elapsed time between run boundaries | source events + reconstruction | yes, with review |
| `active_seconds` | time doing the actual activity | spans + review | yes, with review |
| `setup_seconds` | preparation time | spans/extraction/review | review-dependent |
| `detour_seconds` | resource or path detours | spans/extraction/review | no for duration baseline; yes for friction model |
| `interruption_seconds` | unrelated interruption | spans/extraction/review | no for duration baseline; yes for friction model |
| `waiting_seconds` | blocked time | spans/extraction/review | review-dependent |
| `side_quest_seconds` | nested unrelated work | spans/extraction/review | no for original baseline |
| `start_latency_seconds` | time between intended and actual start | start latency observations | start model only |
| `transition_seconds` | time moving between activities/phases | transition observations | transition model only |
| `recovery_seconds` | time to regain flow after interruption | inferred/corrected spans | separate friction/attention model |
| `context_switch_count` | number of significant mode/activity switches | event graph | friction/attention model |
| `uncertainty_score` | confidence in reconstructed timeline | reconciliation engine | controls review burden |
| `sensor_quality_score` | reliability/availability of context data | context snapshots | explanatory only |

Do not create a generic `duration` field without a qualifier.

## Context-aware analytics features

The analytics layer should compute and store feature vectors only after source data is normalized and privacy policy is applied.

Recommended feature families:

### Temporal/circadian features

- local hour bucket;
- day of week;
- weekday/weekend;
- morning/afternoon/evening/night;
- user-defined energy window if configured;
- time since previous run;
- time since previous interruption-heavy run;
- intended-start delta;
- deadline proximity when the user configured one.

### Activity features

- activity ID;
- activity relationship cluster;
- checkpoint template IDs;
- work mode;
- actor mode;
- preflight state;
- user estimate;
- previous recent p50/p80;
- last-run duration.

### Geospatial/place features

- inferred place ID;
- place category;
- coarse location cluster;
- place confidence;
- indoor/outdoor hint if derivable without invasive capture;
- distance from prior place;
- transition path class: same place, nearby, commute-like, errand-like, travel-like;
- GPS accuracy bucket;
- radio fingerprint cluster ID.

### Device/sensor features

- capture method;
- permission quality;
- app foreground/locked/background;
- motion state;
- charging/battery bucket;
- network connectivity;
- capture delay between event and sync;
- clock drift/monotonic clock quality.

### Friction features

- open detour at completion;
- interruption count;
- waiting count;
- side-quest count;
- resource dependency hits;
- repeated location-specific friction;
- user-corrected span ratio;
- unreviewed extraction ratio.

## ML/analytics model roadmap

### Baseline deterministic analytics

Build first. This is the source of user trust.

- robust rolling p50/p80 by activity;
- winsorized or trimmed stats for outlier resistance;
- confidence labels from sample count and dispersion;
- event/spans reconciliation rules;
- activity profile facts from reviewed runs only.

### Contextual quantile estimator

Add after enough reviewed data exists.

Purpose: predict active/wall/start/transition ranges conditioned on context.

Candidate approaches:

- grouped empirical quantiles by `(activity, work_mode, place_category, actor_mode)`;
- hierarchical shrinkage so low-sample contexts borrow strength from parent activity/global priors;
- quantile regression or gradient-boosted quantile models once sample volume exists;
- pinball loss as the primary objective;
- calibration checks for p50 and p80 coverage.

Do not train contextual models on unreviewed, discarded, or sensor-only inferred events.

### Start-latency model

Start latency is not task duration. It is often the hidden planning cost.

Candidate approaches:

- survival/hazard model for probability of starting within a window;
- logistic model for "will start by planned time";
- contextual features: place, prior activity, time-of-day, deadline proximity, energy window, prior interruptions;
- feedback loop: nudges must be evaluated for usefulness and annoyance.

### Friction/preflight model

Purpose: suggest checks that reduce avoidable detours.

Candidate approaches:

- resource dependency frequency;
- place-specific resource misses;
- sequence-aware repeated friction;
- confidence threshold with user-confirmed usefulness;
- contextual bandit only after a safe deterministic rule baseline exists.

The model should optimize for fewer high-quality suggestions, not maximum suggestion volume.

### Anomaly/outlier model

Purpose: protect baselines and explain unusual runs.

Signals:

- forgot-to-stop pattern;
- impossible event sequence;
- wall/active ratio far outside prior distribution;
- sensor context changed sharply while timer stayed active;
- run completed at a very different place than it started;
- unreviewed long gap;
- low-quality capture context.

An anomaly should ask for review. It should not silently discard data unless the user has configured that behavior.

### Place inference and radio fingerprint clustering

Purpose: help distinguish "same activity at different places" and explain timing variability.

Approach:

- cluster geospatial observations by user, never globally;
- store raw radio identifiers only as salted hashes or encrypted short-retention artifacts;
- infer place candidates with explicit confidence;
- require user confirmation before labeling places as home, work, sensitive, or private;
- support place aliases and corrections.

### LLM role

LLMs may help summarize context and extract candidate friction from annotations. They must not:

- compute durations;
- invent place labels;
- infer sensitive place categories without confirmation;
- update timing baselines;
- decide permission policy;
- create hidden capture behavior.

## Analytics storage posture

Postgres remains the source of truth. TimescaleDB can accelerate time-series projections but should not replace the relational timing/event model.

Use:

- source tables for canonical facts;
- `capture_context_snapshot` and observation tables for context;
- `temporal_feature_vector` for ML-ready derived features;
- `activity_stats_snapshot` for user-visible stats;
- optional TimescaleDB shadow tables for high-volume analytics;
- optional PostGIS profile for geospatial indexing;
- optional pgvector/ParadeDB for retrieval, not for canonical timing truth.

## Evaluation requirements

Add the following eval families to the existing test strategy:

### Timing analytics evals

- p50 and p80 coverage by activity;
- active/wall/start/transition separation;
- model inclusion filter correctness;
- outlier handling behavior;
- low-sample confidence behavior.

### Contextual prediction evals

- pinball loss for p50/p80;
- context ablation: does place/work mode improve prediction?
- no leakage from discarded/unreviewed sessions;
- calibration by place category and activity;
- graceful fallback when context is unavailable.

### Place inference evals

- inferred place precision/recall on user-confirmed samples;
- false sensitive-label rate;
- permission-denied fallback;
- retention/redaction behavior;
- indoor/outdoor and radio fingerprint quality where available.

### Prompt/nudge evals

- suggestion precision;
- accepted/hidden/snoozed/retired rates;
- interruption burden;
- false-positive capture prompts;
- "felt creepy" qualitative feedback.

## Implementation rule

Context should reduce review burden only when confidence is high and privacy risk is low. Otherwise it should create transparent evidence, not automatic truth.
