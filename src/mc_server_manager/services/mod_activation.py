from __future__ import annotations

from mc_server_manager.domain.models import ActiveModListsRecord, utc_now
from mc_server_manager.services.mod_resolution import resolve_active_mods


class ModActivationService:
    def __init__(self, mod_repository, live_mods_store) -> None:
        self._mod_repository = mod_repository
        self._live_mods_store = live_mods_store

    def apply_active_mod_lists(self, slugs_in_order: tuple[str, ...]) -> None:
        unique_slugs = _unique_slugs(slugs_in_order)
        manifests_by_slug = {
            manifest.slug: manifest for manifest in self._mod_repository.list_mod_lists()
        }

        missing = [slug for slug in unique_slugs if slug not in manifests_by_slug]
        if missing:
            raise ValueError(f"Mod list '{missing[0]}' was not found.")

        resolved = resolve_active_mods(manifests_by_slug, unique_slugs)
        jar_bytes_by_filename: dict[str, bytes] = {}
        for item in resolved.effective_files:
            jar_bytes_by_filename[item.filename] = self._mod_repository.read_mod_bytes(
                item.source_list_slug,
                item.filename,
            )

        self._live_mods_store.replace_live_mods(jar_bytes_by_filename)
        self._live_mods_store.save_active_mod_lists(
            ActiveModListsRecord(
                slugs_in_order=unique_slugs,
                applied_at_utc=utc_now(),
                applied_files=resolved.effective_files,
            )
        )


def _unique_slugs(slugs_in_order: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for slug in slugs_in_order:
        if slug in seen:
            continue
        seen.add(slug)
        ordered.append(slug)
    return tuple(ordered)
