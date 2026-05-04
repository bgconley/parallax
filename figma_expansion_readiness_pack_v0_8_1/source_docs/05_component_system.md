# Component System

## 1. Component philosophy

Every component should answer a clear role in the execution loop. Avoid decorative components that do not carry state, action, or meaning.

## 2. Core components

### 2.1 List Row / List Card

Purpose: represent a human container.

Anatomy:

- Icon/color marker.
- List name.
- Optional count.
- Optional shared indicator.
- Optional recent activity/progress.

Variants:

- Default
- Pinned
- Shared
- Smart list
- Empty
- Offline pending

### 2.2 Task Row

Purpose: represent captured intent.

Anatomy:

- Completion control.
- Title.
- Optional metadata chips.
- Optional small estimate/date.
- Optional route/status indicator.

Variants:

- Simple
- Today
- Start-by
- Waiting-for
- Overdue
- Routine step
- Has plan
- Has timing history
- Offline pending

Rules:

- Title remains primary.
- Metadata should not exceed one compact line in dense mode.
- Avoid showing all model-derived data by default.

### 2.3 Capture Field

Purpose: accept raw intent.

Anatomy:

- Placeholder.
- Input area.
- Voice button.
- Attach button optional.
- Save/route action.
- Inferred chips after input.

Variants:

- Contextual list add
- Global quick capture
- Voice capture
- Share-sheet capture
- Offline capture

### 2.4 Inference Chip

Purpose: show AI/system interpretation without forcing a form.

Examples:

- Today
- 20–30 min
- Needs plan
- Reminder?
- Errand
- Waiting for Alex
- High friction

States:

- Suggested
- Accepted
- Edited
- Dismissed
- Low confidence

Rules:

- Chips must be tappable/editable.
- Low confidence chips should appear as suggestions, not facts.
- Dismissed chips should not nag the user.

### 2.5 Now Card

Purpose: execute one action.

Anatomy:

- Parent context.
- Now action.
- Done-enough boundary.
- Estimate/start-by.
- Primary Done button.
- Support rail.

Variants:

- Ready
- Active
- Timer active
- Stuck
- Blocked
- Complete
- Offline cached

### 2.6 Stuck Option Button

Purpose: quickly diagnose friction.

Anatomy:

- Icon.
- Plain-language label.
- Optional one-line explanation.

Variants:

- Too big
- Too vague
- No energy
- Not enough time
- Missing something
- Waiting
- Dreading
- Lost context

### 2.7 Timing Instrument

Purpose: measure active task time.

Anatomy:

- Elapsed time.
- Current phase.
- Checkpoint button.
- Pause/interruption.
- Finish.
- Split history.

Variants:

- Not started
- Active
- Paused
- Interrupted
- Checkpoint review
- Completed

### 2.8 Estimate Chip

Purpose: surface Temporal Intelligence gently.

Anatomy:

- Range or estimate.
- Confidence indicator.
- Basis text: “based on 7 sessions” or “estimate still learning.”

Variants:

- No history
- Low confidence
- Personal history
- Last similar
- Start-by
- Overrun risk

### 2.9 Route Badge

Purpose: show selected workflow route when useful.

Examples:

- Tiny start
- Checklist
- Full plan
- Reminder
- Routine
- Timing
- Recovery

Rule: route badges should mostly appear in detail/plan views, not every task row.

### 2.10 Offline / Sync Indicator

Purpose: reassure, not alarm.

States:

- Saved locally
- Syncing
- Synced
- Needs attention
- AI pending

Copy should be plain:

- “Saved on this iPhone.”
- “Will refine when online.”
- “Synced.”

## 3. Component density modes

Support at least two visual density modes:

- Comfortable: default, high legibility, more whitespace.
- Compact: for power users, but still accessible.

Optional later:

- Focus mode: hides most metadata.
- Detail mode: shows estimates, routes, and statuses.

## 4. Component implementation notes

Agentic coder should generate SwiftUI components with explicit view models. Avoid hardcoding AI state into views. Views should receive `source_state`, `derived_state`, `sync_state`, and `confidence` where relevant.
