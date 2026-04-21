from __future__ import annotations

from mc_server_manager.domain.models import (
    WorldDetail,
    WorldFileSet,
    WorldManifest,
    WorldStatus,
    utc_now,
)
from mc_server_manager.services.world_name import create_slug, ensure_unique_slug


class WorldEditorService:
    def __init__(
        self, world_repository, live_config_store, server_properties_validator, whitelist_validator
    ) -> None:
        self._world_repository = world_repository
        self._live_config_store = live_config_store
        self._server_properties_validator = server_properties_validator
        self._whitelist_validator = whitelist_validator

    def create_draft_from_live(self, display_name: str) -> WorldDetail:
        manifests = self._world_repository.list_worlds()
        slug = ensure_unique_slug(
            create_slug(display_name), {manifest.slug for manifest in manifests}
        )
        now = utc_now()
        live_files = self._live_config_store.get_live_files()
        return WorldDetail(
            manifest=WorldManifest(
                slug=slug,
                display_name=display_name.strip(),
                created_at_utc=now,
                updated_at_utc=now,
            ),
            files=live_files,
            status=WorldStatus.INACTIVE,
        )

    def save_world(self, detail: WorldDetail) -> WorldDetail:
        if not detail.manifest.display_name.strip():
            raise ValueError("Display name is required.")

        self._raise_for_invalid(detail.files)
        self._raise_for_duplicate_name(detail)

        existing_manifest = next(
            (
                manifest
                for manifest in self._world_repository.list_worlds()
                if manifest.slug == detail.manifest.slug
            ),
            None,
        )
        now = utc_now()
        manifest = WorldManifest(
            slug=detail.manifest.slug,
            display_name=detail.manifest.display_name.strip(),
            created_at_utc=existing_manifest.created_at_utc
            if existing_manifest
            else detail.manifest.created_at_utc,
            updated_at_utc=now,
        )
        normalized_files = WorldFileSet(
            server_properties_text=_normalize_line_endings(detail.files.server_properties_text),
            whitelist_json_text=_normalize_line_endings(detail.files.whitelist_json_text),
        )
        self._world_repository.save_world(manifest, normalized_files)
        return WorldDetail(manifest=manifest, files=normalized_files, status=detail.status)

    def delete_world(self, slug: str) -> None:
        active_record = self._live_config_store.get_active_world()
        if active_record is not None and active_record.slug == slug:
            raise ValueError("Activate a different world before deleting the active one.")
        self._world_repository.delete_world(slug)

    def _raise_for_invalid(self, files: WorldFileSet) -> None:
        server_result = self._server_properties_validator.validate(files.server_properties_text)
        whitelist_result = self._whitelist_validator.validate(files.whitelist_json_text)
        issues = [*server_result.issues, *whitelist_result.issues]
        if issues:
            raise ValueError("\n".join(issue.message for issue in issues))

    def _raise_for_duplicate_name(self, detail: WorldDetail) -> None:
        duplicate = any(
            manifest.slug != detail.manifest.slug
            and manifest.display_name.lower() == detail.manifest.display_name.strip().lower()
            for manifest in self._world_repository.list_worlds()
        )
        if duplicate:
            raise ValueError(
                f"A world named '{detail.manifest.display_name.strip()}' already exists."
            )


def _normalize_line_endings(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")
