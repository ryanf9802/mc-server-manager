from __future__ import annotations

from dataclasses import dataclass

import pytest

from mc_server_manager.config.settings import RconSettings
from mc_server_manager.services.rcon import RconService


@dataclass
class FakeRconClient:
    login_result: bool = True
    command_response: str = "There are 0 of a max of 20 players online"
    stopped: bool = False
    received_commands: list[str] | None = None

    def __post_init__(self) -> None:
        if self.received_commands is None:
            self.received_commands = []

    def login(self, password: str) -> bool:
        return self.login_result and bool(password)

    def command(self, com: str) -> str:
        assert self.received_commands is not None
        self.received_commands.append(com)
        return self.command_response

    def stop(self) -> None:
        self.stopped = True


def test_rcon_service_is_unavailable_without_settings() -> None:
    service = RconService(None, "RCON is not configured.")

    assert not service.is_available
    assert service.availability_message == "RCON is not configured."

    with pytest.raises(ValueError, match="RCON is not configured"):
        service.execute("list")


def test_rcon_service_executes_command_after_login() -> None:
    client = FakeRconClient()
    service = RconService(
        RconSettings(host="example.org", port=27065, password="secret"),
        client_factory=lambda host, port: client,
    )

    result = service.execute("list")

    assert result.command == "list"
    assert result.succeeded is True
    assert result.response_text == "There are 0 of a max of 20 players online"
    assert client.received_commands == ["list"]


def test_rcon_service_raises_on_auth_failure() -> None:
    service = RconService(
        RconSettings(host="example.org", port=27065, password="secret"),
        client_factory=lambda host, port: FakeRconClient(login_result=False),
    )

    with pytest.raises(ValueError, match="RCON authentication failed"):
        service.execute("list")


def test_rcon_service_close_stops_client() -> None:
    client = FakeRconClient()
    service = RconService(
        RconSettings(host="example.org", port=27065, password="secret"),
        client_factory=lambda host, port: client,
    )

    service.test_connection()
    service.close()

    assert client.stopped is True
