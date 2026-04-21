import httpx

from mc_server_manager.domain.models import HostingProvider, ProviderConnection, ProviderPowerSignal
from mc_server_manager.infrastructure.provider_clients import (
    GameHostBrosClient,
    ProviderClientFactory,
)


def test_gamehostbros_client_lists_servers_and_sends_headers() -> None:
    captured_headers = httpx.Headers()

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_headers
        captured_headers = request.headers
        assert request.url.path == "/api/client/servers"
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "attributes": {
                            "uuid": "556cadd0-e292-48f9-b407-00fd2e682f31",
                            "uuid_short": "556cadd0",
                            "name": "minecraft",
                            "description": "Server created with love",
                        }
                    }
                ]
            },
        )

    client = GameHostBrosClient(
        _connection(),
        httpx.Client(transport=httpx.MockTransport(handler)),
    )

    servers = client.list_servers()

    assert servers[0].server_id == "556cadd0"
    assert servers[0].server_uuid == "556cadd0-e292-48f9-b407-00fd2e682f31"
    assert captured_headers["Authorization"] == "Bearer token-1"
    assert captured_headers["Accept"] == "application/vnd.wisp.v1+json"
    assert captured_headers["Content-Type"] == "application/json"


def test_gamehostbros_client_parses_resource_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/client/servers/556cadd0/resources"
        return httpx.Response(
            200,
            json={
                "status": 1,
                "proc": {
                    "memory": {"total": 1821257728},
                    "cpu": {"total": 53.81},
                    "disk": {"used": 102577308},
                    "network": {"eth0": {"rx_bytes": 6517, "tx_bytes": 6703}},
                },
                "query": {
                    "maxplayers": 20,
                    "players": [],
                },
            },
        )

    client = GameHostBrosClient(
        _connection(),
        httpx.Client(transport=httpx.MockTransport(handler)),
    )

    resources = client.get_resources("556cadd0")

    assert resources.current_state == "running"
    assert resources.memory_bytes == 1821257728
    assert resources.cpu_absolute == 53.81
    assert resources.disk_bytes == 102577308
    assert resources.network_rx_bytes == 6517
    assert resources.network_tx_bytes == 6703
    assert resources.players_online == 0
    assert resources.players_max == 20


def test_gamehostbros_client_parses_resource_response_with_string_metrics() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/client/servers/556cadd0/resources"
        return httpx.Response(
            200,
            json={
                "status": "running",
                "proc": {
                    "memory": {"total": "1821257728"},
                    "cpu": {"total": "53.81"},
                    "disk": {"used": "102577308"},
                    "network": {"rx_bytes": "6517", "tx_bytes": "6703"},
                },
                "query": {
                    "maxplayers": "2",
                    "players": [],
                },
            },
        )

    client = GameHostBrosClient(
        _connection(),
        httpx.Client(transport=httpx.MockTransport(handler)),
    )

    resources = client.get_resources("556cadd0")

    assert resources.current_state == "running"
    assert resources.memory_bytes == 1821257728
    assert resources.cpu_absolute == 53.81
    assert resources.disk_bytes == 102577308
    assert resources.network_rx_bytes == 6517
    assert resources.network_tx_bytes == 6703
    assert resources.players_online == 0
    assert resources.players_max == 2


def test_gamehostbros_client_parses_live_process_shape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/client/servers/556cadd0/resources"
        return httpx.Response(
            200,
            json={
                "status": "running",
                "process": {
                    "cpu_used": 0.309,
                    "memory_used": 975114240,
                    "disk_used": 69094546323,
                    "network": {
                        "rx_bytes": 55863,
                        "tx_bytes": 16348,
                    },
                },
                "query": {
                    "maxplayers": 2,
                    "players": [],
                },
            },
        )

    client = GameHostBrosClient(
        _connection(),
        httpx.Client(transport=httpx.MockTransport(handler)),
    )

    resources = client.get_resources("556cadd0")

    assert resources.current_state == "running"
    assert resources.memory_bytes == 975114240
    assert resources.cpu_absolute == 0.309
    assert resources.disk_bytes == 69094546323
    assert resources.network_rx_bytes == 55863
    assert resources.network_tx_bytes == 16348
    assert resources.players_online == 0
    assert resources.players_max == 2


def test_gamehostbros_client_sends_power_signal_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/client/servers/556cadd0/power"
        assert request.method == "POST"
        assert request.content == b'{"signal":"restart"}'
        return httpx.Response(204)

    client = GameHostBrosClient(
        _connection(),
        httpx.Client(transport=httpx.MockTransport(handler)),
    )

    client.send_power_signal("556cadd0", ProviderPowerSignal.RESTART)


def test_provider_client_factory_creates_gamehostbros_client() -> None:
    factory = ProviderClientFactory(
        http_client_factory=lambda: httpx.Client(
            transport=httpx.MockTransport(lambda _request: httpx.Response(200, json={"data": []}))
        )
    )

    client = factory.create(_connection())

    assert client.test_connection() == "Connected to GameHostBros API. 0 server(s) available."


def _connection() -> ProviderConnection:
    return ProviderConnection(
        provider=HostingProvider.GAMEHOSTBROS,
        api_token="token-1",
        server_id="556cadd0",
        server_uuid="556cadd0-e292-48f9-b407-00fd2e682f31",
        server_name="minecraft",
    )
