import pytest

from mc_server_manager.services.sftp_connection_address import (
    build_gamehostbros_sftp_settings,
    format_gamehostbros_sftp_address,
    parse_gamehostbros_sftp_address,
)


def test_parse_gamehostbros_sftp_address_accepts_full_scheme() -> None:
    host, port = parse_gamehostbros_sftp_address("sftp://9950ece8c16c6dbc.daemon.panel.gg:2022")

    assert host == "9950ece8c16c6dbc.daemon.panel.gg"
    assert port == 2022


def test_parse_gamehostbros_sftp_address_accepts_plain_host_port() -> None:
    host, port = parse_gamehostbros_sftp_address("9950ece8c16c6dbc.daemon.panel.gg:2022")

    assert host == "9950ece8c16c6dbc.daemon.panel.gg"
    assert port == 2022


def test_parse_gamehostbros_sftp_address_rejects_missing_port() -> None:
    with pytest.raises(ValueError, match="must include a port"):
        parse_gamehostbros_sftp_address("sftp://9950ece8c16c6dbc.daemon.panel.gg")


def test_parse_gamehostbros_sftp_address_rejects_invalid_port() -> None:
    with pytest.raises(ValueError, match="must include a valid port"):
        parse_gamehostbros_sftp_address("sftp://9950ece8c16c6dbc.daemon.panel.gg:notaport")


def test_build_gamehostbros_sftp_settings_forces_root_directory() -> None:
    settings = build_gamehostbros_sftp_settings(
        connection_address="sftp://9950ece8c16c6dbc.daemon.panel.gg:2022",
        username="minecraft",
        password="secret",
        require=True,
    )

    assert settings is not None
    assert settings.host == "9950ece8c16c6dbc.daemon.panel.gg"
    assert settings.port == 2022
    assert settings.username == "minecraft"
    assert settings.password == "secret"
    assert settings.server_root == "/"


def test_build_gamehostbros_sftp_settings_returns_none_when_optional_and_blank() -> None:
    settings = build_gamehostbros_sftp_settings(
        connection_address="",
        username="",
        password="",
        require=False,
    )

    assert settings is None


def test_format_gamehostbros_sftp_address_prefills_settings() -> None:
    assert (
        format_gamehostbros_sftp_address("9950ece8c16c6dbc.daemon.panel.gg", 2022)
        == "sftp://9950ece8c16c6dbc.daemon.panel.gg:2022"
    )
