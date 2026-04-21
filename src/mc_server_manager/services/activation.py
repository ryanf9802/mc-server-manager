from __future__ import annotations

from mc_server_manager.domain.models import ActiveWorldRecord, utc_now
from mc_server_manager.services.hashing import sha256_text


class ActivationService:
    def __init__(self, world_repository, live_config_store) -> None:
        self._world_repository = world_repository
        self._live_config_store = live_config_store

    def activate_world(self, slug: str) -> None:
        files = self._world_repository.get_files(slug)
        if files is None:
            raise ValueError(f"World '{slug}' was not found.")

        self._live_config_store.apply_live_files(files)
        self._live_config_store.save_active_world(
            ActiveWorldRecord(
                slug=slug,
                applied_at_utc=utc_now(),
                server_properties_sha256=sha256_text(files.server_properties_text),
                whitelist_sha256=sha256_text(files.whitelist_json_text),
            )
        )
