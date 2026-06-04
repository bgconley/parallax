import hashlib
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
    assert "release-preflight:" in makefile
    assert "scripts/release_preflight.py" in makefile
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


def test_release_preflight_requires_release_auth_inputs_without_leaking_values() -> None:
    script = _load_script("release_preflight", "release_preflight.py")

    missing = script.evaluate_environment({})
    rendered_missing = script.render_checks(missing)

    assert missing["production_auth_provider"]["status"] == "blocked"
    assert "PARALLAX_RELEASE_BEARER_TOKEN" in rendered_missing
    assert "PARALLAX_FIREBASE_WEB_API_KEY" in rendered_missing
    assert "PARALLAX_RELEASE_FIREBASE_EMAIL" in rendered_missing
    assert "PARALLAX_RELEASE_FIREBASE_PASSWORD" in rendered_missing
    assert "parallax_dev_password" not in rendered_missing

    ready = script.evaluate_environment({"PARALLAX_RELEASE_BEARER_TOKEN": "secret-token"})
    rendered_ready = script.render_checks(ready)

    assert ready["production_auth_provider"]["status"] == "ready"
    assert "secret-token" not in rendered_ready


def test_release_preflight_requires_app_check_token_when_enforced() -> None:
    script = _load_script("release_preflight", "release_preflight.py")

    checks = script.evaluate_environment(
        {
            "PARALLAX_RELEASE_BEARER_TOKEN": "secret-token",
            "PARALLAX_FIREBASE_APP_CHECK_MODE": "enforce",
        }
    )

    assert checks["release_app_check"]["status"] == "blocked"
    assert "PARALLAX_RELEASE_APP_CHECK_TOKEN" in script.render_checks(checks)


def test_release_preflight_uses_repo_root_parity_script() -> None:
    script = _load_script("release_preflight", "release_preflight.py")

    assert script.PARITY_SCRIPT == REPO_ROOT / "scripts/verify_gpu_commit_parity.sh"


def test_release_preflight_formats_local_checkout_parity() -> None:
    script = _load_script("release_preflight", "release_preflight.py")

    assert script.checkout_parity_status(
        expected_sha="abc123",
        actual_sha="abc123",
        dirty_status="",
    ) == {"status": "ready", "detail": "GPU deployment checkout matches release SHA"}
    assert script.checkout_parity_status(
        expected_sha="abc123",
        actual_sha="def456",
        dirty_status="",
    ) == {
        "status": "blocked",
        "detail": "GPU checkout mismatch: expected abc123, got def456",
    }
    assert script.checkout_parity_status(
        expected_sha="abc123",
        actual_sha="abc123",
        dirty_status=" M services/api/example.py",
    ) == {"status": "blocked", "detail": "GPU checkout is dirty"}
    assert script.checkout_parity_status(
        expected_sha="abc123",
        actual_sha="def456",
        dirty_status=" M services/api/example.py",
    ) == {
        "status": "blocked",
        "detail": "GPU checkout mismatch: expected abc123, got def456; GPU checkout is dirty",
    }


def test_release_proof_defaults_are_repo_root_relative() -> None:
    status = _load_script("release_gate_status", "release_gate_status.py")
    writer = _load_script("write_release_gate_evidence", "write_release_gate_evidence.py")
    cleaner = _load_script("clear_release_gate_proofs", "clear_release_gate_proofs.py")
    recorder = _load_script("record_release_gate", "record_release_gate.py")

    expected = REPO_ROOT / ".release-gate-proofs"

    assert status.DEFAULT_PROOF_DIR == expected
    assert writer.DEFAULT_PROOF_DIR == expected
    assert cleaner.DEFAULT_PROOF_DIR == expected
    assert recorder.DEFAULT_PROOF_DIR == expected


def test_release_evidence_writer_builds_from_structured_proofs(tmp_path: Path) -> None:
    script = _load_script("write_release_gate_evidence", "write_release_gate_evidence.py")
    status = _load_script("release_gate_status", "release_gate_status.py")
    for gate in status.RELEASE_GATES:
        proof_payload = {
            "schema_version": 1,
            "gate": gate,
            "status": "passed",
            "commit_sha": "sha",
            "recorded_at": "2026-04-30T00:00:00+00:00",
            "command": ["uv", "run", "python", "scripts/probe.py"],
        }
        (tmp_path / f"{gate}.json").write_text(json.dumps(proof_payload))

    evidence = script.build_release_evidence(tmp_path, current_sha="sha")

    assert evidence["release_readiness"] == "ready"
    assert evidence["commit_sha"] == "sha"
    for gate in status.RELEASE_GATES:
        proof_bytes = (tmp_path / f"{gate}.json").read_bytes()
        gate_evidence = evidence["gates"][gate]
        assert gate_evidence["status"] == "passed"
        assert gate_evidence["evidence"][0]["source"] == "structured_release_proof"
        assert gate_evidence["evidence"][0]["command"] == [
            "uv",
            "run",
            "python",
            "scripts/probe.py",
        ]
        assert gate_evidence["evidence"][0]["proof_sha256"] == hashlib.sha256(
            proof_bytes
        ).hexdigest()


