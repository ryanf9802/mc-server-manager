from pathlib import Path

import pytest

from mc_server_manager.domain.models import InstalledAppMetadata, utc_now
from mc_server_manager.infrastructure.installations import (
    InstallLayoutResolver,
    InstallationMetadataStore,
    WindowsInstallationManager,
    _retry_file_operation,
)


def test_install_layout_resolver_uses_expected_paths(tmp_path: Path) -> None:
    resolver = InstallLayoutResolver(
        install_root=tmp_path / "install",
        start_menu_dir=tmp_path / "start-menu",
    )

    layout = resolver.resolve()

    assert (
        Path(layout.current_app_exe) == tmp_path / "install" / "current" / "mc-server-manager.exe"
    )
    assert Path(layout.installer_exe) == tmp_path / "install" / "mc-server-manager-installer.exe"
    assert Path(layout.metadata_path) == tmp_path / "install" / "installation.json"
    assert (
        Path(layout.start_menu_shortcut) == tmp_path / "start-menu" / "Minecraft Server Manager.lnk"
    )


def test_installation_metadata_store_round_trips(tmp_path: Path) -> None:
    resolver = InstallLayoutResolver(
        install_root=tmp_path / "install",
        start_menu_dir=tmp_path / "start-menu",
    )
    layout = resolver.resolve()
    store = InstallationMetadataStore()
    metadata = InstalledAppMetadata(
        release_tag="main-12-abcdef0",
        installed_at_utc=utc_now(),
        current_exe_name="mc-server-manager.exe",
        installer_exe_name="mc-server-manager-installer.exe",
    )

    store.save(layout, metadata)

    assert store.load(layout) == metadata


def test_retry_file_operation_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = {"count": 0}

    def flaky_operation() -> None:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise OSError(32, "The process cannot access the file because it is being used")

    monkeypatch.setattr("mc_server_manager.infrastructure.installations.time.sleep", lambda _s: None)

    _retry_file_operation(flaky_operation, timeout_seconds=1.0, initial_delay_seconds=0.01)

    assert attempts["count"] == 3


def test_windows_installation_manager_retries_current_dir_replace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    resolver = InstallLayoutResolver(
        install_root=tmp_path / "install",
        start_menu_dir=tmp_path / "start-menu",
    )
    layout = resolver.resolve()
    current_dir = Path(layout.current_dir)
    current_dir.mkdir(parents=True, exist_ok=True)
    (current_dir / "mc-server-manager.exe").write_text("old exe", encoding="utf-8")
    extracted = tmp_path / "bundle"
    extracted.mkdir(parents=True, exist_ok=True)
    (extracted / "mc-server-manager.exe").write_text("new exe", encoding="utf-8")
    (extracted / "mc-server-manager-installer.exe").write_text("installer", encoding="utf-8")
    (extracted / "build-info.json").write_text("{}", encoding="utf-8")

    original_replace = Path.replace
    attempts = {"count": 0}

    def flaky_replace(self: Path, target: Path) -> Path:
        if self == current_dir and attempts["count"] == 0:
            attempts["count"] += 1
            raise OSError(32, "The process cannot access the file because it is being used")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", flaky_replace)
    monkeypatch.setattr("mc_server_manager.infrastructure.installations.time.sleep", lambda _s: None)
    monkeypatch.setattr(
        WindowsInstallationManager,
        "_create_start_menu_shortcut",
        lambda self, shortcut_path, target_path: None,
    )

    app_path = WindowsInstallationManager().install_bundle(
        layout,
        extracted,
        release_tag="main-12-abcdef0",
    )

    assert attempts["count"] == 1
    assert app_path == current_dir / "mc-server-manager.exe"
    assert app_path.read_text(encoding="utf-8") == "new exe"
