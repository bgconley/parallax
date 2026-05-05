# Phase 9 App-Wide Remediation Pack

Status: planning and implementation specification only. This pack is canonical
for the Phase 9 app remediation slice until superseded by an explicit product
decision.

## Problem Statement

The current native iOS app proves that selected API calls can be made, but it is
not yet a real Parallax application. Runtime launch, Today/Temporal Home,
launcher, active timing, review, drawers, context capture, checkpoint setup,
Activity Profile, Ask About Time, sync, and tests are contaminated by copied
Figma/example scenarios such as "Clean pots and pans", "sponge", "kitchen",
"Load dishwasher", "Hand-wash pans", and the NC2/Alex email example.

Those examples are valid artifact-pack examples and visual fixtures. They are
not default app state, not user data, and not product behavior. Phase 9
remediation converts the entire shipped iOS app into a dynamic temporal-first
application backed by canonical v1.3 contracts.

## Source Of Truth

Read these before implementing or reviewing this remediation:

1. `parallax_v1_3_artifact_pack/AGENT_START_HERE.md`
2. `parallax_v1_3_artifact_pack/docs/01_app_system_spec.md`
3. `parallax_v1_3_artifact_pack/docs/02_temporal_domain_model.md`
4. `parallax_v1_3_artifact_pack/docs/03_phased_implementation_plan.md`
5. `parallax_v1_3_artifact_pack/database/README.md`
6. `parallax_v1_3_artifact_pack/contracts/openapi/parallax_api_v1_3.yaml`
7. `parallax_v1_3_artifact_pack/contracts/events/parallax_event_contracts_v1_3.yaml`
8. `parallax_v1_3_artifact_pack/contracts/jobs/parallax_workflows_v1_3.yaml`
9. `parallax_v1_3_artifact_pack/docs/23_agentic_implementation_guardrails.md`
10. `parallax_v1_3_artifact_pack/docs/12_testing_qa_release_rollback.md`

The existing `docs/phase10_temporal_home_interactions/` artifacts remain useful
only as a Figma action inventory. They do not authorize hardcoded runtime data
and do not narrow this remediation to Temporal Home only.

## Scope

This remediation covers the full current native iOS Parallax app:

- app launch and runtime configuration;
- activity selection, creation, and empty state;
- Today/Temporal Home;
- timing launcher and measurement mode choice;
- active timing session;
- context capture and quick note capture;
- checkpoint setup and step drawers;
- friction/evidence drawers;
- preflight drawers and decisions;
- timing review, review decisions, forgotten timer flags, and discard flows;
- Activity Profile;
- Ask About Time;
- privacy and offline/sync surfaces;
- local persistence, pending sync, and mutation envelopes;
- simulator UAT against the GPU-node backend.

This remains temporal scope. It must not introduce broad task management,
agenda/due-date workflows, generic project planning, routine-builder scope, or
general assistant behavior unless a canonical artifact or explicit product
decision adds that scope.

## Non-Negotiable Runtime Rules

- Runtime app launch must never default to example activity names or example
  preflight text.
- `PARALLAX_ACTIVITY_NAME`, `PARALLAX_ACTIVITY_ID`, and
  `PARALLAX_PREFLIGHT_CHECK_TEXT` may be supported as UAT seed inputs, but their
  absence must lead to a real empty/create/select state, not a demo.
- Demo and Figma data may exist only in preview fixtures or explicitly named test
  fixtures.
- Every visible user action must either change local app state, call/queue a
  canonical API workflow, open a drawer backed by data, navigate to a real
  surface, or be explicitly display-only.
- Timing must work when sensor permissions are denied and when the backend is
  temporarily unreachable.
- Every mutating API call must carry a canonical `MutationEnvelope`.
- Resolver POST endpoints remain read-only.
- Ask About Time must call `POST /v1/temporal/query` in connected mode. A queued
  local intent is not an answer.
- Context capture must capture user-entered text. It must not submit fixed
  "sponge" notes unless the user actually typed that text.
- Review decisions decide model inclusion. LLM or workflow output must not alter
  source timing facts without explicit user correction or review.

## Artifact Files

- `implementation_spec.md`: architecture and implementation slices.
- `workflow_action_contract.md`: screen and action contract for the full current
  app.
- `testing_uat_plan.md`: test, simulator, GPU-node, and release evidence plan.
- `agent_execution_checklist.md`: step-by-step checklist for the coding agent.

## Acceptance Gate

Phase 9 app remediation is complete only when all of these are true:

- A clean simulator with no Parallax app data launches to an empty/create/select
  activity flow and contains no example scenario strings.
- The user can create an arbitrary activity name, start timing, pause/resume,
  capture arbitrary context text, log friction from user-entered data, finish,
  review, save/discard, view profile state, and ask a time question.
- Connected UAT against the GPU node proves backend rows contain the dynamic
  user-entered activity and notes.
- The app never creates "Clean pots and pans", "Clean the kitchen", "sponge",
  "Load dishwasher", "Hand-wash pans", "Pack lunch", "Laundry", "NC2", or
  "Alex" unless entered by the UAT operator.
- Swift tests, Xcode build/tests, local Python tests, and GPU-node smoke tests
  pass.
- No visible SwiftUI `Button` in app runtime has an empty action.
- `make release-status` still reports the broader release gate truth without
  claiming private-alpha readiness unless the release gates are separately met.
