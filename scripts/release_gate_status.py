from __future__ import annotations

import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
STATUS_DOC = REPO_ROOT / "docs/release/release_gate_status.md"

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

    content = STATUS_DOC.read_text()
    if "release readiness: ready" not in content:
        print("release readiness: blocked")
        for gate in RELEASE_GATES:
            if gate not in content:
                print(f"- {gate}: missing")
            elif f"`{gate}` | proof-required" in content:
                print(f"- {gate}: proof-required")
            elif f"`{gate}` | passed" in content:
                print(f"- {gate}: passed")
            else:
                print(f"- {gate}: not passed")
        return 1 if not args.summary else 0
    print("release readiness: ready")
    for gate in RELEASE_GATES:
        if gate not in content:
            print(f"missing gate record: {gate}")
            return 2
        if f"`{gate}` | passed" not in content:
            print(f"- {gate}: not passed")
            return 1 if not args.summary else 0
        print(f"- {gate}: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
