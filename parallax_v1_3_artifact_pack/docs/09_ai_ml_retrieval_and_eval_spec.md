# 09 — AI, Retrieval, and Evaluation Specification

## AI role boundary

AI in Parallax has three valid roles:

1. Interpret user context into structured candidate events.
2. Help retrieve, cluster, or summarize evidence.
3. Narrate deterministic facts in a humane way.

AI must not:

- own duration facts;
- silently update duration baselines;
- invent evidence;
- quote private raw context without permission;
- make uncorrectable decisions;
- block timer source actions.

## Model roles

### Context extractor

Input:

- redacted annotation;
- session context;
- current checkpoint;
- timer position;
- privacy class;
- allowed taxonomy.

Output:

- one or more extracted context events;
- proposed count policy;
- confidence;
- sensitive data flag;
- suggested preflight check when relevant.

### Query intent classifier

Input:

- user question;
- optional scoped activity;
- available activity aliases;
- privacy flags.

Output:

- query intent;
- activity/entity candidates;
- time window;
- required facts;
- unsupported components.

### Query narrator

Input:

- computed facts;
- selected evidence;
- limitations;
- permitted quote policy.

Output:

- answer structure with short answer, facts, evidence references, limitations, and confidence.

### Preflight suggester

Input:

- repeated resource dependencies/friction patterns;
- activity profile;
- recent corrections.

Output:

- candidate preflight check with evidence and confidence.

## Structured output controls

Every model output must have:

- prompt version;
- schema version;
- model/provider/version;
- input privacy class;
- schema validation result;
- confidence;
- repair count;
- evidence or source IDs;
- correction path.

Invalid structured output must be rejected. Repair loops may run but must be capped.

## Prompt-injection controls

Imported or user-provided content is untrusted. Prompts must treat notes, transcripts, activity names, and imported text as data, not instructions. The AI orchestrator should strip or neutralize obvious instruction-like content before model calls when possible.

## Retrieval architecture

Retrieval supports:

- activity resolution;
- similar run lookup;
- delay/friction clustering;
- preflight check suggestions;
- query evidence selection.

Retrieval document types:

- `activity_summary`
- `activity_alias`
- `timing_session_summary`
- `checkpoint_run_summary`
- `extracted_context_event_summary`
- `preflight_check`
- `user_correction`
- `query_answer`

Baseline retrieval uses PostgreSQL FTS. pgvector can add semantic retrieval. ParadeDB can add BM25/faceted/hybrid ranking after readiness tests.

## Embedding policy

Do not store every embedding in one generic table. Use:

- `embedding_model` registry;
- one embedding table per dimension/profile;
- immutable model metadata;
- re-embedding plan;
- dual-read comparison before promotion.

Sensitive/private raw notes should not be embedded by default. Derived summaries can often preserve utility without storing sensitive text.

## Evaluation families

### Temporal semantics evals

Verify:

- active/wall/friction counting;
- start latency separation;
- transition latency separation;
- review inclusion behavior;
- correction propagation.

### Context extraction evals

Verify:

- schema validity;
- category accuracy;
- count-policy accuracy;
- confidence calibration;
- sensitive-data detection;
- preflight suggestion precision;
- unnecessary confirmation rate.

### Query grounding evals

Verify:

- no invented facts;
- sample size included;
- time window included;
- limitations included;
- evidence references valid;
- privacy quote settings respected;
- active/wall/start latency distinctions preserved.

### Numeric calibration evals

Verify:

- p50/p80 coverage;
- prediction interval width;
- active/wall split error;
- start-by success;
- estimator drift after corrections.

## Human review gates

LLM-derived outputs require confirmation when:

- confidence is low or medium and the event affects counting;
- sensitive data is present;
- duration extraction is uncertain;
- count policy is ambiguous;
- a preflight suggestion might be annoying or overgeneralized.

## Fallback behavior

If models are unavailable:

- timing still works;
- annotations remain captured;
- extraction status remains pending;
- review can proceed manually;
- Ask can return deterministic facts without narrative if available.


## v1.3 timing analytics and sensor/context ML readiness

v1.3 adds context-aware analytics, but the trust boundary remains the same: AI and ML may propose, classify, cluster, and explain; user-reviewed timing events remain the durable source of duration truth.

### Additional model roles

#### Place/context inferrer

Input:

- permitted capture context snapshots;
- geospatial observations;
- radio observations;
- device context;
- user-confirmed places;
- privacy settings.

Output:

- inferred place candidate;
- confidence;
- evidence summary;
- privacy/sensitive-place flag;
- "needs user confirmation" decision.

#### Contextual duration estimator

Input:

- reviewed timing sessions;
- derived spans;
- activity/checkpoint identity;
- user-confirmed place/category;
- work/actor mode;
- temporal/circadian features;
- feature eligibility policy.

Output:

- p50/p80 active range;
- p50/p80 wall range;
- contextual confidence;
- sample size and parent fallback path;
- feature attribution summary safe for user display.

#### Start-latency estimator

Input:

- intended start observations;
- actual start observations;
- context features;
- prior user corrections;
- nudge history.

Output:

- probability of starting by time window;
- expected start-latency range;
- nudge eligibility;
- confidence and burden score.

### Additional evaluation families

- Place inference precision/recall on user-confirmed places.
- Sensitive-place false-label rate.
- Contextual estimator calibration by context bucket.
- Sensor ablation tests.
- Permission-denied fallback quality.
- Prompt burden and false-positive review rate.
- Battery/context-capture budget tests.
