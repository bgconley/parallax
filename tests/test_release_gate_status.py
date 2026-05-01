import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script(module_name: str, script_name: str) -> Any:
    scripts_dir = REPO_ROOT / "scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(module_name, scripts_dir / script_name)
        assert spec is not None
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(scripts_dir))


def test_release_gate_status_records_verified_release_gates() -> None:
    evidence_doc = REPO_ROOT / "docs/release/release_gate_evidence.json"
    content = json.loads(evidence_doc.read_text())

    assert content["release_readiness"] == "blocked"
    assert content["gates"]["backup_restore"]["status"] == "proof-required"
    assert content["gates"]["privacy_export_delete_redact"]["status"] == "proof-required"
    assert content["gates"]["performance_slo"]["status"] == "proof-required"
    assert content["gates"]["production_auth_provider"]["status"] == "proof-required"
    assert content["gates"]["production_log_privacy_scan"]["status"] == "proof-required"


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
    assert "scripts/write_release_gate_evidence.py" in release_gate_section


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


def test_release_status_uses_evidence_file_not_markdown_status_text() -> None:
    script = (REPO_ROOT / "scripts/release_gate_status.py").read_text()

    assert "release_gate_evidence.json" in script
    assert "release_gate_status.md" not in script
    assert "_current_git_sha" in script


def test_release_gate_writes_evidence_only_after_proof_commands() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text()
    release_gate_section = makefile.split("release-gate:", 1)[1].split("\n\n", 1)[0]

    assert "scripts/clear_release_gate_proofs.py" in release_gate_section
    assert 'rm -rf "$(RELEASE_PROOF_DIR)"' not in release_gate_section

    gates = [
        "deployed_commit_parity",
        "production_auth_provider",
        "privacy_export_delete_redact",
        "performance_slo",
        "production_log_privacy_scan",
        "backup_restore",
    ]
    for gate in gates:
        assert f"scripts/record_release_gate.py --gate {gate}" in release_gate_section

    assert release_gate_section.rfind("scripts/write_release_gate_evidence.py") > max(
        release_gate_section.rfind(f"scripts/record_release_gate.py --gate {gate}")
        for gate in gates
    )


def test_release_evidence_writer_requires_per_gate_proofs(tmp_path: Path) -> None:
    script = _load_script("write_release_gate_evidence", "write_release_gate_evidence.py")

    try:
        script.build_release_evidence(tmp_path, current_sha="sha")
    except RuntimeError as exc:
        assert "missing release proof" in str(exc)
    else:
        raise AssertionError("expected release evidence writer to reject missing proofs")


def test_release_evidence_writer_builds_from_structured_proofs(tmp_path: Path) -> None:
    script = _load_script("write_release_gate_evidence", "write_release_gate_evidence.py")
    status = _load_script("release_gate_status", "release_gate_status.py")
    for gate in status.RELEASE_GATES:
        (tmp_path / f"{gate}.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "gate": gate,
                    "status": "passed",
                    "commit_sha": "sha",
                    "recorded_at": "2026-04-30T00:00:00+00:00",
                    "command": ["uv", "run", "python", "scripts/probe.py"],
                }
            )
        )

    evidence = script.build_release_evidence(tmp_path, current_sha="sha")

    assert evidence["release_readiness"] == "ready"
    assert evidence["commit_sha"] == "sha"
    for gate in status.RELEASE_GATES:
        gate_evidence = evidence["gates"][gate]
        assert gate_evidence["status"] == "passed"
        assert gate_evidence["evidence"][0]["source"] == "structured_release_proof"
        assert gate_evidence["evidence"][0]["command"] == [
            "uv",
            "run",
            "python",
            "scripts/probe.py",
        ]


def test_release_gate_recorder_redacts_sensitive_arguments() -> None:
    script = _load_script("record_release_gate", "record_release_gate.py")

    sanitized = script.sanitize_command(
        [
            "uv",
            "run",
            "python",
            "scripts/probe.py",
            "--bearer-token",
            "raw-token",
            "--database-url",
            "postgresql://user:password@localhost/db",
            "--app-check-token=raw-app-check",
        ]
    )

    rendered = json.dumps(sanitized)
    assert "raw-token" not in rendered
    assert "password" not in rendered
    assert "raw-app-check" not in rendered
    assert "<redacted>" in rendered


def test_release_gate_proof_cleanup_rejects_dangerous_paths() -> None:
    script = _load_script("clear_release_gate_proofs", "clear_release_gate_proofs.py")

    for path in (Path("/"), REPO_ROOT, Path.home()):
        try:
            script.clear_release_proofs(path)
        except RuntimeError as exc:
            assert "refusing to clear release proofs" in str(exc)
        else:
            raise AssertionError(f"expected cleanup to reject {path}")
