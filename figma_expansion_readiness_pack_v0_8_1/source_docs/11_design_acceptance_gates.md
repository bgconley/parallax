# Design Acceptance Gates

## Gate 1: Capture Friction

A first-time user must be able to capture a raw thought without selecting metadata, granting permissions, creating a project, or waiting on AI.

Pass criteria:

- Capture available from Home and global action.
- Task title/raw text is the only required input.
- Offline save state exists.
- AI chips appear after capture, not before capture.

## Gate 2: Progressive Power

A simple task must remain simple. A complex task must be able to deepen.

Pass criteria:

- “Take trash out” does not become a full plan by default.
- “Plan taxes” can become a full task graph.
- User can escalate/deescalate route.

## Gate 3: Wunderlist Habitability

The app should feel like a place where thoughts live.

Pass criteria:

- Lists are primary spatial objects.
- Contextual add field exists inside lists.
- Home is not a metrics dashboard.
- Task rows are readable and calm.

## Gate 4: Now Card Clarity

The user can identify the immediate action within 2 seconds.

Pass criteria:

- One action sentence.
- Done-enough boundary.
- Done button visually primary.
- Stuck/Smaller/Timer available.

## Gate 5: Recovery Without Shame

The stuck flow should make forward movement easier without scolding.

Pass criteria:

- No failure language.
- Friction choices are plain.
- Repair suggestions are concrete.
- Defer is a valid outcome.

## Gate 6: Temporal Intelligence Usability

Timing and estimates should support realism without creating anxiety.

Pass criteria:

- Estimates shown as ranges/confidence.
- Timing can start quickly.
- Checkpoint labels optional.
- Completion review is short.

## Gate 7: Offline Resilience

The UI should make offline normal source actions possible.

Pass criteria:

- Capture works offline.
- Timing works offline.
- Local states are clear.
- AI pending state is non-alarming.

## Gate 8: Accessibility and Cognitive Load

The app should remain usable with large text, reduced motion, high contrast, and screen reader use.

Pass criteria:

- Dynamic Type stress frames pass.
- No color-only states.
- Primary actions are visible.
- Reminder intensity and visual density are configurable.

## Gate 9: Native iOS Polish

The app should feel like a true iOS citizen.

Pass criteria:

- Native controls, materials, and sheet patterns.
- SF Symbols where appropriate.
- Haptics meaningful and restrained.
- Permission prompts contextual.

## Gate 10: Agentic Buildability

Design artifacts must map cleanly to code.

Pass criteria:

- Components have variants.
- Screens have state models.
- Tokens exist.
- Acceptance criteria exist.
- Empty/error/offline states are included.
