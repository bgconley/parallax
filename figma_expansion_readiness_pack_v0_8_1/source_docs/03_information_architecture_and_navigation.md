# Information Architecture and Navigation Model

## 1. IA thesis

The app should be list-first, not dashboard-first. The home screen should answer “where can this thought live?” before it answers “how productive am I?”

## 2. Primary surface model

### Home

Purpose: let the user find or create a place for thoughts.

Visible elements:

- Search / quick find.
- Inbox.
- Today.
- Active/Now if present.
- Waiting.
- Pinned lists.
- Recent lists.
- Optional active Now/Timing live card.
- Minimal sync/offline indicator only when relevant.

Do not make Home a metrics dashboard.

### Today

Purpose: show what realistically fits today.

Visible elements:

- Day header with date and optional energy context.
- Up Next / Now-ready task.
- Calendar/time blocks if connected.
- Tasks selected for today.
- Start-by items.
- Routines due today.
- Low-energy mode toggle when appropriate.

### Capture

Purpose: accept unstructured intent.

Visible elements:

- Large natural-language field.
- Voice button.
- Optional attach/share/photo affordances.
- Inferred chips after input.
- “Save” / “Route” / “Plan” actions.

### List View

Purpose: be the everyday working surface.

Visible elements:

- List title and list controls.
- Contextual add field.
- Task rows.
- Sections only when useful.
- Completed tucked away.
- Lightweight sort/filter controls.

### Task Detail Sheet

Purpose: reveal depth without breaking context.

Visible elements:

- Title field.
- Notes.
- Checklist/subtasks.
- Date/reminder chips.
- Estimate chip.
- AI suggestions/replan controls.
- Attachments/comments if enabled.
- Activity/source history tucked low.

### Plan Builder

Purpose: review and edit AI-generated structure.

Visible elements:

- Original capture preserved.
- Suggested workflow route.
- Task breakdown with dependencies.
- Estimate and confidence.
- “Make smaller,” “Make simpler,” “Make complete,” “Use this plan.”

### Now Card

Purpose: execute one action.

Visible elements:

- One action sentence.
- Completion boundary.
- Estimate/time context.
- Done button.
- Smaller, Stuck, Timer, Defer.
- Why this is next.

### Stuck / Recovery

Purpose: convert stalled action into a smaller, clearer, or deferred path.

Visible elements:

- “What is making this hard?”
- Options: too big, unclear, no energy, not enough time, missing something, anxious/avoidant, waiting on someone.
- Repair path.
- No shame language.

### Timing Session

Purpose: collect empirical duration data without turning timing into a burden.

Visible elements:

- Large elapsed time.
- Checkpoint button.
- Pause/interruption.
- Current phase label.
- Finish.
- Completion review.

### Review / Learn

Purpose: turn outcomes into future realism.

Visible elements:

- What got done.
- What slipped.
- What took longer.
- Gentle calibration questions.
- Tomorrow carryover choices.

### Settings / Personalization

Purpose: give control over cognitive load, AI behavior, reminders, privacy, sync, integrations, and accessibility.

Visible elements:

- Account / sync.
- AI and privacy.
- Reminder preferences.
- Task granularity.
- Visual density.
- Accessibility.
- Data export/deletion.

## 3. Navigation rule

The app can contain deep capabilities, but everyday navigation should remain shallow. Most users should live in Home, Today, Capture, List, Task Detail, Now, and Timing.

## 4. Modes vs surfaces

Avoid exposing workflow modes as primary navigation. The router chooses the mode; the UI presents the right shape.

For example:

- “Return package” becomes reminder + errand cluster.
- “Clean kitchen” becomes tiny start or checklist.
- “Taxes” becomes full plan + life admin + timing estimates.
- “I am overwhelmed” becomes recovery/low-energy day.

The user should not have to choose these modes up front.
