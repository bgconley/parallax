from __future__ import annotations

import argparse
import os
from pathlib import Path

from release_gate_status import RELEASE_GATES

DEFAULT_PROOF_DIR = Path(os.getenv("PARALLAX_RELEASE_PROOF_DIR", ".release-gate-proofs"))
REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Clear Parallax release gate proof files safely.")
    parser.add_argument("--proof-dir", type=Path, default=DEFAULT_PROOF_DIR)
    args = parser.parse_args()

    try:
        clear_release_proofs(args.proof_dir)
    except RuntimeError as exc:
        print(f"release proof cleanup failed: {exc}")
        return 1
    print(f"release proof files cleared from {args.proof_dir}")
    return 0


def clear_release_proofs(proof_dir: Path) -> None:
    resolved = proof_dir.expanduser().resolve()
    dangerous_paths = {
        Path("/").resolve(),
        Path.home().resolve(),
        REPO_ROOT.resolve(),
    }
    if resolved in dangerous_paths:
        raise RuntimeError(f"refusing to clear release proofs from dangerous path: {proof_dir}")
    if resolved.exists() and not resolved.is_dir():
        raise RuntimeError(f"release proof path is not a directory: {proof_dir}")

    resolved.mkdir(parents=True, exist_ok=True)
    for gate in RELEASE_GATES:
        (resolved / f"{gate}.json").unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
