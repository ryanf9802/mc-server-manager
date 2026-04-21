from __future__ import annotations

import json
import stat
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from mc_server_manager.domain.models import (
    ActiveModListsRecord,
    ActiveWorldRecord,
    AppliedModFileRecord,
    LiveModFile,
    ModFileFingerprint,
    ModJarMetadata,
    ModListManifest,
    ModListSaveRequest,
    WorldFileSet,
    WorldManifest,
    utc_now,
)
from mc_server_manager.infrastructure.remote_paths import RemotePaths
from mc_server_manager.infrastructure.sftp_gateway import SftpGateway


class SftpWorldRepository:
    def __init__(self, gateway: SftpGateway, paths: RemotePaths) -> None:
        self._gateway = gateway
        self._paths = paths

    def list_worlds(self) -> list[WorldManifest]:
        with self._gateway.session() as sftp:
            if not self._gateway.exists(sftp, self._paths.worlds_root):
                return []

            manifests: list[WorldManifest] = []
            for entry in sftp.listdir_attr(self._paths.worlds_root):
                if not stat.S_ISDIR(entry.st_mode):
                    continue
                manifest_path = self._paths.world_manifest_path(entry.filename)
                if not self._gateway.exists(sftp, manifest_path):
                    continue
                manifests.append(
                    _manifest_from_dict(json.loads(self._gateway.read_text(sftp, manifest_path)))
                )
            return manifests

    def get_files(self, slug: str) -> WorldFileSet | None:
        with self._gateway.session() as sftp:
            server_path = self._paths.world_server_properties_path(slug)
            whitelist_path = self._paths.world_whitelist_path(slug)
            if not self._gateway.exists(sftp, server_path) or not self._gateway.exists(
                sftp, whitelist_path
            ):
                return None
            return WorldFileSet(
                server_properties_text=self._gateway.read_text(sftp, server_path),
                whitelist_json_text=self._gateway.read_text(sftp, whitelist_path),
            )

    def save_world(self, manifest: WorldManifest, files: WorldFileSet) -> None:
        with self._gateway.session() as sftp:
            self._gateway.ensure_dir(sftp, self._paths.world_root(manifest.slug))
            self._gateway.write_text(
                sftp,
                self._paths.world_manifest_path(manifest.slug),
                json.dumps(_manifest_to_dict(manifest), indent=2),
            )
            self._gateway.write_text(
                sftp,
                self._paths.world_server_properties_path(manifest.slug),
                files.server_properties_text,
            )
            self._gateway.write_text(
                sftp, self._paths.world_whitelist_path(manifest.slug), files.whitelist_json_text
            )

    def delete_world(self, slug: str) -> None:
        with self._gateway.session() as sftp:
            root = self._paths.world_root(slug)
            if self._gateway.exists(sftp, root):
                self._gateway.remove_tree(sftp, root)


class SftpLiveConfigStore:
    def __init__(self, gateway: SftpGateway, paths: RemotePaths) -> None:
        self._gateway = gateway
        self._paths = paths

    def get_live_files(self) -> WorldFileSet:
        with self._gateway.session() as sftp:
            return WorldFileSet(
                server_properties_text=self._gateway.read_text(
                    sftp,
                    self._paths.live_server_properties_path,
                    default="",
                ),
                whitelist_json_text=self._gateway.read_text(
                    sftp,
                    self._paths.live_whitelist_path,
                    default="[]",
                ),
            )

    def apply_live_files(self, files: WorldFileSet) -> None:
        with self._gateway.session() as sftp:
            self._gateway.write_text(
                sftp, self._paths.live_server_properties_path, files.server_properties_text
            )
            self._gateway.write_text(
                sftp, self._paths.live_whitelist_path, files.whitelist_json_text
            )

    def get_active_world(self) -> ActiveWorldRecord | None:
        with self._gateway.session() as sftp:
            if not self._gateway.exists(sftp, self._paths.active_world_path):
                return None
            payload = json.loads(self._gateway.read_text(sftp, self._paths.active_world_path))
            return _active_world_from_dict(payload)

    def save_active_world(self, record: ActiveWorldRecord) -> None:
        with self._gateway.session() as sftp:
            self._gateway.write_text(
                sftp,
                self._paths.active_world_path,
                json.dumps(_active_world_to_dict(record), indent=2),
            )


