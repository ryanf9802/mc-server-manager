from __future__ import annotations

from pathlib import Path

from mc_server_manager.domain.models import AppState, ProviderConnection, StoredServerConfig
from mc_server_manager.infrastructure.app_state_store import AppStateStore


class AppStateService:
    def __init__(self, store: AppStateStore, state: AppState, password: str) -> None:
        self._store = store
        self._state = state
        self._password = password

    @property
    def state(self) -> AppState:
        return self._state

    def list_servers(self) -> list[StoredServerConfig]:
        return sorted(self._state.servers, key=lambda server: server.display_name.lower())

    def get_server(self, local_id: str | None) -> StoredServerConfig | None:
        if local_id is None:
            return None
        return next((server for server in self._state.servers if server.local_id == local_id), None)

    def get_selected_server(self) -> StoredServerConfig | None:
        return self.get_server(self._state.selected_server_id)

    def set_selected_server(self, local_id: str | None) -> None:
        self._state = AppState(servers=self._state.servers, selected_server_id=local_id)
        self._persist()

    def upsert_server(self, server: StoredServerConfig) -> StoredServerConfig:
        self._assert_unique_provider_server(server)
        existing = [item for item in self._state.servers if item.local_id != server.local_id]
        existing.append(server)
        self._state = AppState(
            servers=tuple(existing),
            selected_server_id=server.local_id,
        )
        self._persist()
        return server

    def delete_server(self, local_id: str) -> None:
        servers = tuple(server for server in self._state.servers if server.local_id != local_id)
        selected = self._state.selected_server_id
        if selected == local_id:
            selected = servers[0].local_id if servers else None
        self._state = AppState(servers=servers, selected_server_id=selected)
        self._persist()

    def export_server(self, local_id: str, path: Path) -> None:
        server = self.require_server(local_id)
        self._store.export_server(server, self._password, path)

    def import_server(self, path: Path) -> StoredServerConfig:
        imported = self._store.import_server(self._password, path)
        return imported

    def save_imported_server(self, server: StoredServerConfig) -> StoredServerConfig:
        return self.upsert_server(server)

    def duplicate_with_new_identity(
        self, server: StoredServerConfig, display_name: str
    ) -> StoredServerConfig:
        return StoredServerConfig(
            local_id=AppStateStore.create_local_id(),
            display_name=display_name,
            provider=server.provider,
            sftp=server.sftp,
            rcon=server.rcon,
            notes=server.notes,
        )

    def require_server(self, local_id: str) -> StoredServerConfig:
        server = self.get_server(local_id)
        if server is None:
            raise ValueError("Selected server was not found.")
        return server

    def find_by_provider_server(self, provider: ProviderConnection) -> StoredServerConfig | None:
        return next(
            (
                server
                for server in self._state.servers
                if server.provider.provider == provider.provider
                and server.provider.resolved_panel_url == provider.resolved_panel_url
                and server.provider.server_id == provider.server_id
            ),
            None,
        )

    def _assert_unique_provider_server(self, server: StoredServerConfig) -> None:
        duplicate = self.find_by_provider_server(server.provider)
        if duplicate is not None and duplicate.local_id != server.local_id:
            raise ValueError(
                "A server with this provider connection is already saved in the application state."
            )

    def _persist(self) -> None:
        self._store.save(self._state, self._password)
