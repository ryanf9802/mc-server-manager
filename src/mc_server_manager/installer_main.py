from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import tempfile
import time
import tkinter as tk
import zipfile
from pathlib import Path
from tkinter import messagebox

from mc_server_manager.app_icon import apply_window_icon, configure_windows_app_identity
from mc_server_manager.infrastructure.build_info import load_build_info
from mc_server_manager.infrastructure.installations import (
    InstallLayoutResolver,
    WindowsInstallationManager,
)
from mc_server_manager.infrastructure.releases import GitHubReleaseClient
from mc_server_manager.infrastructure.runtime_logging import configure_logging, get_logs_dir

logger = logging.getLogger(__name__)


def main() -> int:
    log_path = configure_logging("installer.log")
    configure_windows_app_identity("installer")
    root = tk.Tk()
    apply_window_icon(root)
    root.withdraw()
    try:
        logger.info("Installer/updater starting with logs at %s", log_path)
        args = _parse_args()
        build_info = load_build_info()
        if build_info.is_dev:
            raise ValueError("Installer metadata is missing build information.")
        if not build_info.repo_owner or not build_info.repo_name:
            raise ValueError("Installer metadata is missing the GitHub repository target.")

        layout = InstallLayoutResolver().resolve()
        release_client = GitHubReleaseClient(build_info.repo_owner, build_info.repo_name)
        if args.wait_pid is not None:
            logger.info("Waiting for process %s to exit before continuing update", args.wait_pid)
            _wait_for_exit(args.wait_pid)

        release = (
            release_client.get_release_by_tag(args.release_tag)
            if args.release_tag
            else release_client.latest_release()
        )
        bundle_asset = release.get_asset(build_info.bundle_asset_name)
        if bundle_asset is None:
            raise ValueError(
                f"Release {release.tag_name} is missing {build_info.bundle_asset_name}."
            )

        working_dir = Path(tempfile.mkdtemp(prefix="mc-server-manager-install-"))
        archive_path = working_dir / bundle_asset.name
        extract_dir = working_dir / "bundle"
        release_client.download_asset(bundle_asset, archive_path)
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(extract_dir)

        app_path = WindowsInstallationManager().install_bundle(
            layout,
            extract_dir,
            release_tag=release.tag_name,
        )
        logger.info("Installed release %s to %s", release.tag_name, layout.current_dir)
        _launch(app_path)
        if not args.silent:
            messagebox.showinfo(
                "Minecraft Server Manager",
                f"Installed {release.tag_name} to {Path(layout.current_dir)}.",
                parent=root,
            )
        root.destroy()
        return 0
    except Exception as exc:  # noqa: BLE001
        logger.exception("Installer/updater failed: %s", exc)
        _show_error(str(exc), root)
        try:
            root.destroy()
        except Exception:  # noqa: BLE001
            pass
        return 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("install", "update"), default="install")
    parser.add_argument("--wait-pid", type=int, default=None)
    parser.add_argument("--release-tag", default="")
    parser.add_argument("--silent", action="store_true")
    return parser.parse_args()


def _wait_for_exit(pid: int, *, timeout_seconds: float = 60.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if not _process_exists(pid):
            return
        time.sleep(0.25)
    raise TimeoutError("Timed out waiting for the running app to close before updating.")


def _process_exists(pid: int) -> bool:
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                check=False,
                text=True,
            )
            return str(pid) in result.stdout
        import os

        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _launch(app_path: Path) -> None:
    if sys.platform == "win32":
        subprocess.Popen(
            [str(app_path)],
            cwd=str(app_path.parent),
            close_fds=True,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        return
    subprocess.Popen([str(app_path)], cwd=str(app_path.parent), close_fds=True)


def _show_error(message: str, root: tk.Tk) -> None:
    message = f"{message}\n\nSee logs in {get_logs_dir()} for details."
    try:
        messagebox.showerror("Minecraft Server Manager", message, parent=root)
    except Exception:  # noqa: BLE001
        print(message, file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
