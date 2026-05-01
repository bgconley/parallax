from __future__ import annotations

import argparse
import json
import os
import re
import subprocess  # nosec B404
from datetime import UTC, datetime
from pathlib import Path

from release_gate_status import RELEASE_GATES, _current_git_sha

DEFAULT_PROOF_DIR = Path(os.getenv("PARALLAX_RELEASE_PROOF_DIR", ".release-gate-proofs"))
SENSITIVE_FLAGS = {
    "--app-check-token",
    "--bearer-token",
    "--database-url",
    "--password",
    "--web-api-key",
}
USERINFO_PATTERN = re.compile(r"://([^:/@\s]+):([^/@\s]+)@")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run and record a Parallax release gate proof.")
    parser.add_argument("--gate", required=True, choices=RELEASE_GATES)
    parser.add_argument("--proof-dir", type=Path, default=DEFAULT_PROOF_DIR)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("release gate command is required after --")

    proof_path = args.proof_dir / f"{args.gate}.json"
    proof_path.unlink(missing_ok=True)
    result = subprocess.run(command, check=False)  # nosec B603
    if result.returncode != 0:
        proof_path.unlink(missing_ok=True)
        return result.returncode

    args.proof_dir.mkdir(parents=True, exist_ok=True)
    proof = {
        "schema_version": 1,
        "gate": args.gate,
        "status": "passed",
        "commit_sha": _current_git_sha(),
        "recorded_at": datetime.now(UTC).isoformat(),
        "command": sanitize_command(command),
    }
    proof_path.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"release gate proof written: {proof_path}")
    return 0


def sanitize_command(command: list[str]) -> list[str]:
    sanitized: list[str] = []
    redact_next = False
    for arg in command:
        if redact_next:
            sanitized.append("<redacted>")
            redact_next = False
            continue
        if arg in SENSITIVE_FLAGS:
            sanitized.append(arg)
            redact_next = True
            continue
        flag, separator, value = arg.partition("=")
        if separator and flag in SENSITIVE_FLAGS:
            sanitized.append(f"{flag}=<redacted>")
            continue
        sanitized.append(_sanitize_value(arg))
    return sanitized


def _sanitize_value(value: str) -> str:
    lower = value.casefold()
    if "token" in lower and not value.startswith("--"):
        return "<redacted>"
    return USERINFO_PATTERN.sub(r"://<redacted>:<redacted>@", value)


if __name__ == "__main__":
    raise SystemExit(main())
