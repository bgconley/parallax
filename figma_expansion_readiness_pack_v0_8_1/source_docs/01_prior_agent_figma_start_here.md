# Agent / Figma Start Here — [APP_NAME] UI/UX Design Language v0.8

You are generating native iOS mockups for an AI-powered executive-function, task-planning, timing, and recovery application. The prior working codename was `LumenTask`, but the final production app name is not chosen. Use `[APP_NAME]` in symbolic labels and avoid baking the codename into UI unless explicitly instructed.

## Non-negotiable product posture

This app is not a project-management cockpit. It is not OmniFocus. It is not Jira-lite. It is not a chatbot with checkboxes. It is a warm, fast, list-native, AI-assisted execution companion.

The interface must let users express intent before it demands structure. A user must be able to open the app, capture a thought, and leave in seconds. Deeper planning, timing, task graphs, reminders, recovery, and model explanations must be progressively available without making the first interaction feel heavy.

## Core visual direction

Use warm minimalism with progressive power.

The UI should feel:

- Native iOS, not cross-platform generic.
- Calm and refined, not playful-chaotic.
- Habitable, not sterile.
- Fast to enter, gentle to recover from.
- Highly legible, with clear hierarchy.
- Softly structured, not flat or database-like.
- AI-enhanced, but never AI-showoff.

## Primary inspiration synthesis

- Wunderlist: lists as natural human containers; a place where thoughts can land.
- Things: restrained detail views and optional metadata.
- Todoist/Fantastical: natural-language input that infers structure.
- Apple Reminders: native integration, simple task actions, shared-list familiarity.
- Voice Memos: one-tap capture and recording/timing flow.
- Apple Health: customizable priority summary with clean drill-down.
- Flighty/Live Activities: ambient status for time-sensitive execution.
- Superlist: modern continuation of the Wunderlist lineage, but do not over-workspace the design.

## Main surfaces to design first

Design these as a coherent connected prototype, not separate feature screens:

1. Home / Lists / Pinned Spaces
2. Quick Capture
3. Capture Inbox / Triage
4. Today / Day Plan
5. List View
6. Task Detail Sheet
7. AI Plan Builder / Task Graph Review
8. Now Card / Execution Surface
9. Stuck / Recovery Flow
10. Timing Session / Temporal Intelligence
11. Routine Run
12. Review / Learn
13. Settings / Personalization / Privacy
14. Empty / Offline / Sync / Error states

## Component philosophy

The task row is the atomic unit. The list is the primary spatial object. The detail sheet is the index card. The Now Card is the execution membrane. The Timing Surface is a calm instrument panel. The AI should appear as quiet inference chips, not as a mascot or chatbot bubble by default.

## Design output expectations

Create Figma frames at iPhone 15/16 Pro logical dimensions. Use Auto Layout. Define tokens/styles first. Build components with variants. Include light mode first, then dark mode variants. Include accessibility stress frames for large text, reduced transparency, and high contrast.

The app must not rely on color alone for status. Every state needs text/icon/shape redundancy. Interactive targets should be comfortable for real mobile use. Avoid tiny metadata controls packed into rows.

## Guardrails

Do not create a dashboard as the main home. Do not create a giant setup wizard. Do not make AI chat the primary UI. Do not put every feature on the first screen. Do not make adding a task look like filing a ticket. Do not make the user classify the thought before it exists.
