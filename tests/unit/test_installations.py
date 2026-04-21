from pathlib import Path

from mc_server_manager.domain.models import InstalledAppMetadata, utc_now
from mc_server_manager.infrastructure.installations import (
    InstallLayoutResolver,
    InstallationMetadataStore,
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
