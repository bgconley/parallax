import subprocess
import tarfile
from pathlib import Path

from scripts.snapshot_gpu_checkout import snapshot_checkout


def _git(repo: Path, *args: str) -> None:
    import subprocess

    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


def test_snapshot_checkout_preserves_dirty_state_without_secret_payloads(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    tracked = repo / "tracked.txt"
    tracked.write_text("before\n")
    _git(repo, "add", "tracked.txt")
    _git(repo, "commit", "-m", "initial")

    tracked.write_text("after\n")
    (repo / "safe-note.txt").write_text("safe untracked evidence\n")
    (repo / ".env").write_text("DATABASE_URL=postgresql://user:secret@example/db\n")
    secret_dir = repo / ".phase11_evidence" / "secrets"
    secret_dir.mkdir(parents=True)
    (secret_dir / "uat_bearer.jwt").write_text("secret-jwt")
    (repo / "private.pem").write_text("secret-key")

    snapshot = snapshot_checkout(
        repo=repo,
        snapshot_root=tmp_path / "snapshots",
        label="gpu_dirty",
        timestamp="20260604T000000Z",
    )

    assert (snapshot / "head.txt").read_text().strip()
    assert "tracked.txt" in (snapshot / "status.txt").read_text()
    assert "after" in (snapshot / "worktree.patch").read_text()
    assert "safe-note.txt" in (snapshot / "untracked_sanitized_files.txt").read_text()
    assert "uat_bearer.jwt" not in (snapshot / "untracked_sanitized_files.txt").read_text()
    assert "private.pem" not in (snapshot / "untracked_sanitized_files.txt").read_text()
    assert "excluded_untracked_files=3" in (snapshot / "snapshot_manifest.txt").read_text()
    assert (snapshot / "checksums.sha256").read_text().count("  ") >= 2

    with tarfile.open(snapshot / "untracked_sanitized.tgz", "r:gz") as archive:
        names = set(archive.getnames())

    assert "safe-note.txt" in names
    assert ".env" not in names
    assert ".phase11_evidence/secrets/uat_bearer.jwt" not in names
    assert "private.pem" not in names


def test_snapshot_cli_reports_missing_repo_without_traceback(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            "python",
            "scripts/snapshot_gpu_checkout.py",
            "--repo",
            str(tmp_path / "missing"),
            "--snapshot-root",
            str(tmp_path / "snapshots"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "snapshot failed:" in result.stderr
    assert "Traceback" not in result.stderr
