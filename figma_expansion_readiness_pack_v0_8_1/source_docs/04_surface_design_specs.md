# Screen and Surface Design Specs

## 1. Home / Lists

### Primary question

Where should this thought live, and what place do I want to enter?

### Layout

Top: large title, search field, optional profile/sync indicator.

Middle: smart entries: Inbox, Today, Active, Waiting, Routines. These should look like list rows/cards, not dashboard widgets.

Lower: pinned lists and recent lists, each with subtle counts and optional shared indicators.

Bottom: tab bar or floating capture action.

### Design notes

Home should feel like a hallway with doors, not a cockpit. It should be beautiful, calm, and fast. Avoid showing charts here.

### Empty state

“Start with anything.”

Primary action: “Capture a thought.”

Secondary action: “Create a list.”

## 2. Quick Capture

### Primary question

What needs to leave my head right now?

### Layout

A large field with placeholder copy like: “Type anything — task, worry, reminder, errand...”

Voice button nearby. Attach button optional. Save button always reachable.

After text entry, show inferred chips:

- Friday
- Reminder?
- Errand
- 20 min?
- Work?
- Needs plan?

The item must be savable even if the chips are wrong or ignored.

### State variants

- Blank
- Typing
- Inferring
- Chips ready
- Saved locally/offline
- Saved and refining
- Needs one clarification

### Acceptance criteria

The user can capture a raw thought in under 5 seconds without choosing metadata.

## 3. Capture Inbox / Triage

### Primary question

What have I captured that still needs a home or shape?

### Layout

Inbox items as warm cards or rows. Each item shows raw text first, then quiet suggestions below. Suggested routes should be chips, not mandatory modals.

Actions:

- Keep in Inbox
- Move to list
- Make task
- Make reminder
- Break down
- Dismiss/archive

### Design notes

Inbox should not feel like a pile of failure. It should feel like a landing pad.

## 4. Today

### Primary question

What fits in this day?

### Layout

Header: date, day state, optional energy mode.

Up Next card: one suggested next thing.

Timeline/blocks: optional, especially after calendar integration.

Today list: tasks grouped by Now-ready, start-by, routine, later.

Footer: “Review day” or “Adjust plan.”

### Design notes

Today is not a dashboard. It is a realistic plan. The visual tone should reduce panic.

### Key elements

- Fit indicator: “Looks realistic” / “Tight day” / “Overfull.”
- Start-by chips.
- Estimate ranges.
- Low-energy switch.
- “What can wait?” action.

## 5. List View

### Primary question

What belongs in this place?

### Layout

Title area with list icon/color. Contextual add field. Task rows. Completed items collapsed. Optional sections.

Task rows show:

- Checkbox/status.
- Title.
- Optional estimate/date/list metadata.
- Optional route/AI/timing chips only when useful.

### Design notes

The list should feel writable. Avoid making it a report.

## 6. Task Detail Sheet

### Primary question

What do I need to know or change about this item?

### Layout

Sheet over list context. Title first. Notes below. Then metadata chips row. Then checklist/plan. Then AI suggestions. Activity and advanced settings at bottom.

### Design notes

The detail sheet should feel like the back of an index card. It should not feel like a form unless the user enters edit mode.

## 7. AI Plan Builder

### Primary question

Does this plan match reality?

### Layout

Top: original capture, summarized intent, route confidence.

Body: generated steps as editable task rows with optional dependency lines. Use indentation carefully. Avoid visual spaghetti.

Right/secondary area on larger screens: estimate, materials, decisions, risk, confidence.

Actions:

- Use plan
- Make smaller
- Make simpler
- Make more complete
- Only give me the first step
- Ask one clarifying question

### Design notes

The plan builder is where AI is visible, but still restrained. The user should see useful structure, not model theatrics.

## 8. Now Card

### Primary question

What do I do right now?

### Layout

Large card. One action sentence. Completion boundary. Time estimate. Done button. Support rail: Smaller, Timer, Stuck, Defer, Why.

### Design notes

This surface should be gorgeous and extremely legible. It is the execution membrane.

### State variants

- Ready
- Active
- Timer active
- Checkpointed
- Stuck
- Blocked
- Deferred
- Complete
- Offline/cached

## 9. Stuck / Recovery

### Primary question

What is blocking movement?

### Layout

Sheet or card. Friendly but direct prompt. Large option buttons. No blame. Route to repair.

Options:

- Too big
- Too vague
- No energy
- Not enough time
- Missing something
- Waiting on someone
- Dreading it
- I forgot why

Repair output:

- Smaller action
- Clarifying question
- Materials checklist
- Defer plan
- Body double/timer
- Waiting-for reminder

## 10. Timing Session

### Primary question

How long is this actually taking, and what phase am I in?

### Layout

Large timer. Current phase. Checkpoint button. Pause/interruption. Finish.

Checkpoint history as a simple timeline below, not a spreadsheet.

Completion review asks only what matters:

- Normal session?
- Interrupted?
- Forgot timer?
- With help?
- Harder/easier than usual?

### Design notes

This should borrow the clarity of Voice Memos and workout timers, not time-tracking software.

## 11. Routine Run

### Primary question

What is the next step in this recurring sequence?

### Layout

Routine title. Mode selector: Full / Short / Minimum. Step list. Current step prominent. Timer optional.

### Design notes

Routines should support partial success. Skipping a step should not make the entire routine feel failed.

## 12. Review / Learn

### Primary question

What should the app learn from what happened?

### Layout

A gentle summary. Few questions. Carryover decisions. Estimate corrections.

### Design notes

Review should not feel like a performance report. It should feel like adjusting the map.

## 13. Settings / Personalization

### Primary question

How should the app support me?

### Layout

Sections:

- Account and sync
- AI and privacy
- Reminders and notifications
- Task granularity
- Visual density
- Accessibility
- Timing intelligence
- Data export/deletion
- Integrations

### Design notes

Settings are not where the core product lives, but for this app they are important because cognitive preferences vary widely.
