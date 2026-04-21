from pathlib import Path

import pytest

from mc_server_manager.domain.models import SftpConnectionSettings
from mc_server_manager.infrastructure import sftp_gateway
from mc_server_manager.infrastructure.sftp_gateway import SftpGateway


class FakeSftpClient:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakeSshClient:
    def __init__(self, *, connect_error: Exception | None = None) -> None:
        self.connect_error = connect_error
        self.connect_kwargs: dict[str, object] | None = None
        self.closed = False
        self.policy = None
        self.sftp_client = FakeSftpClient()

    def set_missing_host_key_policy(self, policy) -> None:  # noqa: ANN001
        self.policy = policy

    def connect(self, **kwargs) -> None:  # noqa: ANN003
        self.connect_kwargs = kwargs
        if self.connect_error is not None:
            raise self.connect_error

    def open_sftp(self) -> FakeSftpClient:
        return self.sftp_client

    def close(self) -> None:
        self.closed = True


def test_sftp_gateway_connects_with_password_only_flags(monkeypatch) -> None:
    fake_client = FakeSshClient()
    monkeypatch.setattr(sftp_gateway.paramiko, "SSHClient", lambda: fake_client)
    gateway = SftpGateway(_settings())

    with gateway.session() as sftp:
        assert sftp is fake_client.sftp_client

    assert fake_client.connect_kwargs is not None
    assert fake_client.connect_kwargs["look_for_keys"] is False
    assert fake_client.connect_kwargs["allow_agent"] is False
    assert fake_client.connect_kwargs["timeout"] == 15.0
    assert fake_client.connect_kwargs["auth_timeout"] == 15.0
    assert fake_client.connect_kwargs["banner_timeout"] == 15.0
    assert fake_client.sftp_client.closed is True
    assert fake_client.closed is True


def test_sftp_gateway_wraps_connection_errors_with_logs_path(tmp_path: Path, monkeypatch) -> None:
    fake_client = FakeSshClient(connect_error=EOFError("transport shut down or saw EOF"))
    monkeypatch.setattr(sftp_gateway.paramiko, "SSHClient", lambda: fake_client)
    monkeypatch.setattr(sftp_gateway, "get_logs_dir", lambda: tmp_path / "logs")
    monkeypatch.setattr(sftp_gateway, "runtime_diagnostics", lambda: {"release_tag": "test"})
    gateway = SftpGateway(_settings())

    with pytest.raises(ConnectionError, match="See logs in"):
        with gateway.session():
            pass


def _settings() -> SftpConnectionSettings:
    return SftpConnectionSettings(
        host="sftp.example.com",
        port=2022,
        username="minecraft",
        password="secret",
        server_root="/",
    )
