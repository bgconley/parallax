from __future__ import annotations

import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
STATUS_DOC = REPO_ROOT / "docs/release/release_gate_status.md"

BLOCKED_GATES = (
    "backup_restore",
    "privacy_export_delete_redact",
    "performance_slo",
    "production_auth_provider",
    "production_log_privacy_scan",
    "phase5_plus_workflows",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Report Parallax release gate status.")
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print gate status without failing when blockers remain.",
    )
    args = parser.parse_args()

    content = STATUS_DOC.read_text()
    print("release readiness: blocked")
    for gate in BLOCKED_GATES:
        if gate not in content:
            print(f"missing gate record: {gate}")
            return 2
        print(f"- {gate}: blocked")
    return 0 if args.summary else 1


if __name__ == "__main__":
    raise SystemExit(main())
