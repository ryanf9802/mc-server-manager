from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, cast
from urllib.parse import urljoin

import httpx

from mc_server_manager.domain.models import (
    HostingProvider,
    ProviderConnection,
    ProviderPowerSignal,
    ProviderServerResources,
    ProviderServerSummary,
)


class ProviderClient(Protocol):
    def list_servers(self) -> list[ProviderServerSummary]: ...

    def get_server_details(self, server_id: str) -> ProviderServerSummary: ...

    def get_resources(self, server_id: str) -> ProviderServerResources: ...

    def send_power_signal(self, server_id: str, signal: ProviderPowerSignal) -> None: ...

    def test_connection(self) -> str: ...


class ProviderClientFactory:
    def __init__(
        self,
        http_client_factory: Callable[[], httpx.Client] | None = None,
    ) -> None:
        self._http_client_factory = http_client_factory or self._default_http_client_factory

    def create(self, connection: ProviderConnection) -> ProviderClient:
        if connection.provider is HostingProvider.GAMEHOSTBROS:
            return GameHostBrosClient(connection, self._http_client_factory())
        raise ValueError(f"Unsupported hosting provider: {connection.provider}")

    @staticmethod
    def _default_http_client_factory() -> httpx.Client:
        return httpx.Client(timeout=15.0)


class GameHostBrosClient:
    def __init__(self, connection: ProviderConnection, client: httpx.Client) -> None:
        self._connection = connection
        self._client = client
        self._base_url = connection.resolved_panel_url.rstrip("/") + "/"

    def list_servers(self) -> list[ProviderServerSummary]:
        servers: list[ProviderServerSummary] = []
        page = 1
        total_pages = 1

        while page <= total_pages:
            payload = self._request_json("GET", "api/client/servers", params={"page": page})
            for item in _as_list(payload.get("data")):
                attributes = _as_mapping(_as_mapping(item).get("attributes"))
                servers.append(
                    ProviderServerSummary(
                        server_id=str(attributes.get("uuid_short", "")),
                        server_uuid=str(attributes.get("uuid", "")),
                        name=str(attributes.get("name", "")),
                        description=str(attributes.get("description") or ""),
                    )
                )
            meta = _as_mapping(payload.get("meta"))
            pagination = _as_mapping(meta.get("pagination"))
            total_pages = _to_int(pagination.get("total_pages"), default=total_pages)
            page += 1
        return servers

    def get_server_details(self, server_id: str) -> ProviderServerSummary:
        payload = self._request_json("GET", f"api/client/servers/{server_id}")
        attributes = _as_mapping(payload.get("attributes"))
        return ProviderServerSummary(
            server_id=str(attributes.get("uuid_short", server_id)),
            server_uuid=str(attributes.get("uuid", "")),
            name=str(attributes.get("name", "")),
            description=str(attributes.get("description") or ""),
        )

    def get_resources(self, server_id: str) -> ProviderServerResources:
        payload = self._request_json("GET", f"api/client/servers/{server_id}/resources")
        proc = _coalesce_mapping(payload.get("proc"), payload.get("process"))
        query = _as_mapping(payload.get("query"))
        memory = _coalesce_mapping(proc.get("memory"), {"total": proc.get("memory_used")})
        cpu = _coalesce_mapping(proc.get("cpu"), {"total": proc.get("cpu_used")})
        disk = _coalesce_mapping(proc.get("disk"), {"used": proc.get("disk_used")})
        network = _as_mapping(proc.get("network"))
        primary_interface = _select_network_stats(network)
        primary_interface_map = _as_mapping(primary_interface)
        players = query.get("players")

        players_online: int | None = None
        players_max: int | None = None
        if isinstance(players, list):
            players_online = len(players)
        if _to_optional_int(query.get("maxplayers")) is not None:
            players_max = _to_int(query["maxplayers"])

        return ProviderServerResources(
            current_state=_status_label(payload.get("status")),
            memory_bytes=_to_optional_int(memory.get("total")),
            cpu_absolute=_to_optional_float(cpu.get("total")),
            disk_bytes=_to_optional_int(disk.get("used")),
            network_rx_bytes=_to_optional_int(primary_interface_map.get("rx_bytes")),
            network_tx_bytes=_to_optional_int(primary_interface_map.get("tx_bytes")),
            players_online=players_online,
            players_max=players_max,
        )

    def send_power_signal(self, server_id: str, signal: ProviderPowerSignal) -> None:
        self._request_no_content(
            "POST",
            f"api/client/servers/{server_id}/power",
            json={"signal": signal.value},
        )

    def test_connection(self) -> str:
        servers = self.list_servers()
        return f"Connected to GameHostBros API. {len(servers)} server(s) available."

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, int] | None = None,
        json: dict[str, str] | None = None,
    ) -> dict[str, object]:
        try:
            response = self._client.request(
                method,
                urljoin(self._base_url, path),
                headers=self._headers(),
                params=params,
                json=json,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ConnectionError(self._format_http_error(exc.response)) from exc
        except httpx.HTTPError as exc:
            raise ConnectionError(f"Provider API request failed: {exc}") from exc

        try:
            return response.json()
        except ValueError as exc:
            raise ConnectionError("Provider API returned invalid JSON.") from exc

    def _request_no_content(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, str] | None = None,
    ) -> None:
        try:
            response = self._client.request(
                method,
                urljoin(self._base_url, path),
                headers=self._headers(),
                json=json,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ConnectionError(self._format_http_error(exc.response)) from exc
        except httpx.HTTPError as exc:
            raise ConnectionError(f"Provider API request failed: {exc}") from exc

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._connection.api_token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.wisp.v1+json",
            "User-Agent": "mc-server-manager/0.1.0",
        }

    @staticmethod
    def _format_http_error(response: httpx.Response) -> str:
        if response.status_code == 401:
            return "Provider API authentication failed. Check the API token."
        if response.status_code == 403:
            return "Provider API access was denied."
        if response.status_code == 404:
            return "Provider server was not found."
        if response.status_code == 412:
            return "Provider rejected the request because the server is not in the required state."
        return f"Provider API request failed with status {response.status_code}."


def _optional_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    return None


def _optional_float(value: object) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


def _status_label(value: object) -> str:
    if value == 1:
        return "running"
    if value == 0:
        return "offline"
    if value is True:
        return "running"
    if value is False:
        return "offline"
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "running", "online", "on", "started"}:
            return "running"
        if normalized in {"0", "offline", "off", "stopped"}:
            return "offline"
        if normalized:
            return normalized
    return "unknown"


def _as_mapping(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return cast(dict[str, object], value)
    return {}


def _coalesce_mapping(*values: object) -> dict[str, object]:
    for value in values:
        mapping = _as_mapping(value)
        if mapping:
            return mapping
    return {}


def _as_list(value: object) -> list[object]:
    if isinstance(value, list):
        return cast(list[object], value)
    return []


def _to_int(value: object, *, default: int = 0) -> int:
    if value is None:
        return default
    return int(str(value))


def _to_optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _to_optional_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _select_network_stats(network: dict[str, object]) -> object:
    direct_keys = {"rx_bytes", "tx_bytes"}
    if direct_keys.issubset(network):
        return network
    for stats in network.values():
        if isinstance(stats, dict):
            stats_map = _as_mapping(stats)
            if "rx_bytes" in stats_map or "tx_bytes" in stats_map:
                return stats_map
    return {}
