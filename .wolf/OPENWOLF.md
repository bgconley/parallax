# OpenWolf Operating Protocol

You are working in an OpenWolf-managed project. These rules apply every turn.

## File Navigation

1. Check `.wolf/anatomy.md` BEFORE reading any file. It has a 2-3 line description and token estimate for every file in the project.
2. If the description in anatomy.md is sufficient for your task, do NOT read the full file.
3. If a file is not in anatomy.md, search with Grep/Glob, then update anatomy.md with the new entry.
4. For Parallax implementation or infrastructure decisions, read the relevant canonical artifact files before inferring from the GPU node or another app's layout.

## Code Generation

1. Before generating code, read `.wolf/cerebrum.md` and respect every entry.
2. Check the `## Do-Not-Repeat` section — these are past mistakes that must not recur.
3. Follow all conventions in `## Key Learnings` and `## User Preferences`.

## Environment Routing

- Unit tests may run on the Mac.
- Run all functional tests, integration tests, end-of-phase verification/validation tests, and backend operations on the GPU node; the application will live there.
- Run frontend testing, Xcode work, SwiftUI work, initial Figma work, and Playwright UI validation on the Mac.
- Access the GPU node with `ssh -i /Users/brennanconley/vibecode/infx/ubuntu24_ed25519 bgconley@10.25.0.50`.
- For GPU-node storage, first follow `parallax_v1_3_artifact_pack/infrastructure/zfs/zfs_dataset_plan.md` and `create_parallax_datasets.sh`: use the `parallax` namespace, `/srv/parallax` mountpoints, and the actual node pool name as the script argument.
- Use `/tank/repos/parallax` for the GPU-node repo checkout and `/tank/venvs/parallax` for Parallax virtualenvs. After Mac-side changes are pushed, pull updates from remote in `/tank/repos/parallax`. If rsyncing an uncommitted working tree for GPU validation, exclude `.env`, `.git`, `.venv`, `.DS_Store`, and `__pycache__` so host-local runtime config is preserved.
- `tank/venvs` is root ext4 on the GPU node, not a ZFS dataset; `/tank/venvs/parallax` is still the accepted Parallax venv path.
- Use `uv` for GPU-node Parallax Python work. `uv` is at `/home/bgconley/.local/bin/uv`; non-interactive SSH may need `PATH=/home/bgconley/.local/bin:$PATH`. Always set `UV_PROJECT_ENVIRONMENT=/tank/venvs/parallax` so `uv` uses the accepted app venv instead of creating `/tank/repos/parallax/.venv`.
- Parallax runtime datasets are mounted as `tank/parallax/*` under `/srv/parallax`. Use `scripts/setup_gpu_node_storage.sh` for dataset/bootstrap setup and `scripts/apply_gpu_node_permissions.sh` when only ownership/modes need to be applied.
- Remote sudo over SSH needs a TTY. Use `ssh -tt ... 'sudo -v && sudo <command>'`; do not prefix the Mac-side SSH command with local `sudo`.
- Current runtime permission policy: `/srv/parallax` `root:root 0755`; `postgres` and `postgres_wal` numeric `999:999 0700`; `objects`, `exports`, `models`, `hf_cache`, and `logs` numeric `10001:bgconley 0770`; `config` and `observability` `bgconley:bgconley 0755`; `backups` `root:bgconley 0750`.
- Host passwd/group names for numeric UID/GID `999` may display as unrelated local accounts. Treat the numeric IDs as the source of truth until the pinned Postgres image is verified.
- Do not begin any later phase without explicit user instruction. Phase 0 through Phase 9 are complete. Do not start Phase 10 or broaden later work without explicit user instruction. Phase gates must be proven with repo validation, Compose render/start, health readiness, baseline migrations, and GPU-node validation.
- Phase 0 Compose uses Parallax-specific localhost ports to avoid conflicts with other GPU-node stacks: API `18000`, Postgres `15432`, Redis `16379`, Temporal `17233`, Temporal UI `18088`, MinIO `19000/19001`, and Caddy `18080/18443`.
- Baseline migrations are run with `scripts/apply_migrations.py`; the runner reads `migrations/` only and excludes optional profiles unless explicitly enabled later.
- Temporal auto-setup `1.24` requires `DB=postgres12`, not `DB=postgresql`.
- Deferred release work that must be implemented at the right later phase: production/private-alpha auth provider and JWT/session validation, remaining canonical v1.3 endpoint surface, backup/restore plus WAL/archive proof, load/performance SLO validation, later-phase Temporal workflows, and production traffic/log privacy-scrub proof. Do not pull these into Phase 3 unless the user explicitly starts that scope.

