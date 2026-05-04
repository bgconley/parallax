# Canonical Native iOS Design Language v0.8

## 1. One-sentence design thesis

[APP_NAME] is a warm, native, list-first execution companion that lets thoughts land instantly, quietly turns them into useful structure, and helps the user move through time, tasks, recovery, and routines without forcing a full workflow every time.

## 2. Design north star

The app should feel like Wunderlist rebuilt for a modern AI-native iOS world: instantly habitable, emotionally warm, list-native, fast enough for fragile thoughts, and powerful enough to handle complex life without exposing that complexity prematurely.

The app should not feel like OmniFocus, Notion, Jira, a database, a team workspace, a clinical intervention, or a chatbot wrapper.

## 3. Brand/product posture

The app is not here to discipline the user. It is here to receive, clarify, suggest, and recover.

It should feel composed rather than motivational. It may be warm, but never cutesy. It may be intelligent, but never theatrical. It may guide, but should not scold. It may provide structure, but should never make the user feel defective for needing it.

## 4. Governing principles

### 4.1 Capture precedes classification

The user must be able to capture a thought without choosing a project, workflow, tag, priority, date, energy level, or AI mode. The thing must be allowed to exist before it is understood.

### 4.2 Lists are human containers; graphs are infrastructure

The backend may use task graphs, dependencies, embeddings, workflow routes, timing models, and AI artifacts. The user should mostly experience lists, cards, chips, sheets, and flows.

When the system needs to expose deeper structure, it should do so as a “plan view” or “breakdown view,” not as a permanent graph UI.

### 4.3 One obvious action per moment

Each screen should have one dominant next action. Secondary actions may be available, but they should not compete.

Examples:

- Capture screen: Add / Save.
- Today: Start next or choose what fits.
- Now Card: Done, with Stuck and Smaller nearby.
- Timing: Checkpoint or Pause.
- Recovery: Pick what is making this hard.

### 4.4 Power appears at the edge, not in the center

Advanced fields, routing details, filters, graph explanations, source artifacts, model confidence, and personalization controls should be one gesture away. They should not define the first read of a screen.

### 4.5 AI is a quiet assistant, not a visible character

AI should appear as inferred chips, suggested actions, confidence notes, “why this is next,” and repair suggestions. The app should avoid default chatbot framing unless the user explicitly opens an assistant-like interface.

### 4.6 Recovery is a designed path

A user getting stuck, distracted, late, overwhelmed, or offline is not an exceptional error. It is an expected state. The UI should contain recovery paths as first-class flows.

### 4.7 Time is visible, empirical, and forgiving

Temporal Intelligence should not be expressed as harsh productivity analytics. It should be expressed as practical, gentle realism: estimate ranges, start-by times, confidence, buffers, and “last time this took...” context.

### 4.8 The app should be modular without feeling modular

The router may choose capture-only, reminder, tiny start, checklist, timebox, routine, full plan, stuck recovery, communication helper, or timing. The user should experience this as the app offering the right shape for the task, not as selecting from a menu of modes.

## 5. Emotional temperature

The app should feel:

- Calm, not sleepy.
- Warm, not sentimental.
- Precise, not mechanical.
- Capable, not intimidating.
- Polished, not precious.
- Human, not therapeutic.
- Intelligent, not clever.

## 6. Visual language

### 6.1 Overall look

Use an iOS-native visual language with warm surfaces, strong typography, generous touch targets, soft cards, restrained color, and familiar Apple platform primitives.

The app should feel at home on modern iOS, including system materials and current platform conventions, but it should not overuse translucency. Glass/material effects should clarify hierarchy, not decorate surfaces.

### 6.2 Shape

Use soft continuous-radius rectangles and pill chips. Avoid hard enterprise corners. Avoid extreme bubbly shapes that feel childish. Suggested radii:

- Large cards: 22–28 pt.
- Medium cards/sheets: 18–22 pt.
- Small chips: 12–16 pt or full pill.
- Icon containers: 12–16 pt.

### 6.3 Color

Use a warm neutral foundation, with a clear primary accent and restrained semantic colors.

Default light mode should not be pure white everywhere. Use a warm canvas, elevated cards, and subtle dividers. Dark mode should use softened near-black and dark warm neutrals, not harsh OLED black by default.

