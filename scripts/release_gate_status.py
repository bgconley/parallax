from __future__ import annotations

import argparse
import json
import shutil
import subprocess  # nosec B404
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DOC = REPO_ROOT / "docs/release/release_gate_evidence.json"

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
    args = parser.parse_args()

    evidence = _load_evidence()
    current_sha = _current_git_sha()
    statuses = {gate: _gate_status(evidence, gate, current_sha) for gate in RELEASE_GATES}
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


def _gate_status(evidence: dict[str, object], gate: str, current_sha: str) -> str:
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
