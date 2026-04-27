from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PACKAGE_ROOT = REPO_ROOT / "packages" / "db"
if str(DB_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(DB_PACKAGE_ROOT))

from parallax_db.runner import apply_baseline_migrations, run_schema_smoke_checks  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply Parallax baseline SQL migrations.")
    parser.add_argument(
        "--database-url",
        default=os.environ.get("PARALLAX_DATABASE_URL"),
        help="PostgreSQL URL. Defaults to PARALLAX_DATABASE_URL.",
    )
    parser.add_argument(
        "--migrations-dir",
        type=Path,
        default=Path("migrations"),
        help="Directory containing baseline SQL migrations.",
    )
    parser.add_argument("--smoke", action="store_true", help="Run Phase 0 schema smoke checks.")
    args = parser.parse_args()

    if not args.database_url:
        parser.error("--database-url or PARALLAX_DATABASE_URL is required")

    applied = apply_baseline_migrations(args.database_url, args.migrations_dir)
    for migration in applied:
        print(f"applied {migration.name}")

    if args.smoke:
        failures = run_schema_smoke_checks(args.database_url)
        if failures:
            for failure in failures:
                print(f"missing {failure}")
            return 1
        print("schema smoke checks passed")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
