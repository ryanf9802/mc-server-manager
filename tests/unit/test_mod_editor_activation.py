from datetime import datetime, timezone

import pytest

from mc_server_manager.domain.models import (
    ActiveModListsRecord,
    ModJarMetadata,
    ModListManifest,
    ModListSaveRequest,
)
from mc_server_manager.services.hashing import sha256_bytes
from mc_server_manager.services.mod_activation import ModActivationService
from mc_server_manager.services.mod_editor import ModEditorService


class FakeModRepository:
    def __init__(self, manifests=(), bytes_by_slug=None) -> None:
        self._manifests = {manifest.slug: manifest for manifest in manifests}
        self._bytes_by_slug = bytes_by_slug or {}
        self.saved_manifest = None
        self.saved_bytes = None
        self.deleted_slug = None

    def list_mod_lists(self):
        return list(self._manifests.values())

    def get_mod_list(self, slug: str):
        return self._manifests.get(slug)

    def read_mod_bytes(self, slug: str, filename: str) -> bytes:
        return self._bytes_by_slug[slug][filename]

    def save_mod_list(self, manifest, jar_bytes_by_filename):
        self.saved_manifest = manifest
        self.saved_bytes = dict(jar_bytes_by_filename)
        self._manifests[manifest.slug] = manifest
        self._bytes_by_slug[manifest.slug] = dict(jar_bytes_by_filename)

    def delete_mod_list(self, slug: str) -> None:
        self.deleted_slug = slug
        self._manifests.pop(slug, None)
        self._bytes_by_slug.pop(slug, None)


class FakeLiveModsStore:
    def __init__(self, live_mods=(), active_record=None) -> None:
        self._live_mods = tuple(live_mods)
        self._active_record = active_record
        self.replaced_live_mods = None
        self.saved_active_record = None

    def list_live_mods(self):
        return self._live_mods

    def get_active_mod_lists(self):
        return self._active_record

    def replace_live_mods(self, jar_bytes_by_filename):
        self.replaced_live_mods = dict(jar_bytes_by_filename)

    def save_active_mod_lists(self, record):
        self.saved_active_record = record
        self._active_record = record


def test_editor_saves_local_and_managed_files(tmp_path) -> None:
    timestamp = datetime(2026, 4, 21, tzinfo=timezone.utc)
    managed_bytes = b"managed"
    local_bytes = b"local"
    local_path = tmp_path / "extra.jar"
    local_path.write_bytes(local_bytes)
    existing = ModListManifest(
        slug="fabric",
        display_name="Fabric",
        created_at_utc=timestamp,
        updated_at_utc=timestamp,
        jars=(ModJarMetadata("managed.jar", len(managed_bytes), sha256_bytes(managed_bytes)),),
    )
    repository = FakeModRepository(
        manifests=(existing,),
        bytes_by_slug={"fabric": {"managed.jar": managed_bytes}},
    )
    service = ModEditorService(repository, FakeLiveModsStore())

    saved = service.save_mod_list(
        ModListSaveRequest(
            slug="fabric",
            display_name="Fabric Updated",
            created_at_utc=timestamp,
            managed_files=(existing_to_managed_file(existing.jars[0]),),
            local_files=(service.describe_local_files((str(local_path),))[0],),
        )
    )

    assert saved.display_name == "Fabric Updated"
    assert saved.created_at_utc == timestamp
    assert sorted(jar.filename for jar in saved.jars) == ["extra.jar", "managed.jar"]
    assert repository.saved_bytes == {"managed.jar": managed_bytes, "extra.jar": local_bytes}


def test_editor_rejects_deleting_active_mod_list() -> None:
    repository = FakeModRepository()
    live_store = FakeLiveModsStore(
        active_record=ActiveModListsRecord(
            slugs_in_order=("fabric",),
            applied_at_utc=datetime.now(timezone.utc),
            applied_files=(),
        )
    )
    service = ModEditorService(repository, live_store)

    with pytest.raises(ValueError, match="active set"):
        service.delete_mod_list("fabric")


def test_activation_applies_last_list_wins() -> None:
    timestamp = datetime(2026, 4, 21, tzinfo=timezone.utc)
    base_shared = b"base-shared"
    late_shared = b"late-shared"
    base_unique = b"base-only"
    repository = FakeModRepository(
        manifests=(
            ModListManifest(
                slug="base",
                display_name="Base",
                created_at_utc=timestamp,
                updated_at_utc=timestamp,
                jars=(
                    ModJarMetadata("shared.jar", len(base_shared), sha256_bytes(base_shared)),
                    ModJarMetadata("base.jar", len(base_unique), sha256_bytes(base_unique)),
                ),
            ),
            ModListManifest(
                slug="late",
                display_name="Late",
                created_at_utc=timestamp,
                updated_at_utc=timestamp,
                jars=(ModJarMetadata("shared.jar", len(late_shared), sha256_bytes(late_shared)),),
            ),
        ),
        bytes_by_slug={
            "base": {"shared.jar": base_shared, "base.jar": base_unique},
            "late": {"shared.jar": late_shared},
        },
    )
    live_store = FakeLiveModsStore()
    service = ModActivationService(repository, live_store)

    service.apply_active_mod_lists(("base", "late"))

    assert live_store.replaced_live_mods == {
        "base.jar": base_unique,
        "shared.jar": late_shared,
    }
    assert live_store.saved_active_record is not None
    assert live_store.saved_active_record.slugs_in_order == ("base", "late")
    shared = next(
        item
        for item in live_store.saved_active_record.applied_files
        if item.filename == "shared.jar"
    )
    assert shared.source_list_slug == "late"


def existing_to_managed_file(metadata: ModJarMetadata):
    from mc_server_manager.domain.models import ManagedModFile

    return ManagedModFile(filename=metadata.filename, sha256=metadata.sha256)
