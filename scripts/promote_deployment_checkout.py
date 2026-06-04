from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess  # nosec B404
from dataclasses import dataclass
from pathlib import Path

DEFAULT_REPO = Path("/tank/repos/parallax")


@dataclass(frozen=True)
class PromotionResult:
    status: str
    detail: str


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Promote a preserved Parallax deployment checkout to a target commit. "
            "Dry-run by default; pass --apply to mutate the checkout."
        )
    )
    parser.add_argument("--repo", type=Path, default=DEFAULT_REPO)
    parser.add_argument("--target", required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if args.apply:
        result = apply_deployment_checkout(
            repo=args.repo,
            target=args.target,
            snapshot=args.snapshot,
        )
    else:
        result = dry_run_deployment_checkout(
            repo=args.repo,
            target=args.target,
            snapshot=args.snapshot,
        )
    print(f"{result.status}: {result.detail}")
    return 0 if result.status == "ready" else 1


def dry_run_deployment_checkout(
    *,
    repo: Path,
    target: str,
    snapshot: Path,
) -> PromotionResult:
    snapshot_result = verify_snapshot_matches(repo=repo, snapshot=snapshot)
    if snapshot_result.status != "ready":
        return snapshot_result
    target_result = _target_exists(repo, target)
    if target_result.status != "ready":
        return target_result
    return PromotionResult(
        "ready",
        (
            "snapshot matches current checkout; rerun with --apply to reset tracked files "
            "to target and remove non-ignored untracked files"
        ),
    )


def apply_deployment_checkout(
    *,
    repo: Path,
    target: str,
    snapshot: Path,
) -> PromotionResult:
    dry_run = dry_run_deployment_checkout(repo=repo, target=target, snapshot=snapshot)
    if dry_run.status != "ready":
        return dry_run
    git = _git_executable()
    reset = subprocess.run(
        [git, "-C", str(repo), "reset", "--hard", target],
        check=False,
        capture_output=True,
        text=True,
    )  # nosec B603
    if reset.returncode != 0:
        return PromotionResult("blocked", _first_line(reset.stderr) or "git reset failed")
    clean = subprocess.run(
        [git, "-C", str(repo), "clean", "-fd"],
        check=False,
        capture_output=True,
        text=True,
    )  # nosec B603
    if clean.returncode != 0:
        return PromotionResult("blocked", _first_line(clean.stderr) or "git clean failed")
    status = _git(repo, "status", "--short").stdout.strip()
    if status:
        return PromotionResult("blocked", "deployment checkout is still dirty after promotion")
    return PromotionResult("ready", f"deployment checkout promoted to {target}")


def verify_snapshot_matches(*, repo: Path, snapshot: Path) -> PromotionResult:
    repo = repo.resolve()
    snapshot = snapshot.resolve()
    if not (repo / ".git").exists():
        return PromotionResult("blocked", f"not a git checkout: {repo}")
    manifest = _read_manifest(snapshot / "snapshot_manifest.txt")
    current_head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    if manifest.get("head") != current_head:
        return PromotionResult(
            "blocked",
            f"snapshot head {manifest.get('head')} does not match current head {current_head}",
        )
    checksums = _read_checksums(snapshot / "checksums.sha256")
    expected_patch_sha = checksums.get(str(snapshot / "worktree.patch"))
    current_patch_sha = hashlib.sha256(_git(repo, "diff", "--binary").stdout.encode()).hexdigest()
    if expected_patch_sha != current_patch_sha:
        return PromotionResult("blocked", "tracked patch checksum differs from snapshot")
    return PromotionResult("ready", "snapshot matches current checkout")


def _target_exists(repo: Path, target: str) -> PromotionResult:
    result = subprocess.run(
        [_git_executable(), "-C", str(repo), "rev-parse", "--verify", f"{target}^{{commit}}"],
        check=False,
        capture_output=True,
        text=True,
    )  # nosec B603
    if result.returncode != 0:
        return PromotionResult("blocked", f"target commit is not available: {target}")
    return PromotionResult("ready", "target commit is available")


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [_git_executable(), "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )  # nosec B603


def _git_executable() -> str:
    git = shutil.which("git")
    if git is None:
        raise RuntimeError("git executable is required")
    return git


def _read_manifest(path: Path) -> dict[str, str]:
    manifest: dict[str, str] = {}
    for line in path.read_text().splitlines():
        key, separator, value = line.partition("=")
        if separator:
            manifest[key] = value
    return manifest


def _read_checksums(path: Path) -> dict[str, str]:
    checksums: dict[str, str] = {}
    for line in path.read_text().splitlines():
        digest, separator, filename = line.partition("  ")
        if separator:
            checksums[filename] = digest
    return checksums


def _first_line(value: str) -> str:
    return next((line.strip() for line in value.splitlines() if line.strip()), "")


if __name__ == "__main__":
    raise SystemExit(main())
