from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path

from platformdirs import user_data_dir

from mc_server_manager.domain.models import InstallLayout, InstalledAppMetadata, utc_now


class InstallLayoutResolver:
    def __init__(
        self,
        install_root: Path | None = None,
        start_menu_dir: Path | None = None,
    ) -> None:
        self._install_root = install_root
        self._start_menu_dir = start_menu_dir

    def resolve(self) -> InstallLayout:
        root_dir = self._install_root or _default_install_root()
        shortcut_dir = self._start_menu_dir or _default_start_menu_dir(root_dir)
        return InstallLayout(
            root_dir=str(root_dir),
            current_dir=str(root_dir / "current"),
            current_app_exe=str(root_dir / "current" / "mc-server-manager.exe"),
            installer_exe=str(root_dir / "mc-server-manager-installer.exe"),
            metadata_path=str(root_dir / "installation.json"),
            staging_dir=str(root_dir / "staging"),
            start_menu_shortcut=str(shortcut_dir / "Minecraft Server Manager.lnk"),
        )


class InstallationMetadataStore:
    def load(self, layout: InstallLayout) -> InstalledAppMetadata | None:
        metadata_path = Path(layout.metadata_path)
        if not metadata_path.exists():
            return None
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        return InstalledAppMetadata(
            release_tag=str(payload["release_tag"]),
            installed_at_utc=_parse_datetime(str(payload["installed_at_utc"])),
            current_exe_name=str(payload["current_exe_name"]),
            installer_exe_name=str(payload["installer_exe_name"]),
        )

    def save(self, layout: InstallLayout, metadata: InstalledAppMetadata) -> None:
        metadata_path = Path(layout.metadata_path)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(metadata)
        payload["installed_at_utc"] = metadata.installed_at_utc.isoformat()
        metadata_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class WindowsInstallationManager:
    def __init__(self, metadata_store: InstallationMetadataStore | None = None) -> None:
        self._metadata_store = metadata_store or InstallationMetadataStore()

    def install_bundle(
        self,
        layout: InstallLayout,
        extracted_bundle_dir: Path,
        *,
        release_tag: str,
    ) -> Path:
        root_dir = Path(layout.root_dir)
        current_dir = Path(layout.current_dir)
        installer_path = Path(layout.installer_exe)
        shortcut_path = Path(layout.start_menu_shortcut)

        root_dir.mkdir(parents=True, exist_ok=True)
        Path(layout.staging_dir).mkdir(parents=True, exist_ok=True)

        current_source = extracted_bundle_dir / "mc-server-manager.exe"
        installer_source = extracted_bundle_dir / "mc-server-manager-installer.exe"
        build_info_source = extracted_bundle_dir / "build-info.json"

        if not current_source.exists():
            raise ValueError("Update bundle is missing mc-server-manager.exe.")
        if not installer_source.exists():
            raise ValueError("Update bundle is missing mc-server-manager-installer.exe.")
        if not build_info_source.exists():
            raise ValueError("Update bundle is missing build-info.json.")

        if current_dir.exists():
            shutil.rmtree(current_dir)
        current_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(current_source, current_dir / current_source.name)
        shutil.copy2(build_info_source, current_dir / build_info_source.name)
        shutil.copy2(installer_source, installer_path)

        self._create_start_menu_shortcut(shortcut_path, current_dir / current_source.name)
        self._metadata_store.save(
            layout,
            InstalledAppMetadata(
                release_tag=release_tag,
                installed_at_utc=utc_now(),
                current_exe_name=current_source.name,
                installer_exe_name=installer_source.name,
            ),
        )
        return current_dir / current_source.name

    @staticmethod
    def _create_start_menu_shortcut(shortcut_path: Path, target_path: Path) -> None:
        shortcut_path.parent.mkdir(parents=True, exist_ok=True)
        escaped_shortcut = str(shortcut_path).replace("'", "''")
        escaped_target = str(target_path).replace("'", "''")
        script = (
            "$ws = New-Object -ComObject WScript.Shell; "
            f"$shortcut = $ws.CreateShortcut('{escaped_shortcut}'); "
            f"$shortcut.TargetPath = '{escaped_target}'; "
            f"$shortcut.WorkingDirectory = '{target_path.parent}'; "
            "$shortcut.Save()"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            check=True,
        )


def _default_install_root() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "mc-server-manager" / "install"
    return Path(user_data_dir("mc-server-manager", "mc-server-manager")).parent / "install"


def _default_start_menu_dir(install_root: Path) -> Path:
    app_data = os.environ.get("APPDATA")
    if app_data:
        return Path(app_data) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    return install_root / "shortcuts"


def _parse_datetime(value: str):
    from datetime import datetime

    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)
