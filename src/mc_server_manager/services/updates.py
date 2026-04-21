from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from mc_server_manager.domain.models import BuildInfo, GitHubRelease, UpdateAvailability
from mc_server_manager.infrastructure.installations import InstallLayoutResolver
from mc_server_manager.infrastructure.releases import GitHubReleaseClient

logger = logging.getLogger(__name__)


class UpdateService:
    def __init__(
        self,
        build_info: BuildInfo,
        layout_resolver: InstallLayoutResolver | None = None,
        current_executable: Path | None = None,
    ) -> None:
        self._build_info = build_info
        self._layout_resolver = layout_resolver or InstallLayoutResolver()
        self._current_executable = current_executable or Path(sys.executable).resolve()

    @property
    def build_info(self) -> BuildInfo:
        return self._build_info

    def current_build_label(self) -> str:
        return self._build_info.release_tag

    def is_managed_install(self) -> bool:
        if self._build_info.is_dev:
            return False
        layout = self._layout_resolver.resolve()
        return self._current_executable == Path(layout.current_app_exe)

    def check_for_updates(self) -> UpdateAvailability:
        if self._build_info.is_dev:
            logger.info("Update check skipped because current build is a dev build.")
            return UpdateAvailability(
                current_build=self._build_info,
                latest_release=None,
                is_managed_install=False,
                is_update_available=False,
                message="This is a development build. Updates are available only from the installed Windows app.",
            )
        if not self.is_managed_install():
            logger.warning(
                "Update check skipped because executable is outside managed install: %s",
                self._current_executable,
            )
            return UpdateAvailability(
                current_build=self._build_info,
                latest_release=None,
                is_managed_install=False,
                is_update_available=False,
                message="This build is not running from the managed installation path.",
            )
        release_client = self._release_client()
        latest_release = release_client.latest_release()
        logger.info(
            "Checked latest release tag=%s against current tag=%s",
            latest_release.tag_name,
            self._build_info.release_tag,
        )
        if latest_release.tag_name == self._build_info.release_tag:
            return UpdateAvailability(
                current_build=self._build_info,
                latest_release=latest_release,
                is_managed_install=True,
                is_update_available=False,
                message="Minecraft Server Manager is already up to date.",
            )
        return UpdateAvailability(
            current_build=self._build_info,
            latest_release=latest_release,
            is_managed_install=True,
            is_update_available=True,
            message=f"Update available: {latest_release.tag_name}",
        )

    def launch_update(self, release: GitHubRelease, *, wait_pid: int) -> None:
        if not self.is_managed_install():
            raise ValueError("Updates require running from the managed installation path.")

        layout = self._layout_resolver.resolve()
        installer_path = Path(layout.installer_exe)
        if not installer_path.exists():
            raise ValueError("Installed updater helper was not found.")

        temp_dir = Path(tempfile.mkdtemp(prefix="mc-server-manager-updater-"))
        temp_installer = temp_dir / installer_path.name
        shutil.copy2(installer_path, temp_installer)
        logger.info(
            "Launching updater helper from %s for release_tag=%s wait_pid=%s",
            temp_installer,
            release.tag_name,
            wait_pid,
        )

        command = [
            str(temp_installer),
            "--mode",
            "update",
            "--wait-pid",
            str(wait_pid),
            "--release-tag",
            release.tag_name,
            "--silent",
        ]
        if os.name == "nt":
            subprocess.Popen(
                command,
                close_fds=True,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            )
            return
        subprocess.Popen(command, close_fds=True)

    def _release_client(self) -> GitHubReleaseClient:
        if not self._build_info.repo_owner or not self._build_info.repo_name:
            raise ValueError("Build information is missing the GitHub repository target.")
        return GitHubReleaseClient(self._build_info.repo_owner, self._build_info.repo_name)
