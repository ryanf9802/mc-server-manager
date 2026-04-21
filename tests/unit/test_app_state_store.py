from pathlib import Path

import pytest

from mc_server_manager.domain.models import (
    AppState,
    HostingProvider,
    ProviderConnection,
    RconConnectionSettings,
    SftpConnectionSettings,
    StoredServerConfig,
)
from mc_server_manager.infrastructure.app_state_store import AppStateStore


def test_app_state_store_round_trips_encrypted_state(tmp_path: Path) -> None:
    store = AppStateStore(app_dir=tmp_path)
    state = AppState(
        servers=(
            StoredServerConfig(
                local_id="local-1",
                display_name="Weekend Server",
                provider=ProviderConnection(
                    provider=HostingProvider.GAMEHOSTBROS,
                    api_token="token-1",
                    server_id="abcd1234",
                    server_uuid="abcd1234-full",
                    server_name="Weekend Provider Name",
                ),
                sftp=SftpConnectionSettings(
                    host="sftp.example.com",
                    port=22,
                    username="minecraft",
                    password="secret",
                    server_root="/servers/weekend",
                ),
                rcon=RconConnectionSettings(
                    host="mc.example.com",
                    port=27065,
                    password="rcon-secret",
                ),
                notes="Main shared server",
            ),
        ),
        selected_server_id="local-1",
    )

    store.save(state, "passphrase")
    loaded = store.load("passphrase")

    assert loaded == state
    assert store.state_path.exists()


def test_app_state_store_rejects_wrong_password(tmp_path: Path) -> None:
    store = AppStateStore(app_dir=tmp_path)
    store.initialize("correct horse battery staple")

    with pytest.raises(ValueError, match="Failed to decrypt app data"):
        store.load("wrong password")


def test_app_state_store_exports_and_imports_single_server(tmp_path: Path) -> None:
    store = AppStateStore(app_dir=tmp_path / "app")
    server = StoredServerConfig(
        local_id="local-1",
        display_name="Imported Server",
        provider=ProviderConnection(
            provider=HostingProvider.GAMEHOSTBROS,
            api_token="token-1",
            server_id="abcd1234",
            server_uuid="abcd1234-full",
            server_name="Imported Provider Name",
        ),
        sftp=SftpConnectionSettings(
            host="sftp.example.com",
            port=22,
            username="minecraft",
            password="secret",
            server_root="/servers/imported",
        ),
    )
    export_path = tmp_path / "server.mcserver"

    store.export_server(server, "passphrase", export_path)
    imported = store.import_server("passphrase", export_path)

    assert imported == server