Color must never be the only carrier of meaning.

### 6.4 Typography

Use SF Pro / system fonts. The UI should rely on font weight, size, and spacing more than color for hierarchy.

Suggested hierarchy:

- Large title: Home / Today context.
- Title 2 / Title 3: list names, sheet titles, Now Card action.
- Body: task titles and instructions.
- Callout / Subheadline: metadata chips, estimates, confidence notes.
- Footnote / Caption: provenance, sync state, muted explanations.

Avoid dense all-caps labels. Avoid long uppercase navigation labels. Use sentence case.

### 6.5 Spacing

Use a calm 4 pt base grid, with most major spacing at 8, 12, 16, 20, 24, and 32 pt.

The screen should breathe. ADHD-friendly does not mean cramming everything above the fold. The important thing is fast recognition, not maximum density.

### 6.6 Icons

Use SF Symbols where possible. Prefer outline symbols for passive metadata and filled/weighted symbols only for active state or primary actions.

Symbols should clarify meaning, not create a second visual language. Avoid novelty icons for core objects.

## 7. Interaction language

### 7.1 Capture

Capture should be available from everywhere. It should support text, voice, share sheet, photo/screenshot later, and contextual list entry.

The first input should feel like a text field, not a form. The user writes naturally. The app infers chips after entry.

### 7.2 Contextual add

Inside a list, the add field belongs to that list. This is crucial to the Wunderlist-like feeling. The user should feel they are adding to a place, not launching a generic task modal.

### 7.3 Sheets and detail

Use bottom sheets and inline expansion for detail. A task detail should feel like opening the back of an index card, not navigating into an admin page.

### 7.4 Menus

Use menus for secondary actions: move, duplicate, convert to routine, archive, export, advanced plan options. Do not hide primary actions in menus.

### 7.5 Swipe actions

Support common iOS swipe gestures, but never require them. Swipes can expose complete, defer, remind, and flag/star. Every swipe action must be available through a visible menu or button too.

### 7.6 Haptics

Use haptics sparingly: capture saved, task completed, checkpoint marked, timer started/stopped, stuck path selected, recovery accepted. Haptics should signal state change, not decorate every tap.

## 8. Primary navigation model

Recommended initial iPhone navigation:

- Home: lists, pinned spaces, inbox, today, recently used.
- Today: realistic day plan and up-next surfaces.
- Capture: global quick capture / voice capture. May be center tab or prominent floating action.
- Timing / Now: active execution when relevant; otherwise accessible from Today.
- Settings/Profile: preferences, privacy, sync, integrations, accessibility.

Alternate: four-tab model with Home, Today, Capture, Settings, while active Now/Timing is elevated as a live bottom card. This may be cleaner.

The app should avoid a left-sidebar information architecture on iPhone. iPad and Mac can use sidebars later.

## 9. Object model in UI terms

### 9.1 List

A list is a human container. It may represent groceries, work, life admin, cleaning, trip prep, routines, someday ideas, or a shared household space. Lists are the visible home of most tasks.

### 9.2 Task

A task is a captured intent that may be simple or complex. It can remain a simple row forever, or unfold into subtasks, timing history, reminders, dependencies, notes, and AI plan artifacts.

### 9.3 Plan

A plan is a structured breakdown of a task. It should appear as an optional breakdown, not as the default representation of every task.

### 9.4 Now Card

The Now Card is the execution surface. It should show one action, completion boundary, estimate, context, and recovery affordances.

### 9.5 Timing Session

A timing session is an instrumented execution event. It should feel like Voice Memos plus a workout timer: start, checkpoint, pause, finish, review.

### 9.6 Routine

A routine is a repeatable sequence. It should support full, short, and minimum viable modes.

## 10. The app should feel simple because it routes complexity

The app will have sophisticated backend capabilities: workflow routing, LLM extraction, task graph generation, temporal modeling, local sync, retrieval, and personalization. The design should not expose those mechanisms as permanent UI structures.

The user should feel: “I put something in; the app understood enough to help.”

The agentic coder should implement: structured state machines, view models, derived UI artifacts, routing contracts, and offline/sync states.
