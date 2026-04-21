from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if platform.system() != "Windows":
        print(
            "Windows builds must be produced on Windows. Run this script from a Windows shell.",
            file=sys.stderr,
        )
        return 1

    repo_root = Path(__file__).resolve().parents[2]
    dist_path = repo_root / "dist" / "windows-single"
    work_path = repo_root / "build" / "pyinstaller"
    spec_path = repo_root / "tools" / "packaging" / "mc_server_manager.spec"

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--distpath",
        str(dist_path),
        "--workpath",
        str(work_path),
        str(spec_path),
    ]

    subprocess.run(command, check=True, cwd=repo_root)

    exe_path = dist_path / "mc-server-manager.exe"
    print(f"Built {exe_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
