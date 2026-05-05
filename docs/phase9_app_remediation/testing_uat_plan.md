# Phase 9 App Remediation Testing And UAT Plan

## Test Authority

Use `parallax_v1_3_artifact_pack/docs/12_testing_qa_release_rollback.md` as the
test authority. Mac tests can prove Swift correctness. Functional,
integration, end-of-phase, and production-style validation must run on the GPU
node.

## Local Swift Test Gate

Run from `apps/ios`:

```sh
swift test
```

Required coverage:

- `ParallaxRuntimeConfig` has no default activity/preflight fixture.
- clean app store launch has empty/create/select activity state.
- connected app store loads activities from `GET /v1/activities`.
- dynamic activity creation sends canonical mutation envelope.
- selected activity drives launcher, session, review, profile, and Ask copy.
- timer start/pause/resume/finish computes elapsed and active durations from
  injected clock.
- quick capture stores arbitrary user-entered note text.
- friction capture stores arbitrary resource/friction text.
- checkpoint setup reads/writes dynamic checkpoint templates.
- preflight decisions require a real check ID.
- review buttons save `.saveUsefulRun`, `.markUnusual`, and discard decisions.
- Ask About Time submits `POST /v1/temporal/query` in connected mode.
- offline mode queues but does not fabricate backend answers.
- source leak guard rejects banned fixture strings in runtime files.
- visible button guard rejects empty action closures.

## Local Xcode Build/Test Gate

Use the iOS simulator target:

```sh
xcodebuild \
  -project apps/ios/ParallaxNative.xcodeproj \
  -scheme ParallaxNative \
  -destination 'platform=iOS Simulator,name=iPhone 17' \
  build
```

If a UI test target is added, run it against a clean simulator and preserve the
result bundle under `.phase9_evidence/`.

## Repo Test Gate

Run from repository root:

```sh
uv run pytest -q
uv run ruff check .
make typecheck
make validate
make phase8-smoke
make release-status
```

Do not claim release readiness from `release-status`; it is a truth report for
broader release gates.

## GPU-Node Backend Gate

After committing/pushing from the Mac, pull to the GPU node:

```sh
ssh -i /Users/brennanconley/vibecode/infx/ubuntu24_ed25519 bgconley@10.25.0.50 \
  'cd /tank/repos/parallax && git pull --ff-only'
```

Run backend checks with:

```sh
PATH=/home/bgconley/.local/bin:$PATH \
UV_PROJECT_ENVIRONMENT=/tank/venvs/parallax \
make phase1-smoke phase2-smoke phase3-smoke phase4-smoke phase5-smoke phase6-smoke phase7-smoke
```

Run any new Phase 9 app remediation smoke on the GPU node, not only locally.

## Simulator UAT Scenario

Use a clean simulator or reset Parallax app data. Connect the native app to the
GPU-node API through the accepted tunnel/proxy route. Use a unique activity and
note for every run, for example:

- activity: `UAT Dynamic Activity <timestamp>`
- note: `UAT dynamic note <timestamp>`
- question: `How long does UAT Dynamic Activity <timestamp> take?`

Required automated flow:

1. Launch app with backend config and no seeded activity.
2. Verify empty/create/select state.
3. Create the unique activity.
4. Verify Temporal Home shows the unique activity and no fixture strings.
5. Open launcher.
6. Choose a measurement mode.
7. Start timing.
8. Pause.
9. Resume.
10. Capture the unique note.
11. Log a dynamic friction item from typed text.
12. Finish.
13. Review and save useful run.
14. Open Activity Profile.
15. Ask the unique time question.
16. Retry sync if any local queue remains.
17. Terminate and relaunch.
18. Verify selected activity/current state persists.

## Backend Evidence Checks

After UAT, query the GPU-node API or database to prove:

- one activity exists with the exact unique activity name;
- timing session rows reference that activity;
- event rows include start, pause, resume, completion, review, and capture
  mutations;
- context annotation or queued event contains the exact unique note;
- temporal query row contains the exact unique question;
- no row for the UAT user/device contains banned fixture strings unless the UAT
  operator typed them.

Banned fixture strings for UAT:

- `Clean pots and pans`
- `Clean the kitchen`
- `sponge`
- `Load dishwasher`
- `Hand-wash pans`
- `Pack lunch`
- `Laundry`
- `NC2`
- `Alex`

## Visual And Interaction Evidence

Capture screenshots or simulator snapshots for:

- clean empty state;
- dynamic activity selected on Temporal Home;
- launcher with dynamic activity;
- active timing session;
- context capture with dynamic note;
- review with dynamic durations;
- Activity Profile no-data or low-sample state;
- Ask About Time pending/answered state;
- sync queue when backend is unavailable.

Check each screenshot for clipping, overlap, cramped text, inaccessible tap
targets, and Dynamic Type risk.

## Done Criteria

The phase is not done until:

- all tests above pass;
- GPU-node UAT passes;
- evidence files are saved under `.phase9_evidence/`;
- `git status --short` is understood and contains no accidental build output;
- a final summary names exact validation commands and outcomes.
