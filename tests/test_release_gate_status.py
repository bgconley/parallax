import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_release_gate_status_records_verified_release_gates() -> None:
    status_doc = REPO_ROOT / "docs/release/release_gate_status.md"
    content = status_doc.read_text()

    assert "release readiness: blocked" in content
    assert "backup_restore" in content
    assert "privacy_export_delete_redact" in content
    assert "performance_slo" in content
    assert "production_auth_provider" in content
    assert "production_log_privacy_scan" in content
    assert "| proof-required |" in content


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
    assert "backup_restore: proof-required" in result.stdout


def test_release_gate_commands_are_available_from_makefile() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text()

    assert "release-status:" in makefile
    assert "release-gate:" in makefile
    assert "scripts/release_gate_status.py --summary" in makefile
    release_gate_section = makefile.split("release-gate:", 1)[1].split("\n\n", 1)[0]
    assert "scripts/verify_gpu_commit_parity.sh" in release_gate_section
    assert "scripts/release_auth_provider_probe.py" in release_gate_section
    assert "scripts/privacy_lifecycle_smoke.py" in release_gate_section
    assert "scripts/release_slo_smoke.py" in release_gate_section
    assert "scripts/release_log_privacy_scan.py" in release_gate_section
    assert "scripts/release_backup_restore_drill.py" in release_gate_section


def test_release_status_summary_command_reads_machine_status() -> None:
    result = subprocess.run(
        ["uv", "run", "python", "scripts/release_gate_status.py", "--summary"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "release readiness: blocked" in result.stdout