class SftpModRepository:
    def __init__(self, gateway: SftpGateway, paths: RemotePaths) -> None:
        self._gateway = gateway
        self._paths = paths

    def list_mod_lists(self) -> list[ModListManifest]:
        with self._gateway.session() as sftp:
            if not self._gateway.exists(sftp, self._paths.mod_lists_root):
                return []

            manifests: list[ModListManifest] = []
            for entry in sftp.listdir_attr(self._paths.mod_lists_root):
                if not stat.S_ISDIR(entry.st_mode):
                    continue
                manifest_path = self._paths.mod_list_manifest_path(entry.filename)
                if not self._gateway.exists(sftp, manifest_path):
                    continue
                manifests.append(
                    _mod_list_manifest_from_dict(
                        json.loads(self._gateway.read_text(sftp, manifest_path))
                    )
                )
            return manifests

    def get_mod_list(self, slug: str) -> ModListManifest | None:
        with self._gateway.session() as sftp:
            manifest_path = self._paths.mod_list_manifest_path(slug)
            if not self._gateway.exists(sftp, manifest_path):
                return None
            return _mod_list_manifest_from_dict(
                json.loads(self._gateway.read_text(sftp, manifest_path))
            )

    def read_mod_bytes(self, slug: str, filename: str) -> bytes:
        with self._gateway.session() as sftp:
            return self._gateway.read_bytes(sftp, self._paths.mod_list_jar_path(slug, filename))

    def materialize_mod_files(
        self, applied_files: tuple[AppliedModFileRecord, ...]
    ) -> dict[str, bytes]:
        with self._gateway.session() as sftp:
            jar_bytes_by_filename: dict[str, bytes] = {}
            for item in applied_files:
                jar_bytes_by_filename[item.filename] = self._gateway.read_bytes(
                    sftp,
                    self._paths.mod_list_jar_path(item.source_list_slug, item.filename),
                )
            return jar_bytes_by_filename

    def save_mod_list(
        self,
        request: ModListSaveRequest,
        existing_manifest: ModListManifest | None,
    ) -> ModListManifest:
        with self._gateway.session() as sftp:
            root = self._paths.mod_list_root(request.slug)
            mods_root = self._paths.mod_list_mods_root(request.slug)
            self._gateway.ensure_dir(sftp, root)
            self._gateway.ensure_dir(sftp, mods_root)

            existing_names = set()
            if self._gateway.exists(sftp, mods_root):
                for entry in sftp.listdir_attr(mods_root):
                    if stat.S_ISDIR(entry.st_mode):
                        continue
                    existing_names.add(entry.filename)

            existing_metadata = (
                {jar.filename: jar for jar in existing_manifest.jars}
                if existing_manifest is not None
                else {}
            )
            live_entries = self._live_jar_attrs_by_filename(sftp)
            final_names: set[str] = set()
            final_jars: list[ModJarMetadata] = []

            for managed_file in request.managed_files:
                metadata = existing_metadata.get(managed_file.filename)
                if metadata is None or metadata.sha256 != managed_file.sha256:
                    raise ValueError(
                        f"Managed mod '{managed_file.filename}' changed on the remote host. Reload it first."
                    )
                if not self._gateway.exists(
                    sftp, self._paths.mod_list_jar_path(request.slug, managed_file.filename)
                ):
                    raise ValueError(
                        f"Managed mod '{managed_file.filename}' is missing on the remote host. Reload it first."
                    )
                final_names.add(managed_file.filename)
                final_jars.append(metadata)

            for live_file in request.live_files:
                metadata = self._copy_live_mod_to_list(
                    sftp=sftp,
                    slug=request.slug,
                    live_file=live_file,
                    live_entries=live_entries,
                )
                final_names.add(metadata.filename)
                final_jars.append(metadata)

            for local_file in request.local_files:
                path = Path(local_file.local_path)
                if not path.is_file():
                    raise ValueError(f"Local mod file was not found: {local_file.local_path}")
                content = path.read_bytes()
                metadata = ModJarMetadata(
                    filename=local_file.filename,
                    size_bytes=len(content),
                    sha256=_sha256_bytes(content),
                )
                self._gateway.write_bytes(
                    sftp,
                    self._paths.mod_list_jar_path(request.slug, local_file.filename),
                    content,
                )
                final_names.add(metadata.filename)
                final_jars.append(metadata)

            for filename in existing_names - final_names:
                self._gateway.remove_file(sftp, self._paths.mod_list_jar_path(request.slug, filename))

            now = utc_now()
            manifest = ModListManifest(
                slug=request.slug,
                display_name=request.display_name,
                created_at_utc=existing_manifest.created_at_utc
                if existing_manifest is not None
                else request.created_at_utc or now,
                updated_at_utc=now,
                jars=tuple(sorted(final_jars, key=lambda item: item.filename.lower())),
            )
            self._gateway.write_text(
                sftp,
                self._paths.mod_list_manifest_path(manifest.slug),
                json.dumps(_mod_list_manifest_to_dict(manifest), indent=2),
            )
            return manifest

    def _copy_live_mod_to_list(
        self,
        *,
        sftp,  # noqa: ANN001
        slug: str,
        live_file: LiveModFile,
        live_entries: dict[str, object],
    ) -> ModJarMetadata:
        entry = live_entries.get(live_file.filename)
        if entry is None:
            raise ValueError(
                f"Live mod '{live_file.filename}' is no longer present on the remote host. Reload it first."
            )
        entry_size = _coerce_int(getattr(entry, "st_size"))
        entry_mtime = _coerce_int(getattr(entry, "st_mtime"))
        if (
            entry_size != live_file.size_bytes
            or entry_mtime != live_file.modified_time_epoch_seconds
        ):
            raise ValueError(
                f"Live mod '{live_file.filename}' changed on the remote host. Reload it first."
            )
        content = self._gateway.read_bytes(sftp, self._paths.live_mod_path(live_file.filename))
        metadata = ModJarMetadata(
            filename=live_file.filename,
            size_bytes=len(content),
            sha256=_sha256_bytes(content),
        )
        self._gateway.write_bytes(
            sftp,
            self._paths.mod_list_jar_path(slug, live_file.filename),
            content,
        )
        return metadata

    def _live_jar_attrs_by_filename(self, sftp) -> dict[str, object]:  # noqa: ANN001
        if not self._gateway.exists(sftp, self._paths.live_mods_root):
            return {}
        return {
            entry.filename: entry
            for entry in sftp.listdir_attr(self._paths.live_mods_root)
            if not stat.S_ISDIR(entry.st_mode) and entry.filename.lower().endswith(".jar")
        }

    def delete_mod_list(self, slug: str) -> None:
        with self._gateway.session() as sftp:
            root = self._paths.mod_list_root(slug)
            if self._gateway.exists(sftp, root):
                self._gateway.remove_tree(sftp, root)


