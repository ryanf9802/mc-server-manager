from datetime import datetime, timezone

from mc_server_manager.domain.models import (
    ActiveModListsRecord,
    AppliedModFileRecord,
    ModFileFingerprint,
    ModJarStatus,
    ModJarMetadata,
    ModListManifest,
    ModListStatus,
)
from mc_server_manager.services.mod_catalog import ModCatalogService


class FakeModRepository:
    def __init__(self, manifests) -> None:
        self._manifests = list(manifests)

    def list_mod_lists(self):
        return list(self._manifests)

    def get_mod_list(self, slug: str):
        return next((item for item in self._manifests if item.slug == slug), None)


class FakeLiveModsStore:
    def __init__(self, live_fingerprints, active_record) -> None:
        self._live_fingerprints = tuple(live_fingerprints)
        self._active_record = active_record

    def list_live_mod_fingerprints(self):
        return self._live_fingerprints

    def get_active_mod_lists(self):
        return self._active_record


class GuardedLiveModsStore(FakeLiveModsStore):
    def list_live_mod_fingerprints(self):
        raise AssertionError("list_live_mod_fingerprints should not be called")


def test_catalog_marks_active_lists_and_conflicts() -> None:
    timestamp = datetime.now(timezone.utc)
    base = _manifest(
        "base",
        "Base",
        timestamp,
        (
            ModJarMetadata("shared.jar", 101, "SHA-BASE-SHARED"),
            ModJarMetadata("base-only.jar", 102, "SHA-BASE-ONLY"),
        ),
    )
    extra = _manifest(
        "extra",
        "Extra",
        timestamp,
        (
            ModJarMetadata("shared.jar", 201, "SHA-EXTRA-SHARED"),
            ModJarMetadata("extra-only.jar", 202, "SHA-EXTRA-ONLY"),
        ),
    )
    active_record = ActiveModListsRecord(
        slugs_in_order=("base", "extra"),
        applied_at_utc=timestamp,
        applied_files=(
            AppliedModFileRecord("base-only.jar", "base", "SHA-BASE-ONLY", 102),
            AppliedModFileRecord("extra-only.jar", "extra", "SHA-EXTRA-ONLY", 202),
            AppliedModFileRecord("shared.jar", "extra", "SHA-EXTRA-SHARED", 201),
        ),
    )
    live_mods = (
        ModFileFingerprint("base-only.jar", 102, 1700000102),
        ModFileFingerprint("extra-only.jar", 202, 1700000202),
        ModFileFingerprint("shared.jar", 201, 1700000201),
    )
    service = ModCatalogService(
        FakeModRepository((base, extra)),
        FakeLiveModsStore(
            live_mods,
            ActiveModListsRecord(
                slugs_in_order=active_record.slugs_in_order,
                applied_at_utc=active_record.applied_at_utc,
                applied_files=active_record.applied_files,
                live_files=live_mods,
            ),
        ),
    )

    summaries = service.get_mod_lists()
    detail = service.get_mod_list("base")

    assert [item.status for item in summaries] == [ModListStatus.ACTIVE, ModListStatus.ACTIVE]
    assert summaries[0].included_count == 1
    assert summaries[0].overridden_count == 1
    assert summaries[1].included_count == 2
    assert summaries[1].overridden_count == 0
    assert detail is not None
    shared = next(item for item in detail.jars if item.metadata.filename == "shared.jar")
    assert shared.status is ModJarStatus.OVERRIDDEN
    assert shared.overridden_by_slug == "extra"
    assert shared.overridden_by_display_name == "Extra"


def test_catalog_marks_active_lists_pending_when_managed_copy_changes() -> None:
    timestamp = datetime.now(timezone.utc)
    current = _manifest(
        "fabric",
        "Fabric",
        timestamp,
        (ModJarMetadata("mod.jar", 200, "SHA-NEW"),),
    )
    active_record = ActiveModListsRecord(
        slugs_in_order=("fabric",),
        applied_at_utc=timestamp,
        applied_files=(AppliedModFileRecord("mod.jar", "fabric", "SHA-OLD", 100),),
    )
    live_mods = (ModFileFingerprint("mod.jar", 100, 1700000001),)
    service = ModCatalogService(
        FakeModRepository((current,)),
        FakeLiveModsStore(
            live_mods,
            ActiveModListsRecord(
                slugs_in_order=active_record.slugs_in_order,
                applied_at_utc=active_record.applied_at_utc,
                applied_files=active_record.applied_files,
                live_files=live_mods,
            ),
        ),
    )

    summaries = service.get_mod_lists()

    assert summaries[0].status is ModListStatus.PENDING_APPLY


def test_catalog_marks_active_lists_unmanaged_when_live_folder_drifts() -> None:
    timestamp = datetime.now(timezone.utc)
    current = _manifest(
        "fabric",
        "Fabric",
        timestamp,
        (ModJarMetadata("mod.jar", 100, "SHA-OLD"),),
    )
    active_record = ActiveModListsRecord(
        slugs_in_order=("fabric",),
        applied_at_utc=timestamp,
        applied_files=(AppliedModFileRecord("mod.jar", "fabric", "SHA-OLD", 100),),
    )
    live_mods = (ModFileFingerprint("mod.jar", 100, 1700000002),)
    service = ModCatalogService(
        FakeModRepository((current,)),
        FakeLiveModsStore(
            live_mods,
            ActiveModListsRecord(
                slugs_in_order=active_record.slugs_in_order,
                applied_at_utc=active_record.applied_at_utc,
                applied_files=active_record.applied_files,
                live_files=(ModFileFingerprint("mod.jar", 100, 1700000001),),
            ),
        ),
    )

    summaries = service.get_mod_lists()

    assert summaries[0].status is ModListStatus.UNMANAGED_LIVE


def test_catalog_skips_live_mod_scan_when_no_active_lists() -> None:
    timestamp = datetime.now(timezone.utc)
    manifest = _manifest(
        "fabric",
        "Fabric",
        timestamp,
        (ModJarMetadata("mod.jar", 100, "SHA-OLD"),),
    )
    service = ModCatalogService(
        FakeModRepository((manifest,)),
        GuardedLiveModsStore((), None),
    )

    summaries = service.get_mod_lists()
    detail = service.get_mod_list("fabric")

    assert summaries[0].status is ModListStatus.INACTIVE
    assert detail is not None
    assert detail.status is ModListStatus.INACTIVE


def test_catalog_uses_filename_and_size_for_old_active_records_without_live_snapshots() -> None:
    timestamp = datetime.now(timezone.utc)
    manifest = _manifest(
        "fabric",
        "Fabric",
        timestamp,
        (ModJarMetadata("mod.jar", 100, "SHA-OLD"),),
    )
    active_record = ActiveModListsRecord(
        slugs_in_order=("fabric",),
        applied_at_utc=timestamp,
        applied_files=(AppliedModFileRecord("mod.jar", "fabric", "SHA-OLD", 100),),
    )
    service = ModCatalogService(
        FakeModRepository((manifest,)),
        FakeLiveModsStore((ModFileFingerprint("mod.jar", 100, 1700000001),), active_record),
    )

    summaries = service.get_mod_lists()

    assert summaries[0].status is ModListStatus.ACTIVE


def _manifest(
    slug: str,
    display_name: str,
    timestamp: datetime,
    jars: tuple[ModJarMetadata, ...],
) -> ModListManifest:
    return ModListManifest(
        slug=slug,
        display_name=display_name,
        created_at_utc=timestamp,
        updated_at_utc=timestamp,
        jars=jars,
    )
