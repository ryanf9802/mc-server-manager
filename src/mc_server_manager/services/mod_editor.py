from __future__ import annotations

from pathlib import Path

from mc_server_manager.domain.models import (
    LocalModFile,
    LiveModFile,
    ModListManifest,
    ModListSaveRequest,
    utc_now,
)
from mc_server_manager.services.world_name import create_slug, ensure_unique_slug


class ModEditorService:
    def __init__(self, mod_repository, live_mods_store) -> None:
        self._mod_repository = mod_repository
        self._live_mods_store = live_mods_store

    def create_empty_draft(self, display_name: str) -> ModListManifest:
        cleaned_name = display_name.strip()
        if not cleaned_name:
            raise ValueError("Display name is required.")
        manifests = self._mod_repository.list_mod_lists()
        slug = ensure_unique_slug(
            create_slug(cleaned_name), {manifest.slug for manifest in manifests}
        )
        now = utc_now()
        return ModListManifest(
            slug=slug,
            display_name=cleaned_name,
            created_at_utc=now,
            updated_at_utc=now,
            jars=(),
        )

    def create_draft_from_live(
        self, display_name: str
    ) -> tuple[ModListManifest, tuple[LiveModFile, ...]]:
        draft = self.create_empty_draft(display_name)
        live_files = tuple(
            LiveModFile(
                filename=item.filename,
                size_bytes=item.size_bytes,
                modified_time_epoch_seconds=item.modified_time_epoch_seconds,
            )
            for item in self._live_mods_store.list_live_mod_fingerprints()
        )
        return draft, live_files

    def save_mod_list(self, request: ModListSaveRequest) -> ModListManifest:
        display_name = request.display_name.strip()
        if not display_name:
            raise ValueError("Display name is required.")

        existing_manifests = self._mod_repository.list_mod_lists()
        self._raise_for_duplicate_name(request.slug, display_name, existing_manifests)
        seen_names: set[str] = set()

        for managed_file in request.managed_files:
            if not managed_file.filename.lower().endswith(".jar"):
                raise ValueError(f"Only .jar files are supported: {managed_file.filename}")
            if managed_file.filename in seen_names:
                raise ValueError(f"Duplicate mod filename: {managed_file.filename}")
            seen_names.add(managed_file.filename)

        for live_file in request.live_files:
            if not live_file.filename.lower().endswith(".jar"):
                raise ValueError(f"Only .jar files are supported: {live_file.filename}")
            if live_file.filename in seen_names:
                raise ValueError(f"Duplicate mod filename: {live_file.filename}")
            seen_names.add(live_file.filename)

        for local_file in request.local_files:
            if not local_file.filename.lower().endswith(".jar"):
                raise ValueError(f"Only .jar files are supported: {local_file.filename}")
            if local_file.filename in seen_names:
                raise ValueError(f"Duplicate mod filename: {local_file.filename}")
            seen_names.add(local_file.filename)
            path = Path(local_file.local_path)
            if not path.is_file():
                raise ValueError(f"Local mod file was not found: {local_file.local_path}")

        existing_manifest = next(
            (manifest for manifest in existing_manifests if manifest.slug == request.slug),
            None,
        )
        return self._mod_repository.save_mod_list(
            ModListSaveRequest(
                slug=request.slug,
                display_name=display_name,
                created_at_utc=existing_manifest.created_at_utc
                if existing_manifest is not None
                else request.created_at_utc or utc_now(),
                managed_files=request.managed_files,
                live_files=request.live_files,
                local_files=request.local_files,
            ),
            existing_manifest,
        )

    def delete_mod_list(self, slug: str) -> None:
        active_record = self._live_mods_store.get_active_mod_lists()
        if active_record is not None and slug in active_record.slugs_in_order:
            raise ValueError("Remove this mod list from the active set before deleting it.")
        self._mod_repository.delete_mod_list(slug)

    def describe_local_files(self, local_paths: tuple[str, ...]) -> tuple[LocalModFile, ...]:
        files: list[LocalModFile] = []
        seen_names: set[str] = set()

        for raw_path in local_paths:
            path = Path(raw_path)
            if not path.is_file():
                raise ValueError(f"Local mod file was not found: {raw_path}")
            if path.suffix.lower() != ".jar":
                raise ValueError(f"Only .jar files are supported: {path.name}")
            if path.name in seen_names:
                raise ValueError(f"Duplicate mod filename: {path.name}")
            seen_names.add(path.name)
            files.append(
                LocalModFile(
                    filename=path.name,
                    local_path=str(path),
                    size_bytes=path.stat().st_size,
                )
            )
        return tuple(files)

    def _raise_for_duplicate_name(
        self,
        slug: str,
        display_name: str,
        manifests: list[ModListManifest],
    ) -> None:
        duplicate = any(
            manifest.slug != slug and manifest.display_name.lower() == display_name.lower()
            for manifest in manifests
        )
        if duplicate:
            raise ValueError(f"A mod list named '{display_name}' already exists.")
