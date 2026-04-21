from datetime import datetime, timezone

from mc_server_manager.domain.models import (
    BuildInfo,
    GitHubRelease,
    HostingProvider,
    ProviderConnection,
    ProviderPowerSignal,
    ReleaseAsset,
    StoredServerConfig,
    UpdateAvailability,
)
from mc_server_manager.gui.main_window import (
    _power_signal_enabled,
    _provider_panel_url,
    _update_banner_state,
)


def test_power_controls_for_running_server() -> None:
    assert _power_signal_enabled(ProviderPowerSignal.START, "running") is False
    assert _power_signal_enabled(ProviderPowerSignal.STOP, "running") is True
    assert _power_signal_enabled(ProviderPowerSignal.RESTART, "running") is True
    assert _power_signal_enabled(ProviderPowerSignal.KILL, "running") is True


def test_power_controls_for_offline_server() -> None:
    assert _power_signal_enabled(ProviderPowerSignal.START, "offline") is True
    assert _power_signal_enabled(ProviderPowerSignal.STOP, "offline") is False
    assert _power_signal_enabled(ProviderPowerSignal.RESTART, "offline") is False
    assert _power_signal_enabled(ProviderPowerSignal.KILL, "offline") is False


def test_power_controls_disable_during_transitional_states() -> None:
    assert _power_signal_enabled(ProviderPowerSignal.START, "starting") is False
    assert _power_signal_enabled(ProviderPowerSignal.STOP, "stopping") is False
    assert _power_signal_enabled(ProviderPowerSignal.RESTART, "restarting") is False


def test_power_controls_default_to_enabled_for_unknown_state() -> None:
    assert _power_signal_enabled(ProviderPowerSignal.START, None) is True
    assert _power_signal_enabled(ProviderPowerSignal.STOP, "unknown") is True


def test_provider_panel_url_uses_short_server_id_for_gamehostbros() -> None:
    server = StoredServerConfig(
        local_id="local-1",
        display_name="QuagCraft",
        provider=ProviderConnection(
            provider=HostingProvider.GAMEHOSTBROS,
            api_token="token",
            server_id="18f3416c",
            server_uuid="18f3416c-uuid",
            server_name="QuagCraft",
        ),
    )

    assert _provider_panel_url(server) == "https://panel.gamehostbros.com/server/18f3416c"


def test_update_banner_state_shows_update_when_available() -> None:
    release = GitHubRelease(
        tag_name="main-12-abcdef0",
        published_at_utc=datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc),
        html_url="https://github.com/ryanf9802/mc-server-manager/releases/tag/main-12-abcdef0",
        assets=(
            ReleaseAsset(
                name="mc-server-manager-windows-x64.zip",
                browser_download_url="https://example.com/bundle.zip",
                size_bytes=123,
                content_type="application/zip",
            ),
        ),
    )
    availability = UpdateAvailability(
        current_build=BuildInfo(
            release_tag="main-11-aaaaaaa",
            commit_sha="abc",
            repo_owner="ryanf9802",
            repo_name="mc-server-manager",
        ),
        latest_release=release,
        is_managed_install=True,
        is_update_available=True,
        message="Update available: main-12-abcdef0",
    )

    assert _update_banner_state("main-11-aaaaaaa", availability) == (
        "Build: main-11-aaaaaaa",
        "Update available",
        release,
    )


def test_update_banner_state_keeps_default_button_when_up_to_date() -> None:
    assert _update_banner_state("main-11-aaaaaaa", None) == (
        "Build: main-11-aaaaaaa",
        "Update",
        None,
    )
