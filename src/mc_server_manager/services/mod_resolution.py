from __future__ import annotations

from dataclasses import dataclass

from mc_server_manager.domain.models import (
    AppliedModFileRecord,
    ModJarStatus,
    ModJarView,
    ModListManifest,
)


@dataclass(frozen=True, slots=True)
class ResolvedModComposition:
    effective_files: tuple[AppliedModFileRecord, ...]
    jar_views_by_slug: dict[str, tuple[ModJarView, ...]]
    included_counts: dict[str, int]
    overridden_counts: dict[str, int]


def resolve_active_mods(
    manifests_by_slug: dict[str, ModListManifest],
    slugs_in_order: tuple[str, ...],
) -> ResolvedModComposition:
    active_slugs = tuple(slug for slug in slugs_in_order if slug in manifests_by_slug)
    display_names = {
        slug: manifests_by_slug[slug].display_name
        for slug in active_slugs
        if slug in manifests_by_slug
    }

    winning_slug_by_filename: dict[str, str] = {}
    for slug in active_slugs:
        manifest = manifests_by_slug[slug]
        for jar in manifest.jars:
            winning_slug_by_filename[jar.filename] = slug

    effective_files: list[AppliedModFileRecord] = []
    jar_views_by_slug: dict[str, tuple[ModJarView, ...]] = {}
    included_counts: dict[str, int] = {}
    overridden_counts: dict[str, int] = {}

    for slug in active_slugs:
        manifest = manifests_by_slug[slug]
        jar_views: list[ModJarView] = []
        included = 0
        overridden = 0

        for jar in manifest.jars:
            winner_slug = winning_slug_by_filename[jar.filename]
            if winner_slug == slug:
                included += 1
                effective_files.append(
                    AppliedModFileRecord(
                        filename=jar.filename,
                        source_list_slug=slug,
                        sha256=jar.sha256,
                        size_bytes=jar.size_bytes,
                    )
                )
                jar_views.append(
                    ModJarView(
                        metadata=jar,
                        status=ModJarStatus.INCLUDED,
                    )
                )
                continue

            overridden += 1
            jar_views.append(
                ModJarView(
                    metadata=jar,
                    status=ModJarStatus.OVERRIDDEN,
                    overridden_by_slug=winner_slug,
                    overridden_by_display_name=display_names.get(winner_slug),
                )
            )

        included_counts[slug] = included
        overridden_counts[slug] = overridden
        jar_views_by_slug[slug] = tuple(jar_views)

    effective_files.sort(key=lambda item: item.filename.lower())
    return ResolvedModComposition(
        effective_files=tuple(effective_files),
        jar_views_by_slug=jar_views_by_slug,
        included_counts=included_counts,
        overridden_counts=overridden_counts,
    )