class SftpLiveModsStore:
    def __init__(self, gateway: SftpGateway, paths: RemotePaths) -> None:
        self._gateway = gateway
        self._paths = paths

    def list_live_mod_fingerprints(self) -> tuple[ModFileFingerprint, ...]:
        with self._gateway.session() as sftp:
            return self._list_live_mod_fingerprints_in_session(sftp)

    def read_live_mod_bytes(self, filename: str) -> bytes:
        with self._gateway.session() as sftp:
            return self._gateway.read_bytes(sftp, self._paths.live_mod_path(filename))

    def replace_live_mods(
        self, jar_bytes_by_filename: dict[str, bytes]
    ) -> tuple[ModFileFingerprint, ...]:
        with self._gateway.session() as sftp:
            self._gateway.ensure_dir(sftp, self._paths.live_mods_root)
            for entry in sftp.listdir_attr(self._paths.live_mods_root):
                if stat.S_ISDIR(entry.st_mode) or not entry.filename.lower().endswith(".jar"):
                    continue
                self._gateway.remove_file(sftp, self._paths.live_mod_path(entry.filename))
            for filename, content in jar_bytes_by_filename.items():
                self._gateway.write_bytes(sftp, self._paths.live_mod_path(filename), content)
            return self._list_live_mod_fingerprints_in_session(sftp)

    def get_active_mod_lists(self) -> ActiveModListsRecord | None:
        with self._gateway.session() as sftp:
            if not self._gateway.exists(sftp, self._paths.active_mod_lists_path):
                return None
            payload = json.loads(self._gateway.read_text(sftp, self._paths.active_mod_lists_path))
            return _active_mod_lists_from_dict(payload)

    def save_active_mod_lists(self, record: ActiveModListsRecord) -> None:
        with self._gateway.session() as sftp:
            self._gateway.write_text(
                sftp,
                self._paths.active_mod_lists_path,
                json.dumps(_active_mod_lists_to_dict(record), indent=2),
            )

    def _list_live_mod_fingerprints_in_session(
        self, sftp
    ) -> tuple[ModFileFingerprint, ...]:  # noqa: ANN001
        if not self._gateway.exists(sftp, self._paths.live_mods_root):
            return ()

        jars: list[ModFileFingerprint] = []
        for entry in sftp.listdir_attr(self._paths.live_mods_root):
            if stat.S_ISDIR(entry.st_mode) or not entry.filename.lower().endswith(".jar"):
                continue
            jars.append(
                ModFileFingerprint(
                    filename=entry.filename,
                    size_bytes=_coerce_int(entry.st_size),
                    modified_time_epoch_seconds=_coerce_int(entry.st_mtime),
                )
            )
        return tuple(sorted(jars, key=lambda item: item.filename.lower()))


def _manifest_to_dict(manifest: WorldManifest) -> dict[str, str]:
    payload = asdict(manifest)
    payload["created_at_utc"] = manifest.created_at_utc.isoformat()
    payload["updated_at_utc"] = manifest.updated_at_utc.isoformat()
    return payload


