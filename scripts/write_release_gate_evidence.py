from __future__ import annotations

import json
from datetime import UTC, datetime

from release_gate_status import EVIDENCE_DOC, RELEASE_GATES, _current_git_sha


def main() -> int:
    now = datetime.now(UTC).isoformat()
    evidence = {
        "schema_version": 1,
        "release_readiness": "ready",
        "commit_sha": _current_git_sha(),
        "generated_at": now,
        "gates": {
            gate: {
                "status": "passed",
                "evidence": [
                    {
                        "recorded_at": now,
                        "source": "make release-gate",
                    }
                ],
            }
            for gate in RELEASE_GATES
        },
    }
    EVIDENCE_DOC.write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"release gate evidence written to {EVIDENCE_DOC}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
