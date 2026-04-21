from datetime import datetime, timezone
from pathlib import Path

import pytest

from mc_server_manager.domain.models import (
    ActiveModListsRecord,
    LiveModFile,
    ModFileFingerprint,
    ModJarMetadata,
    ModListManifest,
    ModListSaveRequest,
)
from mc_server_manager.services.hashing import sha256_bytes
from mc_server_manager.services.mod_activation import ModActivationService
from mc_server_manager.services.mod_editor import ModEditorService


class FakeModRepository:
    def __init__(self, manifests=(), bytes_by_slug=None, live_bytes_by_filename=None) -> None:
        self._manifests = {manifest.slug: manifest for manifest in manifests}
        self._bytes_by_slug = bytes_by_slug or {}
        self._live_bytes_by_filename = live_bytes_by_filename or {}
        self.saved_manifest = None
        self.saved_request = None
        self.saved_existing_manifest = None
        self.deleted_slug = None
        self.read_requests: list[tuple[str, str]] = []
        self.materialized_files = None

    def list_mod_lists(self):
        return list(self._manifests.values())

    def get_mod_list(self, slug: str):
        return self._manifests.get(slug)

    def read_mod_bytes(self, slug: str, filename: str) -> bytes:
        self.read_requests.append((slug, filename))
        return self._bytes_by_slug[slug][filename]

    def materialize_mod_files(self, applied_files):
        self.materialized_files = tuple(applied_files)
        return {
            item.filename: self._bytes_by_slug[item.source_list_slug][item.filename]
            for item in applied_files
        }

    def save_mod_list(self, request, existing_manifest):
        self.saved_request = request
        self.saved_existing_manifest = existing_manifest
        existing_metadata = (
            {jar.filename: jar for jar in existing_manifest.jars}
            if existing_manifest is not None
            else {}
        )
        jars: list[ModJarMetadata] = []
        for managed_file in request.managed_files:
            jars.append(existing_metadata[managed_file.filename])
        for live_file in request.live_files:
            content = self._live_bytes_by_filename[live_file.filename]
            jars.append(
                ModJarMetadata(
                    filename=live_file.filename,
                    size_bytes=len(content),
                    sha256=sha256_bytes(content),
                )
            )
        for local_file in request.local_files:
            content = Path(local_file.local_path).read_bytes()
            jars.append(
                ModJarMetadata(
                    filename=local_file.filename,
                    size_bytes=len(content),
                    sha256=sha256_bytes(content),
                )
            )
        manifest = ModListManifest(
            slug=request.slug,
            display_name=request.display_name,
            created_at_utc=existing_manifest.created_at_utc
            if existing_manifest is not None
            else request.created_at_utc,
            updated_at_utc=datetime.now(timezone.utc),
            jars=tuple(sorted(jars, key=lambda item: item.filename.lower())),
        )
        self.saved_manifest = manifest
        self._manifests[manifest.slug] = manifest
        return manifest

    def delete_mod_list(self, slug: str) -> None:
        self.deleted_slug = slug
        self._manifests.pop(slug, None)
        self._bytes_by_slug.pop(slug, None)


class FakeLiveModsStore:
    def __init__(
        self,
        live_fingerprints=(),
        live_bytes_by_filename=None,
        active_record=None,
    ) -> None:
        self._live_fingerprints = tuple(live_fingerprints)
        self._live_bytes_by_filename = live_bytes_by_filename or {}
        self._active_record = active_record
        self.replaced_live_mods = None
        self.saved_active_record = None

    def list_live_mod_fingerprints(self):
        return self._live_fingerprints

    def get_active_mod_lists(self):
        return self._active_record

    def replace_live_mods(self, jar_bytes_by_filename):
        self.replaced_live_mods = dict(jar_bytes_by_filename)
        self._live_bytes_by_filename = dict(jar_bytes_by_filename)
        self._live_fingerprints = tuple(
            ModFileFingerprint(filename, len(content), 1700000000 + index)
            for index, (filename, content) in enumerate(
                sorted(jar_bytes_by_filename.items(), key=lambda item: item[0].lower()),
                start=1,
            )
        )
        return self._live_fingerprints

    def save_active_mod_lists(self, record):
        self.saved_active_record = record
        self._active_record = record


def test_editor_saves_local_and_managed_files_without_redownloading_managed_bytes(tmp_path) -> None:
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
    assert repository.saved_request is not None
    assert repository.saved_request.managed_files == (
        existing_to_managed_file(existing.jars[0]),
    )
    assert repository.read_requests == []


def test_editor_creates_live_draft_and_saves_live_snapshot_without_managed_reads() -> None:
    timestamp = datetime(2026, 4, 21, tzinfo=timezone.utc)
    live_bytes = {"live.jar": b"live-bytes"}
    live_fingerprints = (
        ModFileFingerprint("live.jar", len(live_bytes["live.jar"]), 1700000001),
    )
    repository = FakeModRepository(live_bytes_by_filename=live_bytes)
    service = ModEditorService(
        repository,
        FakeLiveModsStore(
            live_fingerprints=live_fingerprints,
            live_bytes_by_filename=live_bytes,
        ),
    )

    draft, live_files = service.create_draft_from_live("Live Snapshot")
    saved = service.save_mod_list(
        ModListSaveRequest(
            slug=draft.slug,
            display_name=draft.display_name,
            created_at_utc=timestamp,
            live_files=live_files,
        )
    )

    assert draft.jars == ()
    assert live_files == (
        LiveModFile("live.jar", len(live_bytes["live.jar"]), 1700000001),
    )
    assert [jar.filename for jar in saved.jars] == ["live.jar"]
    assert repository.saved_request is not None
    assert repository.saved_request.live_files == live_files
    assert repository.read_requests == []


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


def test_activation_applies_last_list_wins_and_records_live_fingerprints() -> None:
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

    assert repository.materialized_files is not None
    assert live_store.replaced_live_mods == {
        "base.jar": base_unique,
        "shared.jar": late_shared,
    }
    assert live_store.saved_active_record is not None
    assert live_store.saved_active_record.slugs_in_order == ("base", "late")
    assert tuple(item.filename for item in live_store.saved_active_record.live_files) == (
        "base.jar",
        "shared.jar",
    )
    shared = next(
        item
        for item in live_store.saved_active_record.applied_files
        if item.filename == "shared.jar"
    )
    assert shared.source_list_slug == "late"


def existing_to_managed_file(metadata: ModJarMetadata):
    from mc_server_manager.domain.models import ManagedModFile

    return ManagedModFile(filename=metadata.filename, sha256=metadata.sha256)
