from __future__ import annotations

from pathlib import Path

BASELINE_MIGRATION_PREFIXES = (
    "0001",
    "0002",
    "0003",
    "0004",
    "0005",
    "0006",
    "0008",
    "0011",
    "0014",
)


def discover_baseline_migrations(migrations_dir: Path) -> list[Path]:
    """Return ordered baseline migrations, excluding optional extension profiles."""
    root = migrations_dir.resolve()
    if not root.exists():
        return []

    discovered = {path.name[:4]: path for path in root.glob("*.sql")}
    return [discovered[prefix] for prefix in BASELINE_MIGRATION_PREFIXES if prefix in discovered]
