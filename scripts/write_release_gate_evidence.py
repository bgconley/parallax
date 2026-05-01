from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from release_gate_status import EVIDENCE_DOC, RELEASE_GATES, _current_git_sha

DEFAULT_PROOF_DIR = Path(os.getenv("PARALLAX_RELEASE_PROOF_DIR", ".release-gate-proofs"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Write Parallax release gate evidence from structured proof artifacts."
    )
    parser.add_argument("--proof-dir", type=Path, default=DEFAULT_PROOF_DIR)
    args = parser.parse_args()

    try:
        evidence = build_release_evidence(args.proof_dir, current_sha=_current_git_sha())
    except RuntimeError as exc:
        print(f"release gate evidence not written: {exc}")
        return 1
    EVIDENCE_DOC.write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"release gate evidence written to {EVIDENCE_DOC}")
    return 0


def build_release_evidence(proof_dir: Path, *, current_sha: str) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    proofs = {gate: _load_gate_proof(proof_dir, gate, current_sha) for gate in RELEASE_GATES}
    return {
        "schema_version": 1,
        "release_readiness": "ready",
        "commit_sha": current_sha,
        "generated_at": now,
        "gates": {
            gate: {
                "status": "passed",
                "evidence": [
                    {
                        "recorded_at": proofs[gate]["recorded_at"],
                        "source": "structured_release_proof",
                        "command": proofs[gate]["command"],
                        "proof_file": f"{gate}.json",
                    }
                ],
            }
            for gate in RELEASE_GATES
        },
    }


def _load_gate_proof(proof_dir: Path, gate: str, current_sha: str) -> dict[str, Any]:
    proof_path = proof_dir / f"{gate}.json"
    if not proof_path.exists():
        raise RuntimeError(f"missing release proof for {gate}: {proof_path}")
    try:
        proof = json.loads(proof_path.read_text())
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid release proof JSON for {gate}") from exc
    if not isinstance(proof, dict):
        raise RuntimeError(f"invalid release proof object for {gate}")
    if proof.get("schema_version") != 1:
        raise RuntimeError(f"invalid release proof schema for {gate}")
    if proof.get("gate") != gate:
        raise RuntimeError(f"release proof gate mismatch for {gate}")
    if proof.get("status") != "passed":
        raise RuntimeError(f"release proof did not pass for {gate}")
    if proof.get("commit_sha") != current_sha:
        raise RuntimeError(f"stale release proof for {gate}")
    if not isinstance(proof.get("recorded_at"), str) or not proof["recorded_at"]:
        raise RuntimeError(f"release proof missing recorded_at for {gate}")
    command = proof.get("command")
    if not isinstance(command, list) or not command or not all(
        isinstance(part, str) for part in command
    ):
        raise RuntimeError(f"release proof missing command for {gate}")
    return proof


if __name__ == "__main__":
    raise SystemExit(main())