def test_release_gate_status_requires_matching_proof_file_hash(tmp_path: Path) -> None:
    script = _load_script("release_gate_status", "release_gate_status.py")
    proof_path = tmp_path / "backup_restore.json"
    proof_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "gate": "backup_restore",
                "status": "passed",
                "commit_sha": "sha",
                "recorded_at": "2026-04-30T00:00:00+00:00",
                "command": ["uv", "run", "python", "scripts/probe.py"],
            }
        )
    )
    good_hash = hashlib.sha256(proof_path.read_bytes()).hexdigest()

    def evidence_with(proof_sha256: str) -> dict[str, object]:
        return {
            "commit_sha": "sha",
            "gates": {
                "backup_restore": {
                    "status": "passed",
                    "evidence": [
                        {
                            "recorded_at": "2026-04-30T00:00:00+00:00",
                            "source": "structured_release_proof",
                            "command": ["uv", "run", "python", "scripts/probe.py"],
                            "proof_file": "backup_restore.json",
                            "proof_sha256": proof_sha256,
                        }
                    ],
                }
            },
        }

    assert (
        script._gate_status(
            evidence_with(good_hash),
            "backup_restore",
            "sha",
            proof_dir=tmp_path,
        )
        == "passed"
    )

    proof_path.write_text("tampered proof")
    assert (
        script._gate_status(
            evidence_with(good_hash),
            "backup_restore",
            "sha",
            proof_dir=tmp_path,
        )
        == "proof-mismatch"
    )
    proof_path.unlink()
    assert (
        script._gate_status(
            evidence_with(good_hash),
            "backup_restore",
            "sha",
            proof_dir=tmp_path,
        )
        == "missing-proof"
    )


def test_release_gate_status_rejects_hash_matched_stale_proof_file(
    tmp_path: Path,
) -> None:
    script = _load_script("release_gate_status", "release_gate_status.py")
    proof_path = tmp_path / "backup_restore.json"
    proof_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "gate": "backup_restore",
                "status": "passed",
                "commit_sha": "old-sha",
                "recorded_at": "2026-04-30T00:00:00+00:00",
                "command": ["uv", "run", "python", "scripts/probe.py"],
            }
        )
    )
    proof_hash = hashlib.sha256(proof_path.read_bytes()).hexdigest()
    evidence = {
        "commit_sha": "sha",
        "gates": {
            "backup_restore": {
                "status": "passed",
                "evidence": [
                    {
                        "recorded_at": "2026-04-30T00:00:00+00:00",
                        "source": "structured_release_proof",
                        "command": ["uv", "run", "python", "scripts/probe.py"],
                        "proof_file": "backup_restore.json",
                        "proof_sha256": proof_hash,
                    }
                ],
            }
        },
    }

    assert (
        script._gate_status(
            evidence,
            "backup_restore",
            "sha",
            proof_dir=tmp_path,
        )
        == "stale-proof"
    )


def test_release_gate_status_rejects_hash_matched_malformed_proof_file(
    tmp_path: Path,
) -> None:
    script = _load_script("release_gate_status", "release_gate_status.py")
    proof_path = tmp_path / "backup_restore.json"
    proof_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "gate": "backup_restore",
                "status": "passed",
                "commit_sha": "sha",
                "recorded_at": "2026-04-30T00:00:00+00:00",
            }
        )
    )
    proof_hash = hashlib.sha256(proof_path.read_bytes()).hexdigest()
    evidence = {
        "commit_sha": "sha",
        "gates": {
            "backup_restore": {
                "status": "passed",
                "evidence": [
                    {
                        "recorded_at": "2026-04-30T00:00:00+00:00",
                        "source": "structured_release_proof",
                        "command": ["uv", "run", "python", "scripts/probe.py"],
                        "proof_file": "backup_restore.json",
                        "proof_sha256": proof_hash,
                    }
                ],
            }
        },
    }

    assert (
        script._gate_status(
            evidence,
            "backup_restore",
            "sha",
            proof_dir=tmp_path,
        )
        == "malformed-proof"
    )


def test_release_gate_status_rejects_missing_proof_hash() -> None:
    script = _load_script("release_gate_status", "release_gate_status.py")

    evidence = {
        "commit_sha": "sha",
        "gates": {
            "backup_restore": {
                "status": "passed",
                "evidence": [
                    {
                        "recorded_at": "2026-04-30T00:00:00+00:00",
                        "source": "structured_release_proof",
                        "command": ["uv", "run", "python", "scripts/probe.py"],
                        "proof_file": "backup_restore.json",
                    }
                ],
            }
        },
    }

    assert script._gate_status(evidence, "backup_restore", "sha") == "malformed-evidence"


def test_release_gate_status_rejects_malformed_passed_evidence() -> None:
    script = _load_script("release_gate_status", "release_gate_status.py")

    evidence = {
        "commit_sha": "sha",
        "gates": {
            "backup_restore": {
                "status": "passed",
                "evidence": ["not a structured proof reference"],
            }
        },
    }

    assert script._gate_status(evidence, "backup_restore", "sha") == "malformed-evidence"


def test_release_gate_status_requires_gate_scoped_proof_reference() -> None:
    script = _load_script("release_gate_status", "release_gate_status.py")

    def evidence_with(proof_file: str) -> dict[str, object]:
        return {
            "commit_sha": "sha",
            "gates": {
                "backup_restore": {
                    "status": "passed",
                    "evidence": [
                        {
                            "recorded_at": "2026-04-30T00:00:00+00:00",
                            "source": "structured_release_proof",
                            "command": ["uv", "run", "python", "scripts/probe.py"],
                            "proof_file": proof_file,
                        }
                    ],
                }
            },
        }

    assert (
        script._gate_status(evidence_with("performance_slo.json"), "backup_restore", "sha")
        == "malformed-evidence"
    )
    assert (
        script._gate_status(evidence_with("../backup_restore.json"), "backup_restore", "sha")
        == "malformed-evidence"
    )


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
