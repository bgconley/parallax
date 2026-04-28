import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_release_gate_status_records_non_phase4_release_blockers() -> None:
    status_doc = REPO_ROOT / "docs/release/release_gate_status.md"
    content = status_doc.read_text()

    assert "release readiness: blocked" in content
    assert "backup_restore" in content
    assert "privacy_export_delete_redact" in content
    assert "performance_slo" in content
    assert "phase5_plus_workflows" in content
    assert "No Phase 5 endpoint or workflow is implemented by this gate" in content


def test_release_gate_summary_command_is_available() -> None:
    result = subprocess.run(
        ["uv", "run", "python", "scripts/release_gate_status.py", "--summary"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "release readiness: blocked" in result.stdout
    assert "backup_restore" in result.stdout


def test_release_gate_commands_are_available_from_makefile() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text()

    assert "release-status:" in makefile
    assert "release-gate:" in makefile
    assert "scripts/release_gate_status.py --summary" in makefile
    assert "scripts/release_gate_status.py" in makefile


def test_release_gate_command_fails_when_blockers_remain() -> None:
    result = subprocess.run(
        ["uv", "run", "python", "scripts/release_gate_status.py"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "release readiness: blocked" in result.stdout
