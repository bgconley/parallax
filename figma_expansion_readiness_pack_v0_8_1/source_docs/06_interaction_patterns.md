# Interaction Patterns

## 1. Capture-to-structure pattern

1. User enters raw text or voice.
2. App immediately creates a local source object.
3. UI confirms save.
4. Router/AI suggests chips or route asynchronously.
5. User can accept, ignore, correct, or deepen.

This protects capture from network/model latency.

## 2. Progressive depth pattern

Each object supports four levels:

- Row: title and minimal metadata.
- Sheet: notes, reminders, estimate, checklist.
- Plan: task graph, dependencies, materials, AI structure.
- Execution: Now Card/timer/recovery.

The user should never be forced through all four.

## 3. AI suggestion pattern

AI output appears as:

- Editable chips.
- Suggested breakdown.
- “Why this?” link.
- Confidence language.
- One-tap alternatives.

AI output must always be reversible.

## 4. Stuck recovery pattern

1. User taps Stuck.
2. App asks one plain question.
3. User chooses friction type.
4. App proposes one repair.
5. User accepts, edits, defers, or switches strategy.

Do not respond to stuck with a lecture.

## 5. Timing checkpoint pattern

1. User starts timing.
2. Large timer runs.
3. User taps checkpoint after phase.
4. App optionally asks for a label.
5. Finish leads to quick review.
6. Timing data becomes future estimate signal.

Checkpoint labeling must be optional. If unlabeled, the system can infer later.

## 6. Offline pattern

When offline, the app does not block source actions. It says what is true:

- “Saved locally.”
- “AI refinement pending.”
- “Using your last known estimate.”
- “Sync will resume automatically.”

Avoid red error banners for normal offline use.

## 7. Notification and reminder pattern

Reminders are user-controlled. The app may suggest a reminder, but should not silently create noisy reminders. Reminder personalization is critical.

## 8. Review pattern

Review should ask for useful corrections, not moral accounting.

Good:

- “Was this bigger than usual?”
- “Should I use this time estimate next time?”
- “Carry this to tomorrow?”

Bad:

- “You failed to complete 7 tasks.”
- “Improve your productivity score.”
