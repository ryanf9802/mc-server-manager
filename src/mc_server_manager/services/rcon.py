from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, cast

from mctools import RCONClient

from mc_server_manager.config.settings import RconSettings
from mc_server_manager.domain.models import RconCommandResult, utc_now


class RconClientProtocol(Protocol):
    def login(self, password: str) -> bool: ...

    def command(self, com: str) -> str: ...

    def stop(self) -> None: ...


class RconService:
    def __init__(
        self,
        settings: RconSettings | None,
        unavailable_reason: str | None = None,
        client_factory: Callable[[str, int], RconClientProtocol] | None = None,
    ) -> None:
        self._settings = settings
        self._unavailable_reason = unavailable_reason
        self._client_factory = client_factory or self._default_client_factory
        self._client: RconClientProtocol | None = None
        self._authenticated = False

    @property
    def is_available(self) -> bool:
        return self._settings is not None

    @property
    def availability_message(self) -> str:
        if self._settings is None:
            return self._unavailable_reason or "RCON is not configured."
        return f"RCON ready for {self._settings.endpoint}."

    def test_connection(self) -> str:
        settings = self._require_settings()
        self._ensure_connected()
        return f"Connected to RCON at {settings.endpoint}."

    def execute(self, command: str) -> RconCommandResult:
        cleaned_command = command.strip()
        if not cleaned_command:
            raise ValueError("Enter an RCON command before sending.")

        self._ensure_connected()
        assert self._client is not None  # Narrowed by _ensure_connected.

        try:
            response = self._client.command(cleaned_command)
        except Exception as exc:  # noqa: BLE001
            self.close()
            raise ConnectionError(f"RCON command failed: {exc}") from exc

        normalized_response = response.strip() or "(no response)"
        return RconCommandResult(
            command=cleaned_command,
            response_text=normalized_response,
            succeeded=True,
            executed_at=utc_now(),
        )

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.stop()
            except Exception:  # noqa: BLE001
                pass
            finally:
                self._client = None
                self._authenticated = False

    def _ensure_connected(self) -> None:
        settings = self._require_settings()
        if self._client is None:
            try:
                self._client = self._client_factory(settings.host, settings.port)
            except Exception as exc:  # noqa: BLE001
                raise ConnectionError(
                    f"Failed to connect to RCON at {settings.endpoint}: {exc}"
                ) from exc

        if self._authenticated:
            return

        assert self._client is not None
        try:
            authenticated = self._client.login(settings.password)
        except Exception as exc:  # noqa: BLE001
            self.close()
            raise ConnectionError(
                f"Failed to connect to RCON at {settings.endpoint}: {exc}"
            ) from exc

        if not authenticated:
            self.close()
            raise ValueError("RCON authentication failed. Check RCON_PASSWORD.")

        self._authenticated = True

    def _require_settings(self) -> RconSettings:
        if self._settings is None:
            raise ValueError(
                self._unavailable_reason
                or "RCON is not configured. Set RCON_HOST, RCON_PORT, and RCON_PASSWORD."
            )
        return self._settings

    @staticmethod
    def _default_client_factory(host: str, port: int) -> RconClientProtocol:
        return cast(RconClientProtocol, RCONClient(host, port=port))
