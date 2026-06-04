import subprocess
from pathlib import Path

from scripts.promote_deployment_checkout import (
    apply_deployment_checkout,
    verify_snapshot_matches,
)
from scripts.snapshot_gpu_checkout import snapshot_checkout


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _repo_with_candidate_and_dirty_worktree(tmp_path: Path) -> tuple[Path, str, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    (repo / "tracked.txt").write_text("base\n")
    _git(repo, "add", "tracked.txt")
    _git(repo, "commit", "-m", "base")
    base_branch = _git(repo, "branch", "--show-current").strip()

    _git(repo, "checkout", "-b", "candidate")
    (repo / "tracked.txt").write_text("candidate\n")
    (repo / "candidate.txt").write_text("candidate file\n")
    _git(repo, "add", "tracked.txt", "candidate.txt")
    _git(repo, "commit", "-m", "candidate")
    target = _git(repo, "rev-parse", "HEAD").strip()

    _git(repo, "checkout", base_branch)
    (repo / "tracked.txt").write_text("dirty local copy\n")
    (repo / "untracked.txt").write_text("untracked evidence\n")
    snapshot = snapshot_checkout(
        repo=repo,
        snapshot_root=tmp_path / "snapshots",
        label="gpu_dirty",
        timestamp="20260604T000000Z",
    )
    return repo, target, snapshot


def test_verify_snapshot_matches_current_dirty_checkout(tmp_path: Path) -> None:
    repo, _, snapshot = _repo_with_candidate_and_dirty_worktree(tmp_path)

    result = verify_snapshot_matches(repo=repo, snapshot=snapshot)

    assert result.status == "ready"
    assert result.detail == "snapshot matches current checkout"


def test_verify_snapshot_rejects_changed_sanitized_untracked_evidence(
    tmp_path: Path,
) -> None:
    repo, _, snapshot = _repo_with_candidate_and_dirty_worktree(tmp_path)
    (repo / "untracked.txt").write_text("changed after snapshot\n")

    result = verify_snapshot_matches(repo=repo, snapshot=snapshot)

    assert result.status == "blocked"
    assert "untracked evidence differs from snapshot" in result.detail


def test_verify_snapshot_rejects_unpreserved_secret_like_untracked_files(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    (repo / "tracked.txt").write_text("base\n")
    _git(repo, "add", "tracked.txt")
    _git(repo, "commit", "-m", "base")
    (repo / "secret.jwt").write_text("raw-token\n")
    snapshot = snapshot_checkout(
        repo=repo,
        snapshot_root=tmp_path / "snapshots",
        label="gpu_dirty",
        timestamp="20260604T000000Z",
    )

    result = verify_snapshot_matches(repo=repo, snapshot=snapshot)

    assert result.status == "blocked"
    assert "unpreserved secret-like untracked files" in result.detail


def test_apply_deployment_checkout_requires_matching_snapshot(tmp_path: Path) -> None:
    repo, target, snapshot = _repo_with_candidate_and_dirty_worktree(tmp_path)
    (repo / "tracked.txt").write_text("new unpreserved mutation\n")

    result = apply_deployment_checkout(repo=repo, target=target, snapshot=snapshot)

    assert result.status == "blocked"
    assert "tracked patch checksum differs" in result.detail
    assert _git(repo, "status", "--short")


def test_apply_deployment_checkout_updates_to_target_after_verified_snapshot(
    tmp_path: Path,
) -> None:
    repo, target, snapshot = _repo_with_candidate_and_dirty_worktree(tmp_path)

    result = apply_deployment_checkout(repo=repo, target=target, snapshot=snapshot)

    assert result.status == "ready"
    assert _git(repo, "rev-parse", "HEAD").strip() == target
    assert _git(repo, "status", "--short") == ""
    assert (repo / "tracked.txt").read_text() == "candidate\n"
    assert not (repo / "untracked.txt").exists()
