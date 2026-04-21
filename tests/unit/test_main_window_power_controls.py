from mc_server_manager.domain.models import (
    HostingProvider,
    ProviderConnection,
    ProviderPowerSignal,
    StoredServerConfig,
)
from mc_server_manager.gui.main_window import _power_signal_enabled, _provider_panel_url


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
