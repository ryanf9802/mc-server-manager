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

    assert settings.host == "example.org"
    assert settings.port == 22
    assert settings.normalized_server_root == "/minecraft"


def test_dotenv_loader_rejects_missing_keys(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("SFTP_HOST=example.org\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Missing required .env keys"):
        DotEnvLoader().load([env_path])
