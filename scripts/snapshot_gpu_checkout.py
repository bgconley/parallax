from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess  # nosec B404
import sys
import tarfile
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_REPO = Path("/tank/repos/parallax")
DEFAULT_SNAPSHOT_ROOT = Path("/home/bgconley/parallax-release-parity-snapshots")
SECRET_SUFFIXES = (".jwt", ".key", ".pem", ".token")
SECRET_NAMES = {".env"}
SECRET_PARTS = {"secrets"}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Snapshot a Parallax GPU checkout before release parity changes."
    )
    parser.add_argument("--repo", type=Path, default=DEFAULT_REPO)
    parser.add_argument("--snapshot-root", type=Path, default=DEFAULT_SNAPSHOT_ROOT)
    parser.add_argument("--label", default="gpu_dirty")
    args = parser.parse_args()

    try:
        snapshot = snapshot_checkout(
            repo=args.repo,
            snapshot_root=args.snapshot_root,
            label=args.label,
        )
    except RuntimeError as exc:
        print(f"snapshot failed: {exc}", file=sys.stderr)
        return 1
    print(snapshot)
    return 0


def snapshot_checkout(
    *,
    repo: Path,
    snapshot_root: Path,
    label: str,
    timestamp: str | None = None,
) -> Path:
    repo = repo.resolve()
    if not (repo / ".git").exists():
        raise RuntimeError(f"not a git checkout: {repo}")
    timestamp = timestamp or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    snapshot = snapshot_root / f"{label}_{timestamp}"
    snapshot.mkdir(parents=True, exist_ok=False)

    head = _git(repo, "rev-parse", "HEAD").stdout
    status = _git(repo, "status", "--short", "--branch").stdout
    patch = _git(repo, "diff", "--binary").stdout
    untracked = _git(repo, "ls-files", "--others", "--exclude-standard").stdout.splitlines()
    safe_untracked = [path for path in untracked if not _is_secret_path(path)]

    (snapshot / "head.txt").write_text(head)
    (snapshot / "status.txt").write_text(status)
    (snapshot / "worktree.patch").write_text(patch)
    (snapshot / "untracked_sanitized_files.txt").write_text(
        "".join(f"{path}\n" for path in safe_untracked)
    )
    (snapshot / "snapshot_manifest.txt").write_text(
        "\n".join(
            (
                f"repo={repo}",
                f"head={head.strip()}",
                f"status_entries={len(status.splitlines())}",
                f"safe_untracked_files={len(safe_untracked)}",
                f"excluded_untracked_files={len(untracked) - len(safe_untracked)}",
            )
        )
        + "\n"
    )
    _write_untracked_archive(repo, snapshot / "untracked_sanitized.tgz", safe_untracked)
    _write_checksums(
        snapshot / "checksums.sha256",
        (
            snapshot / "worktree.patch",
            snapshot / "untracked_sanitized.tgz",
            snapshot / "untracked_sanitized_files.txt",
        ),
    )
    return snapshot


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    git = shutil.which("git")
    if git is None:
        raise RuntimeError("git executable is required")
    return subprocess.run(
        [git, "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )  # nosec B603


def _is_secret_path(path: str) -> bool:
    candidate = Path(path)
    parts = {part.casefold() for part in candidate.parts}
    name = candidate.name.casefold()
    suffix = candidate.suffix.casefold()
    return bool(SECRET_PARTS & parts) or name in SECRET_NAMES or suffix in SECRET_SUFFIXES


def _write_untracked_archive(repo: Path, archive_path: Path, paths: list[str]) -> None:
    with tarfile.open(archive_path, "w:gz") as archive:
        for path in paths:
            archive.add(repo / path, arcname=path, recursive=True)


def _write_checksums(output_path: Path, paths: tuple[Path, ...]) -> None:
    lines = []
    for path in paths:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path}\n")
    output_path.write_text("".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
