from __future__ import annotations

from mc_server_manager.domain.models import (
    ActiveWorldRecord,
    WorldDetail,
    WorldFileSet,
    WorldStatus,
    WorldSummary,
)
from mc_server_manager.services.hashing import sha256_text


class WorldCatalogService:
    def __init__(self, world_repository, live_config_store) -> None:
        self._world_repository = world_repository
        self._live_config_store = live_config_store

    def get_worlds(self) -> list[WorldSummary]:
        manifests = sorted(
            self._world_repository.list_worlds(),
            key=lambda manifest: manifest.display_name.lower(),
        )
        active_record = self._live_config_store.get_active_world()
        live_files = self._live_config_store.get_live_files()

        return [
            WorldSummary(
                manifest=manifest,
                status=self._resolve_status(
                    slug=manifest.slug,
                    managed_files=self._world_repository.get_files(manifest.slug),
                    active_record=active_record,
                    live_files=live_files,
                ),
            )
            for manifest in manifests
        ]

    def get_world(self, slug: str) -> WorldDetail | None:
        manifest = next(
            (item for item in self._world_repository.list_worlds() if item.slug == slug), None
        )
        if manifest is None:
            return None

        managed_files = self._world_repository.get_files(slug)
        if managed_files is None:
            return None

        active_record = self._live_config_store.get_active_world()
        live_files = self._live_config_store.get_live_files()
        status = self._resolve_status(slug, managed_files, active_record, live_files)
        return WorldDetail(manifest=manifest, files=managed_files, status=status)

    def _resolve_status(
        self,
        slug: str,
        managed_files: WorldFileSet | None,
        active_record: ActiveWorldRecord | None,
        live_files: WorldFileSet,
    ) -> WorldStatus:
        if managed_files is None:
            return WorldStatus.INACTIVE

        if active_record is None or active_record.slug != slug:
            return WorldStatus.INACTIVE

        live_hashes = (
            sha256_text(live_files.server_properties_text),
            sha256_text(live_files.whitelist_json_text),
        )
        pointer_matches_live = (
            active_record.server_properties_sha256 == live_hashes[0]
            and active_record.whitelist_sha256 == live_hashes[1]
        )
        if not pointer_matches_live:
            return WorldStatus.UNMANAGED_LIVE

        managed_hashes = (
            sha256_text(managed_files.server_properties_text),
            sha256_text(managed_files.whitelist_json_text),
        )
        return WorldStatus.ACTIVE if managed_hashes == live_hashes else WorldStatus.PENDING_APPLY
