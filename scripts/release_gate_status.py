from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess  # nosec B404
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DOC = REPO_ROOT / "docs/release/release_gate_evidence.json"
DEFAULT_PROOF_DIR = REPO_ROOT / os.getenv(
    "PARALLAX_RELEASE_PROOF_DIR",
    ".release-gate-proofs",
)

RELEASE_GATES = (
    "backup_restore",
    "privacy_export_delete_redact",
    "performance_slo",
    "production_auth_provider",
    "production_log_privacy_scan",
    "deployed_commit_parity",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Report Parallax release gate status.")
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print gate status without failing when blockers remain.",
    )
    parser.add_argument("--proof-dir", type=Path, default=DEFAULT_PROOF_DIR)
    args = parser.parse_args()

    evidence = _load_evidence()
    current_sha = _current_git_sha()
    statuses = {
        gate: _gate_status(evidence, gate, current_sha, proof_dir=args.proof_dir)
        for gate in RELEASE_GATES
    }
    ready = (
        evidence.get("release_readiness") == "ready"
        and evidence.get("commit_sha") == current_sha
        and all(status == "passed" for status in statuses.values())
    )

    if not ready:
        print("release readiness: blocked")
        for gate, status in statuses.items():
            print(f"- {gate}: {status}")
        return 1 if not args.summary else 0

    print("release readiness: ready")
    for gate in RELEASE_GATES:
        print(f"- {gate}: passed")
    return 0


def _load_evidence() -> dict[str, object]:
    if not EVIDENCE_DOC.exists():
        return {}
    loaded = json.loads(EVIDENCE_DOC.read_text())
    return loaded if isinstance(loaded, dict) else {}


def _gate_status(
    evidence: dict[str, object],
    gate: str,
    current_sha: str,
    *,
    proof_dir: Path = DEFAULT_PROOF_DIR,
) -> str:
    raw_gates = evidence.get("gates", {})
    if not isinstance(raw_gates, dict) or gate not in raw_gates:
        return "missing"
    raw_gate = raw_gates[gate]
    if not isinstance(raw_gate, dict):
        return "invalid"
    status = raw_gate.get("status")
    if status != "passed":
        return str(status or "not passed")
    if evidence.get("commit_sha") != current_sha:
        return "stale"
    evidence_items = raw_gate.get("evidence")
    if not isinstance(evidence_items, list) or not evidence_items:
        return "missing-evidence"
    for item in evidence_items:
        if not _is_valid_evidence_item(item, gate):
            return "malformed-evidence"
        proof_status = _proof_reference_status(
            item,
            proof_dir,
            gate=gate,
            current_sha=current_sha,
        )
        if proof_status != "passed":
            return proof_status
    return "passed"


def _is_valid_evidence_item(item: object, gate: str) -> bool:
    if not isinstance(item, dict):
        return False
    recorded_at = item.get("recorded_at")
    source = item.get("source")
    command = item.get("command")
    proof_file = item.get("proof_file")
    proof_sha256 = item.get("proof_sha256")
    return (
        isinstance(recorded_at, str)
        and bool(recorded_at)
        and source == "structured_release_proof"
        and isinstance(command, list)
        and bool(command)
        and all(isinstance(part, str) and bool(part) for part in command)
        and isinstance(proof_file, str)
        and proof_file == f"{gate}.json"
        and isinstance(proof_sha256, str)
        and len(proof_sha256) == 64
        and all(character in "0123456789abcdef" for character in proof_sha256)
    )


def _proof_reference_status(
    item: dict[str, object],
    proof_dir: Path,
    *,
    gate: str,
    current_sha: str,
) -> str:
    proof_file = item["proof_file"]
    proof_sha256 = item["proof_sha256"]
    proof_path = proof_dir / str(proof_file)
    if not proof_path.exists():
        return "missing-proof"
    proof_bytes = proof_path.read_bytes()
    actual_sha256 = hashlib.sha256(proof_bytes).hexdigest()
    if actual_sha256 != proof_sha256:
        return "proof-mismatch"
    try:
        proof = json.loads(proof_bytes)
    except json.JSONDecodeError:
        return "malformed-proof"
    if not isinstance(proof, dict):
        return "malformed-proof"
    if proof.get("schema_version") != 1:
        return "malformed-proof"
    if proof.get("gate") != gate:
        return "proof-gate-mismatch"
    if proof.get("status") != "passed":
        return "proof-not-passed"
    if proof.get("commit_sha") != current_sha:
        return "stale-proof"
    if not isinstance(proof.get("recorded_at"), str) or not proof["recorded_at"]:
        return "malformed-proof"
    command = proof.get("command")
    if not isinstance(command, list) or not command or not all(
        isinstance(part, str) and bool(part) for part in command
    ):
        return "malformed-proof"
    return "passed"


def _current_git_sha() -> str:
    git = shutil.which("git")
    if git is None:
        raise RuntimeError("git executable is required to report release status")
    result = subprocess.run(
        [git, "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )  # nosec B603
    return result.stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())
