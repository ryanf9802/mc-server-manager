from __future__ import annotations

from mc_server_manager.domain.models import StoredServerConfig
from mc_server_manager.infrastructure.provider_clients import ProviderClient, ProviderClientFactory
from mc_server_manager.infrastructure.remote_paths import RemotePaths
from mc_server_manager.infrastructure.repositories import SftpLiveConfigStore, SftpWorldRepository
from mc_server_manager.infrastructure.sftp_gateway import SftpGateway
from mc_server_manager.services.activation import ActivationService
from mc_server_manager.services.rcon import RconService
from mc_server_manager.services.world_catalog import WorldCatalogService
from mc_server_manager.services.world_editor import WorldEditorService
from mc_server_manager.validation.server_properties import ServerPropertiesValidator
from mc_server_manager.validation.whitelist import WhitelistValidator


def create_world_services(
    server: StoredServerConfig,
) -> tuple[WorldCatalogService, WorldEditorService, ActivationService]:
    if server.sftp is None:
        raise ValueError("SFTP is not configured for this server.")

    gateway = SftpGateway(server.sftp)
    paths = RemotePaths(server.sftp)
    world_repository = SftpWorldRepository(gateway, paths)
    live_config_store = SftpLiveConfigStore(gateway, paths)
    return (
        WorldCatalogService(world_repository, live_config_store),
        WorldEditorService(
            world_repository,
            live_config_store,
            ServerPropertiesValidator(),
            WhitelistValidator(),
        ),
        ActivationService(world_repository, live_config_store),
    )


def create_rcon_service(server: StoredServerConfig) -> RconService:
    if server.rcon is None:
        return RconService(None, "RCON is not configured for this server.")
    return RconService(server.rcon, None)


def create_provider_client(server: StoredServerConfig) -> ProviderClient:
    return ProviderClientFactory().create(server.provider)


def test_sftp_connection(server: StoredServerConfig) -> str:
    if server.sftp is None:
        raise ValueError("SFTP is not configured for this server.")
    gateway = SftpGateway(server.sftp)
    with gateway.session():
        return f"Connected to SFTP at {server.sftp.host}:{server.sftp.port}."
