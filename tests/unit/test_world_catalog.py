from datetime import datetime, timezone

from mc_server_manager.domain.models import (
    ActiveWorldRecord,
    WorldFileSet,
    WorldManifest,
    WorldStatus,
)
from mc_server_manager.services.hashing import sha256_text
from mc_server_manager.services.world_catalog import WorldCatalogService


class FakeWorldRepository:
    def __init__(self, manifests, files_by_slug) -> None:
        self._manifests = manifests
        self._files_by_slug = files_by_slug

    def list_worlds(self):
        return self._manifests

    def get_files(self, slug: str):
        return self._files_by_slug.get(slug)


class FakeLiveConfigStore:
    def __init__(self, live_files, active_record) -> None:
        self._live_files = live_files
        self._active_record = active_record

    def get_live_files(self):
        return self._live_files

    def get_active_world(self):
        return self._active_record


def test_catalog_marks_matching_active_world() -> None:
    timestamp = datetime.now(timezone.utc)
    managed_files = WorldFileSet("motd=Weekend", "[]")
    manifest = WorldManifest("weekend", "Weekend", timestamp, timestamp)
    active_record = ActiveWorldRecord(
        slug="weekend",
        applied_at_utc=timestamp,
        server_properties_sha256=sha256_text(managed_files.server_properties_text),
        whitelist_sha256=sha256_text(managed_files.whitelist_json_text),
    )
    service = WorldCatalogService(
        FakeWorldRepository([manifest], {"weekend": managed_files}),
        FakeLiveConfigStore(managed_files, active_record),
    )

    worlds = service.get_worlds()

    assert len(worlds) == 1
    assert worlds[0].status is WorldStatus.ACTIVE


def test_catalog_marks_pointer_world_unmanaged_when_live_files_drift() -> None:
    timestamp = datetime.now(timezone.utc)
    managed_files = WorldFileSet("motd=Weekend", "[]")
    live_files = WorldFileSet("motd=Drifted", "[]")
    manifest = WorldManifest("weekend", "Weekend", timestamp, timestamp)
    active_record = ActiveWorldRecord(
        slug="weekend",
        applied_at_utc=timestamp,
        server_properties_sha256=sha256_text(managed_files.server_properties_text),
        whitelist_sha256=sha256_text(managed_files.whitelist_json_text),
    )
    service = WorldCatalogService(
        FakeWorldRepository([manifest], {"weekend": managed_files}),
        FakeLiveConfigStore(live_files, active_record),
    )

    worlds = service.get_worlds()

    assert len(worlds) == 1
    assert worlds[0].status is WorldStatus.UNMANAGED_LIVE
