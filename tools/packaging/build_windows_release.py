from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


APP_EXE_NAME = "mc-server-manager.exe"
INSTALLER_EXE_NAME = "mc-server-manager-installer.exe"
BUNDLE_NAME = "mc-server-manager-windows-x64.zip"


def main() -> int:
    if platform.system() != "Windows":
        print(
            "Windows builds must be produced on Windows. Run this script from a Windows shell.",
            file=sys.stderr,
        )
        return 1

    repo_root = Path(__file__).resolve().parents[2]
    dist_path = repo_root / "dist" / "windows-release"
    work_root = repo_root / "build" / "pyinstaller"
    bundle_dir = dist_path / "bundle"
    build_info_path = work_root / "build-info.json"

    shutil.rmtree(dist_path, ignore_errors=True)
    shutil.rmtree(work_root, ignore_errors=True)
    dist_path.mkdir(parents=True, exist_ok=True)
    work_root.mkdir(parents=True, exist_ok=True)

    build_info = _build_info(repo_root)
    build_info_path.write_text(json.dumps(build_info, indent=2), encoding="utf-8")

    _run_pyinstaller(
        repo_root,
        dist_path,
        work_root / "app",
        build_info_path,
        APP_EXE_NAME.removesuffix(".exe"),
        repo_root / "src" / "mc_server_manager" / "main.py",
    )
    _run_pyinstaller(
        repo_root,
        dist_path,
        work_root / "installer",
        build_info_path,
        INSTALLER_EXE_NAME.removesuffix(".exe"),
        repo_root / "src" / "mc_server_manager" / "installer_main.py",
    )

    bundle_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(dist_path / APP_EXE_NAME, bundle_dir / APP_EXE_NAME)
    shutil.copy2(dist_path / INSTALLER_EXE_NAME, bundle_dir / INSTALLER_EXE_NAME)
    shutil.copy2(build_info_path, bundle_dir / "build-info.json")

    bundle_path = dist_path / BUNDLE_NAME
    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(bundle_dir.iterdir()):
            archive.write(path, arcname=path.name)

    checksum_path = dist_path / "SHA256SUMS.txt"
    checksum_lines = [
        f"{_sha256(dist_path / INSTALLER_EXE_NAME)}  {INSTALLER_EXE_NAME}",
        f"{_sha256(bundle_path)}  {bundle_path.name}",
    ]
    checksum_path.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")

    print(f"Built {dist_path / INSTALLER_EXE_NAME}")
    print(f"Built {bundle_path}")
    print(f"Built {checksum_path}")
    return 0


def _run_pyinstaller(
    repo_root: Path,
    dist_path: Path,
    work_path: Path,
    build_info_path: Path,
    name: str,
    entrypoint: Path,
) -> None:
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        name,
        "--distpath",
        str(dist_path),
        "--workpath",
        str(work_path),
        "--specpath",
        str(work_path),
        "--paths",
        str(repo_root / "src"),
        "--collect-submodules",
        "mctools",
        "--add-data",
        f"{build_info_path};.",
        str(entrypoint),
    ]
    subprocess.run(command, check=True, cwd=repo_root)


def _build_info(repo_root: Path) -> dict[str, str]:
    owner, repo_name = _repository_target(repo_root)
    commit_sha = os.environ.get(
        "MC_SERVER_MANAGER_COMMIT_SHA", _git_output(repo_root, "rev-parse", "HEAD")
    )
    short_sha = commit_sha[:7] if commit_sha else "local"
    release_tag = os.environ.get("MC_SERVER_MANAGER_RELEASE_TAG", f"local-{short_sha}")
    return {
        "release_tag": release_tag,
        "commit_sha": commit_sha,
        "repo_owner": owner,
        "repo_name": repo_name,
        "installer_asset_name": INSTALLER_EXE_NAME,
        "bundle_asset_name": BUNDLE_NAME,
    }


def _repository_target(repo_root: Path) -> tuple[str, str]:
    owner = os.environ.get("MC_SERVER_MANAGER_REPO_OWNER")
    repo_name = os.environ.get("MC_SERVER_MANAGER_REPO_NAME")
    if owner and repo_name:
        return owner, repo_name

    remote_url = _git_output(repo_root, "remote", "get-url", "origin")
    match = re.search(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+)(?:\.git)?$", remote_url)
    if match is None:
        return "ryanf9802", "mc-server-manager"
    return match.group("owner"), match.group("repo")


def _git_output(repo_root: Path, *args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()
    except Exception:  # noqa: BLE001
        return ""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
