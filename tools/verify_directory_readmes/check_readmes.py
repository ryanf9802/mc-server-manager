#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCOPES = ("docs", "src", "tests", "tools")
IGNORED_NAMES = {".git", "__pycache__", ".pytest_cache", ".venv"}


def main() -> int:
    missing: list[Path] = []

    for scope in SCOPES:
        scope_root = ROOT / scope
        if not scope_root.exists():
            continue

        if not (scope_root / "README.md").exists():
            missing.append(scope_root.relative_to(ROOT))

        for directory in sorted(path for path in scope_root.rglob("*") if path.is_dir()):
            if directory.name in IGNORED_NAMES:
                continue
            if not (directory / "README.md").exists():
                missing.append(directory.relative_to(ROOT))

    if missing:
        print("Missing README.md in:")
        for directory in missing:
            print(f" - {directory}")
        return 1

    print("All tracked documentation scopes contain README.md files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
