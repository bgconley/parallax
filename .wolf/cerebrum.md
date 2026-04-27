# Cerebrum

> OpenWolf's learning memory. Updated automatically as the AI learns from interactions.
> Do not edit manually unless correcting an error.
> Last updated: 2026-04-27

## User Preferences

<!-- How the user likes things done. Code style, tools, patterns, communication. -->
- Unit tests may run on the Mac, but all functional tests, integration tests, end-of-phase verification/validation tests, and backend operations must run on the GPU node where Parallax will live. Frontend testing, Xcode/SwiftUI work, initial Figma work, and Playwright UI validation should run on the Mac.
- GPU node access: `ssh -i /Users/brennanconley/vibecode/infx/ubuntu24_ed25519 bgconley@10.25.0.50`.
- Before inferring anything about Parallax implementation or infrastructure from the GPU node, existing apps, or local conventions, review the relevant canonical artifact files and let them drive the decision.
- Use `/tank/repos/parallax` for the GPU-node repo checkout and `/tank/venvs/parallax` for Parallax virtualenvs. Pull remote updates into `/tank/repos/parallax` after Mac-side pushes.

## Key Learnings

- **Project:** parallax
- **Canonical ZFS setup:** Parallax storage starts from `infrastructure/zfs/zfs_dataset_plan.md` and `infrastructure/zfs/create_parallax_datasets.sh`: datasets use the `parallax` namespace, mount under `/srv/parallax`, and the real ZFS pool name must be passed to the script.
- **GPU node storage additions:** Parallax uses existing `/tank/repos` and `/tank/venvs` parents, with project subdirectories `/tank/repos/parallax` and `/tank/venvs/parallax`.

## Do-Not-Repeat

<!-- Mistakes made and corrected. Each entry prevents the same mistake recurring. -->
<!-- Format: [YYYY-MM-DD] Description of what went wrong and what to do instead. -->
- [2026-04-27] Do not infer Parallax storage layout from existing GPU-node directories before reading the canonical artifact. For ZFS/storage work, review the Parallax ZFS plan and dataset script first.

## Decision Log

<!-- Significant technical decisions with rationale. Why X was chosen over Y. -->
