#!/usr/bin/env python3
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "MANIFEST.txt"

def digest(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()

def main() -> None:
    rows = []
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and path.name != "MANIFEST.txt":
            rel = path.relative_to(ROOT).as_posix()
            rows.append((rel, path.stat().st_size, digest(path)))
    with MANIFEST.open("w", encoding="utf-8") as f:
        f.write("# Parallax v1.3 artifact manifest\n")
        f.write("# path | size_bytes | sha256\n")
        for rel, size, sha in rows:
            f.write(f"{rel} | {size} | {sha}\n")

if __name__ == "__main__":
    main()