def _manifest_from_dict(payload: dict[str, str]) -> WorldManifest:
    return WorldManifest(
        slug=payload["slug"],
        display_name=payload["display_name"],
        created_at_utc=datetime.fromisoformat(payload["created_at_utc"]),
        updated_at_utc=datetime.fromisoformat(payload["updated_at_utc"]),
    )


def _active_world_to_dict(record: ActiveWorldRecord) -> dict[str, str]:
    payload = asdict(record)
    payload["applied_at_utc"] = record.applied_at_utc.isoformat()
    return payload


def _active_world_from_dict(payload: dict[str, str]) -> ActiveWorldRecord:
    return ActiveWorldRecord(
        slug=payload["slug"],
        applied_at_utc=datetime.fromisoformat(payload["applied_at_utc"]),
        server_properties_sha256=payload["server_properties_sha256"],
        whitelist_sha256=payload["whitelist_sha256"],
    )


def _mod_list_manifest_to_dict(manifest: ModListManifest) -> dict[str, object]:
    return {
        "slug": manifest.slug,
        "display_name": manifest.display_name,
        "created_at_utc": manifest.created_at_utc.isoformat(),
        "updated_at_utc": manifest.updated_at_utc.isoformat(),
        "jars": [
            {
                "filename": jar.filename,
                "size_bytes": jar.size_bytes,
                "sha256": jar.sha256,
            }
            for jar in manifest.jars
        ],
    }


def _mod_list_manifest_from_dict(payload: dict[str, object]) -> ModListManifest:
    jar_payloads = payload.get("jars", [])
    if not isinstance(jar_payloads, list):
        raise ValueError("Invalid mod-list manifest payload.")
    return ModListManifest(
        slug=str(payload["slug"]),
        display_name=str(payload["display_name"]),
        created_at_utc=datetime.fromisoformat(str(payload["created_at_utc"])),
        updated_at_utc=datetime.fromisoformat(str(payload["updated_at_utc"])),
        jars=tuple(
            ModJarMetadata(
                filename=str(_mapping_item(item)["filename"]),
                size_bytes=_coerce_int(_mapping_item(item)["size_bytes"]),
                sha256=str(_mapping_item(item)["sha256"]),
            )
            for item in jar_payloads
        ),
    )


def _active_mod_lists_to_dict(record: ActiveModListsRecord) -> dict[str, object]:
    return {
        "slugs_in_order": list(record.slugs_in_order),
        "applied_at_utc": record.applied_at_utc.isoformat(),
        "applied_files": [
            {
                "filename": item.filename,
                "source_list_slug": item.source_list_slug,
                "sha256": item.sha256,
                "size_bytes": item.size_bytes,
            }
            for item in record.applied_files
        ],
        "live_files": [
            {
                "filename": item.filename,
                "size_bytes": item.size_bytes,
                "modified_time_epoch_seconds": item.modified_time_epoch_seconds,
            }
            for item in record.live_files
        ],
    }


def _active_mod_lists_from_dict(payload: dict[str, object]) -> ActiveModListsRecord:
    slugs = payload.get("slugs_in_order", [])
    files = payload.get("applied_files", [])
    live_files = payload.get("live_files", [])
    if not isinstance(slugs, list) or not isinstance(files, list) or not isinstance(
        live_files, list
    ):
        raise ValueError("Invalid active mod-lists payload.")
    return ActiveModListsRecord(
        slugs_in_order=tuple(str(slug) for slug in slugs),
        applied_at_utc=datetime.fromisoformat(str(payload["applied_at_utc"])),
        applied_files=tuple(
            AppliedModFileRecord(
                filename=str(_mapping_item(item)["filename"]),
                source_list_slug=str(_mapping_item(item)["source_list_slug"]),
                sha256=str(_mapping_item(item)["sha256"]),
                size_bytes=_coerce_int(_mapping_item(item)["size_bytes"]),
            )
            for item in files
        ),
        live_files=tuple(
            ModFileFingerprint(
                filename=str(_mapping_item(item)["filename"]),
                size_bytes=_coerce_int(_mapping_item(item)["size_bytes"]),
                modified_time_epoch_seconds=_coerce_int(
                    _mapping_item(item)["modified_time_epoch_seconds"]
                ),
            )
            for item in live_files
        ),
    )


def _mapping_item(item: object) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError("Invalid metadata payload.")
    return cast(dict[str, Any], item)


def _coerce_int(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        return int(value)
    raise ValueError("Invalid integer payload.")


def _sha256_bytes(content: bytes) -> str:
    import hashlib

    return hashlib.sha256(content).hexdigest().upper()
