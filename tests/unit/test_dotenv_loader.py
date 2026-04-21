from pathlib import Path

import pytest

from mc_server_manager.config.dotenv_loader import DotEnvLoader


def test_dotenv_loader_reads_expected_values(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "SFTP_HOST=example.org",
                "SFTP_PORT=22",
                "SFTP_USERNAME=tester",
                "SFTP_PASSWORD=secret",
                "SFTP_SERVER_ROOT=/minecraft",
            ]
        ),
        encoding="utf-8",
    )

    settings = DotEnvLoader().load([env_path])

    assert settings.sftp.host == "example.org"
    assert settings.sftp.port == 22
    assert settings.sftp.normalized_server_root == "/minecraft"
    assert settings.rcon is None


def test_dotenv_loader_rejects_missing_keys(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("SFTP_HOST=example.org\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Missing required .env keys"):
        DotEnvLoader().load([env_path])


def test_dotenv_loader_reads_optional_rcon_values(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "SFTP_HOST=example.org",
                "SFTP_PORT=22",
                "SFTP_USERNAME=tester",
                "SFTP_PASSWORD=secret",
                "SFTP_SERVER_ROOT=/minecraft",
                "RCON_HOST=mc.example.org",
                "RCON_PORT=27065",
                "RCON_PASSWORD=rcon-secret",
            ]
        ),
        encoding="utf-8",
    )

    settings = DotEnvLoader().load([env_path])

    assert settings.rcon is not None
    assert settings.rcon.host == "mc.example.org"
    assert settings.rcon.port == 27065
    assert settings.rcon_unavailable_reason is None


def test_dotenv_loader_marks_partial_rcon_config_unavailable(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "SFTP_HOST=example.org",
                "SFTP_PORT=22",
                "SFTP_USERNAME=tester",
                "SFTP_PASSWORD=secret",
                "SFTP_SERVER_ROOT=/minecraft",
                "RCON_HOST=mc.example.org",
            ]
        ),
        encoding="utf-8",
    )

    settings = DotEnvLoader().load([env_path])

    assert settings.rcon is None
    assert settings.rcon_unavailable_reason is not None
    assert "Missing: RCON_PORT, RCON_PASSWORD" in settings.rcon_unavailable_reason


def test_dotenv_loader_marks_invalid_rcon_port_unavailable(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "SFTP_HOST=example.org",
                "SFTP_PORT=22",
                "SFTP_USERNAME=tester",
                "SFTP_PASSWORD=secret",
                "SFTP_SERVER_ROOT=/minecraft",
                "RCON_HOST=mc.example.org",
                "RCON_PORT=not-a-port",
                "RCON_PASSWORD=rcon-secret",
            ]
        ),
        encoding="utf-8",
    )

    settings = DotEnvLoader().load([env_path])

    assert settings.rcon is None
    assert settings.rcon_unavailable_reason == (
        "RCON is disabled because RCON_PORT must be a valid integer."
    )
