# [APP_NAME] Native iOS Design Language Pack v0.8

Generated: 2026-04-20T23:43:04

This pack is a design-language and Figma-handoff companion to the canonical project artifact pack v0.7. It converts the product, workflow, AI, offline-first, timing, and modular-execution architecture into a native iOS design system direction that can be used by an agentic coder with Figma integration.

The working codename used in earlier artifacts was `LumenTask`. Do not treat that codename as the final production name. All UI copy, Figma naming, code naming, and app metadata should be parameterized around `[APP_NAME]` or another final name selected by the project owner.

## Design thesis

Capture like Voice Memos. Organize like Wunderlist. Clarify like Things. Parse like Todoist. Surface priority like Apple Health. Show live execution context like a restrained Live Activity. Recover like a product that understands people actually fall out of flow.

The result should feel warm, native, fast, and instantly habitable. It should not feel like OmniFocus, Jira, Notion, a database, a chatbot shell, or an enterprise cockpit.

## Folder structure

```text
app_ios_design_language_pack_v0_8/
  README.md
  AGENT_FIGMA_START_HERE.md
  MANIFEST.txt
  VALIDATION_REPORT.md
  docs/
  figma/
  tokens/
  contracts/
  examples/
  tests_or_eval/
  source_inputs/
```

## Most important files

Start with:

1. `AGENT_FIGMA_START_HERE.md`
2. `docs/01_canonical_design_language.md`
3. `docs/04_surface_design_specs.md`
4. `docs/05_component_system.md`
5. `figma/figma_agent_prompt.md`
6. `tokens/design_tokens.json`
7. `contracts/ui_state_model.schema.json`
8. `tests_or_eval/ux_acceptance_checklist.md`

## Use with Figma agent

This pack is written to be consumed in two modes:

- A human design pass: read the canonical language, then draw/refine.
- An agentic Figma pass: provide `AGENT_FIGMA_START_HERE.md`, `figma/figma_agent_prompt.md`, tokens, frame inventory, and component specs as the working context.

The agent should build mockups as native iOS screens, not generic web dashboards. It should prefer SF typography, native spacing rhythm, system materials, native sheets, menus, controls, haptics, and accessibility-aware Dynamic Type behavior.
