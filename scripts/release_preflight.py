from __future__ import annotations

import argparse
import os
import subprocess  # nosec B404
from collections.abc import Mapping

from release_gate_status import REPO_ROOT, _current_git_sha

CheckMap = dict[str, dict[str, str]]
PARITY_SCRIPT = REPO_ROOT / "scripts/verify_gpu_commit_parity.sh"

FIREBASE_RELEASE_INPUTS = (
    "PARALLAX_FIREBASE_WEB_API_KEY",
    "PARALLAX_RELEASE_FIREBASE_EMAIL",
    "PARALLAX_RELEASE_FIREBASE_PASSWORD",
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check release-gate prerequisites without printing secret values."
    )
    parser.add_argument("--expected-sha", default=None)
    parser.add_argument(
        "--skip-gpu",
        action="store_true",
        help="Skip the read-only deployed commit parity check.",
    )
    args = parser.parse_args()

    checks = evaluate_environment(os.environ)
    if not args.skip_gpu:
        checks["deployed_commit_parity"] = check_deployed_commit_parity(
            args.expected_sha or _current_git_sha()
        )
    print(render_checks(checks))
    return 1 if any(check["status"] == "blocked" for check in checks.values()) else 0


def evaluate_environment(environ: Mapping[str, str]) -> CheckMap:
    checks: CheckMap = {
        "production_auth_provider": _auth_provider_check(environ),
        "release_app_check": _app_check(environ),
        "release_api_url": _presence_or_default(
            environ,
            "PARALLAX_API_URL",
            "the local API URL default",
        ),
        "release_database_url": _presence_or_default(
            environ,
            "PARALLAX_HOST_DATABASE_URL",
            "the local host database URL default",
        ),
        "release_object_root": _presence_or_default(
            environ,
            "PARALLAX_OBJECTS_DIR",
            "the standard object-root default",
        ),
        "release_restore_root": _presence_or_default(
            environ,
            "PARALLAX_RESTORE_DRILL_ROOT",
            "the standard restore-drill root default",
        ),
    }
    return checks


def check_deployed_commit_parity(expected_sha: str) -> dict[str, str]:
    result = subprocess.run(
        [str(PARITY_SCRIPT), expected_sha],
        check=False,
        capture_output=True,
        text=True,
    )  # nosec B603
    if result.returncode == 0:
        return {"status": "ready", "detail": "GPU deployment checkout matches release SHA"}
    detail = _first_output_line(result.stderr) or _first_output_line(result.stdout)
    return {
        "status": "blocked",
        "detail": detail or "scripts/verify_gpu_commit_parity.sh failed",
    }


def render_checks(checks: CheckMap) -> str:
    has_blocker = any(check["status"] == "blocked" for check in checks.values())
    overall = "blocked" if has_blocker else "ready"
    lines = [f"release preflight: {overall}"]
    for name, check in checks.items():
        lines.append(f"- {name}: {check['status']} - {check['detail']}")
    return "\n".join(lines)


def _auth_provider_check(environ: Mapping[str, str]) -> dict[str, str]:
    if _is_set(environ, "PARALLAX_RELEASE_BEARER_TOKEN"):
        return {
            "status": "ready",
            "detail": "PARALLAX_RELEASE_BEARER_TOKEN is set",
        }
    if all(_is_set(environ, key) for key in FIREBASE_RELEASE_INPUTS):
        return {
            "status": "ready",
            "detail": "Firebase release token mint inputs are set",
        }
    return {
        "status": "blocked",
        "detail": (
            "set PARALLAX_RELEASE_BEARER_TOKEN or all of "
            + ", ".join(FIREBASE_RELEASE_INPUTS)
        ),
    }


def _app_check(environ: Mapping[str, str]) -> dict[str, str]:
    mode = environ.get("PARALLAX_FIREBASE_APP_CHECK_MODE", "").casefold()
    if mode == "enforce" and not _is_set(environ, "PARALLAX_RELEASE_APP_CHECK_TOKEN"):
        return {
            "status": "blocked",
            "detail": "PARALLAX_RELEASE_APP_CHECK_TOKEN is required when App Check is enforced",
        }
    if mode == "enforce":
        return {
            "status": "ready",
            "detail": "PARALLAX_RELEASE_APP_CHECK_TOKEN is set for App Check enforce mode",
        }
    return {
        "status": "ready",
        "detail": "App Check release token is not required by current mode",
    }


def _presence_or_default(
    environ: Mapping[str, str],
    key: str,
    default_label: str,
) -> dict[str, str]:
    if _is_set(environ, key):
        return {"status": "ready", "detail": f"{key} is set"}
    return {
        "status": "warning",
        "detail": f"{key} is unset; release-gate will use {default_label}",
    }


def _is_set(environ: Mapping[str, str], key: str) -> bool:
    return bool(environ.get(key))


def _first_output_line(output: str) -> str:
    return next((line.strip() for line in output.splitlines() if line.strip()), "")


if __name__ == "__main__":
    raise SystemExit(main())