## Parallax UI/UX Scope Guard

- Treat `figma_expansion_readiness_pack_v0_8_1/` as design-language reference only: native iOS grammar, spacing, typography, card/chip patterns, accessibility posture, interaction tone, and Liquid Glass treatment. It is not product-scope authority for Parallax.
- Keep active Parallax UI scope temporal: timing sessions, timing launcher/calibration, timing review/correction, checkpoints or "break it down" only as timing workflow support, temporal home/current focus, offline/sync/AI-pending/needs-review/high-contrast/Dynamic Type/reduced-motion states for those workflows, and grounded temporal answers only where Phase 7 supports them.
- Do not add broad task/project management, generic inbox/task-tracker flows, routine builders, broad weekly reviews, broad personalization/settings, or unrelated assistant/planning workflows just because they appear in the expansion pack or Figma reference material. Require a canonical artifact or explicit product decision first.
- Active Figma work must be source-backed or canonical-derived from `parallax_v1_3_artifact_pack/examples/` and the current canonical Figma reference pages. Simplified vector drafts are not finished mockups.
- Before declaring Figma/UI work complete, capture screenshots, scrutinize spacing/alignment/centering/clipping/overlap/text fit, and compare directly against the canonical mockups.
- Current active Temporal Home Figma target is `10 Phase 8 Temporal Home Canonical Allocation` at `https://www.figma.com/design/OYOtLrgwZmqAqsURzYJBM9/Parallax---v1.3-Native-Screens?node-id=118-2`; the active implementation board is node `118:3`. The earlier `106:2` temporal scope draft was deleted after QA found unacceptable cramped text, lane collisions, and overlap risk.
- Preserve the canonical Today schema and density for this target: header, current focus, intelligence card, timeline/list block, quick capture, and bottom action pair. Do not fix visual defects by reducing item count, removing canonical sections, or making oversized empty text boxes. Fix defects by reallocating lanes and positions so right-side badge/action lanes, left-side title/meta lanes, progress/caption lanes, and drawer content lanes do not overlap, clip, or crowd borders.

## After Actions

1. After every significant action, append a one-line entry to `.wolf/memory.md`:
   `| HH:MM | description | file(s) | outcome | ~tokens |`
2. After creating, deleting, or renaming files: update `.wolf/anatomy.md`.

## Cerebrum Learning (MANDATORY — every session)

OpenWolf's value comes from learning across sessions. You MUST update `.wolf/cerebrum.md` whenever you learn something useful. This is not optional.

**Update `## User Preferences` when the user:**
- Corrects your approach ("no, do it this way instead")
- Expresses a style preference (naming, structure, formatting)
- Shows a preferred workflow or tool choice
- Rejects a suggestion — record what they preferred instead
- Asks for more/less detail, verbosity, explanation

**Update `## Key Learnings` when you discover:**
- A project convention not obvious from the code (e.g., "tests go in __tests__/ not test/")
- A framework-specific pattern this project uses
- An API behavior that surprised you
- A dependency quirk or version constraint
- How modules connect or data flows through the system

**Update `## Do-Not-Repeat` (with date) when:**
- The user corrects a mistake you made
- You try something that fails and find the right approach
- You discover a gotcha that would trip up a fresh session

**Update `## Decision Log` when:**
- A significant architectural or technical choice is made
- The user explains why they chose approach A over B
- A trade-off is explicitly discussed

