from __future__ import annotations

import json
import stat
from dataclasses import asdict
from datetime import datetime

from mc_server_manager.domain.models import ActiveWorldRecord, WorldFileSet, WorldManifest
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
