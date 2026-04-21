from __future__ import annotations

from mc_server_manager.domain.models import (
    ActiveModListsRecord,
    AppliedModFileRecord,
    ModFileFingerprint,
    ModJarMetadata,
    ModListDetail,
    ModListManifest,
    ModListStatus,
    ModListSummary,
)
from mc_server_manager.services.mod_resolution import resolve_active_mods


class ModCatalogService:
    def __init__(self, mod_repository, live_mods_store) -> None:
        self._mod_repository = mod_repository
        self._live_mods_store = live_mods_store

    def get_mod_lists(self) -> list[ModListSummary]:
        manifests = self._list_manifests()
        manifests_by_slug = {manifest.slug: manifest for manifest in manifests}
        active_record = self._live_mods_store.get_active_mod_lists()
        active_slugs = _active_slugs_from_record(active_record, manifests_by_slug)
        resolved = resolve_active_mods(manifests_by_slug, active_slugs)
        live_matches, desired_matches = self._status_matches(
            active_record=active_record,
            active_slugs=active_slugs,
            desired_files=resolved.effective_files,
        )

        summaries: list[ModListSummary] = []
        for manifest in manifests:
            summaries.append(
                ModListSummary(
                    manifest=manifest,
                    status=_resolve_status(
                        manifest.slug,
                        active_slugs,
                        live_matches,
                        desired_matches,
                    ),
                    active_position=_active_position(manifest.slug, active_slugs),
                    included_count=resolved.included_counts.get(manifest.slug, 0),
                    overridden_count=resolved.overridden_counts.get(manifest.slug, 0),
                )
            )
        return summaries

    def get_mod_list(self, slug: str) -> ModListDetail | None:
        manifest = self._mod_repository.get_mod_list(slug)
        if manifest is None:
            return None

        manifests = self._list_manifests()
        manifests_by_slug = {item.slug: item for item in manifests}
        manifests_by_slug[manifest.slug] = manifest

        active_record = self._live_mods_store.get_active_mod_lists()
        active_slugs = _active_slugs_from_record(active_record, manifests_by_slug)
        resolved = resolve_active_mods(manifests_by_slug, active_slugs)
        live_matches, desired_matches = self._status_matches(
            active_record=active_record,
            active_slugs=active_slugs,
            desired_files=resolved.effective_files,
            target_slug=slug,
        )

        return ModListDetail(
            manifest=manifest,
            status=_resolve_status(
                slug,
                active_slugs,
                live_matches,
                desired_matches,
            ),
            active_position=_active_position(slug, active_slugs),
            jars=resolved.jar_views_by_slug.get(
                slug,
                tuple(_default_jar_view(jar) for jar in manifest.jars),
            ),
        )

    def get_active_slugs(self) -> tuple[str, ...]:
        manifests_by_slug = {manifest.slug: manifest for manifest in self._list_manifests()}
        return _active_slugs_from_record(
            self._live_mods_store.get_active_mod_lists(), manifests_by_slug
        )

    def _list_manifests(self) -> list[ModListManifest]:
        return sorted(
            self._mod_repository.list_mod_lists(),
            key=lambda manifest: manifest.display_name.lower(),
        )

    def _status_matches(
        self,
        *,
        active_record: ActiveModListsRecord | None,
        active_slugs: tuple[str, ...],
        desired_files,
        target_slug: str | None = None,
    ) -> tuple[bool, bool]:
        if active_record is None or not active_slugs:
            return True, True
        if target_slug is not None and target_slug not in active_slugs:
            return True, True

        live_mods = self._live_mods_store.list_live_mod_fingerprints()
        return (
            _live_matches_record(active_record, live_mods),
            _desired_matches_record(active_record, desired_files),
        )


def _default_jar_view(jar: ModJarMetadata):
    from mc_server_manager.domain.models import ModJarStatus, ModJarView

    return ModJarView(metadata=jar, status=ModJarStatus.INCLUDED)


def _active_slugs_from_record(
    active_record: ActiveModListsRecord | None,
    manifests_by_slug: dict[str, ModListManifest],
) -> tuple[str, ...]:
    if active_record is None:
        return ()
    return tuple(slug for slug in active_record.slugs_in_order if slug in manifests_by_slug)


def _active_position(slug: str, active_slugs: tuple[str, ...]) -> int | None:
    try:
        return active_slugs.index(slug) + 1
    except ValueError:
        return None


def _resolve_status(
    slug: str,
    active_slugs: tuple[str, ...],
    live_matches_record: bool,
    desired_matches_record: bool,
) -> ModListStatus:
    if slug not in active_slugs:
        return ModListStatus.INACTIVE
    if not live_matches_record:
        return ModListStatus.UNMANAGED_LIVE
    if not desired_matches_record:
        return ModListStatus.PENDING_APPLY
    return ModListStatus.ACTIVE


def _live_matches_record(
    active_record: ActiveModListsRecord | None,
    live_mods: tuple[ModFileFingerprint, ...],
) -> bool:
    if active_record is None:
        return not live_mods
    if active_record.live_files:
        return _mod_tuples_from_fingerprints(
            active_record.live_files
        ) == _mod_tuples_from_fingerprints(live_mods)
    return _mod_tuples_from_record_sizes(
        active_record.applied_files
    ) == _mod_tuples_from_fingerprint_sizes(live_mods)


def _desired_matches_record(
    active_record: ActiveModListsRecord | None,
    desired_files,
) -> bool:
    if active_record is None:
        return not desired_files
    return _mod_tuples_from_record(active_record.applied_files) == _mod_tuples_from_record(
        desired_files
    )


def _mod_tuples_from_record(records) -> tuple[tuple[str, str, int], ...]:
    return tuple(sorted((item.filename, item.sha256, item.size_bytes) for item in records))


def _mod_tuples_from_fingerprints(
    records: tuple[ModFileFingerprint, ...],
) -> tuple[tuple[str, int, int], ...]:
    return tuple(
        sorted(
            (
                item.filename,
                item.size_bytes,
                item.modified_time_epoch_seconds,
            )
            for item in records
        )
    )


def _mod_tuples_from_record_sizes(
    records: tuple[AppliedModFileRecord, ...],
) -> tuple[tuple[str, int], ...]:
    return tuple(sorted((item.filename, item.size_bytes) for item in records))


def _mod_tuples_from_fingerprint_sizes(
    records: tuple[ModFileFingerprint, ...],
) -> tuple[tuple[str, int], ...]:
    return tuple(
        sorted(
            (
                item.filename,
                item.size_bytes,
            )
            for item in records
        )
    )