**The bar is LOW.** If in doubt, add it. A cerebrum entry that's slightly redundant costs nothing. A missing entry means the next session repeats the same discovery process.

## Bug Logging (MANDATORY)

**Log a bug to `.wolf/buglog.json` whenever ANY of these happen:**
- The user reports an error, bug, or problem
- A test fails or a command produces an error
- You fix something that was broken
- You edit a file more than twice to get it right
- An import, module, or dependency is missing or wrong
- A runtime error, type error, or syntax error occurs
- A build or lint command fails
- A feature doesn't work as expected
- You change error handling, try/catch blocks, or validation logic
- The user says something "doesn't work", "is broken", or "shows wrong X"

**Before fixing:** Read `.wolf/buglog.json` first — the fix may already be known.

**After fixing:** ALWAYS append to `.wolf/buglog.json` with this structure:
```json
{
  "id": "bug-NNN",
  "timestamp": "ISO date",
  "error_message": "exact error or user complaint",
  "file": "file that was fixed",
  "root_cause": "why it broke",
  "fix": "what you changed to fix it",
  "tags": ["relevant", "keywords"],
  "related_bugs": [],
  "occurrences": 1,
  "last_seen": "ISO date"
}
```

**The threshold is LOW.** When in doubt, log it. A false positive in the bug log costs nothing. A missed bug means repeating the same mistake later.

## Token Discipline

- Never re-read a file already read this session unless it was modified since.
- Prefer anatomy.md descriptions over full file reads when possible.
- Prefer targeted Grep over full file reads when searching for specific code.
- If appending to a file, do not read the entire file first.

## Design QC

When the user asks you to check, evaluate, or improve the design/UI of their app:

1. Run `openwolf designqc` via Bash to capture screenshots.
   - The command auto-detects a running dev server, or starts one from package.json if needed
   - Use `--url <url>` only if auto-detection fails
   - The command saves compressed JPEG screenshots to `.wolf/designqc-captures/`
   - Full pages are captured as sectioned viewport-height images (top, section2, ..., bottom)
2. Read the captured screenshot images from `.wolf/designqc-captures/` using the Read tool.
3. Evaluate the design against modern standards (Shadcn UI, Tailwind, clean React patterns):
   - Spacing and whitespace consistency
   - Typography hierarchy and readability
   - Color contrast and accessibility (WCAG)
   - Visual hierarchy and focal points
   - Component consistency
   - Whether the design looks "dull" or "white-coded" (generic, no personality)
4. Provide specific, actionable feedback with fix suggestions.
5. If the user approves, implement the fixes directly in their code.
6. After fixes, re-run `openwolf designqc` to capture new screenshots and verify improvement.

**Token awareness:** Each screenshot costs ~2500 tokens. The command compresses images (JPEG quality 70, max width 1200px) to minimize cost. For large apps, use `--routes / /specific-page` to limit captures.

## Reframe — UI Framework Selection

When the user asks to change, pick, migrate, or "reframe" their project's UI framework:

1. Read `.wolf/reframe-frameworks.md` for the full framework knowledge base.
2. Ask the user the decision questions from the file (current stack, priority, Tailwind usage, theme preference, app type). Stop early once the choice narrows to 1-2 options.
3. Present a recommendation with reasoning based on the comparison matrix.
4. Once the user confirms, use the selected framework's prompt from the file — **adapted to the actual project** using `.wolf/anatomy.md` for real file paths, routes, and components.
5. Execute the migration: install dependencies, update config, refactor components.
6. After migration, run `openwolf designqc` to verify the new look.

**Do NOT read the entire reframe-frameworks.md into context upfront.** Read the decision questions and comparison matrix first (~50 lines). Only read the specific framework's prompt section after the user chooses.

## Session End

Before ending or when asked to wrap up:

1. Write a session summary to `.wolf/memory.md`.
2. Review the session: did you learn anything? Did the user correct you? Did you fix a bug? If yes, update `.wolf/cerebrum.md` and/or `.wolf/buglog.json`.
