from __future__ import annotations

import json
import sys
from pathlib import Path

from mc_server_manager.domain.models import BuildInfo


def load_build_info() -> BuildInfo:
    payload = _load_payload()
    if payload is None:
        return BuildInfo(
            release_tag="dev",
            commit_sha="",
            repo_owner="ryanf9802",
            repo_name="mc-server-manager",
        )
    return BuildInfo(
        release_tag=str(payload.get("release_tag", "dev")),
        commit_sha=str(payload.get("commit_sha", "")),
        repo_owner=str(payload.get("repo_owner", "")),
        repo_name=str(payload.get("repo_name", "")),
        installer_asset_name=str(
            payload.get("installer_asset_name", "mc-server-manager-installer.exe")
        ),
        bundle_asset_name=str(
            payload.get("bundle_asset_name", "mc-server-manager-windows-x64.zip")
        ),
    )


def _load_payload() -> dict[str, object] | None:
    for candidate in _candidate_paths():
        if not candidate.exists():
            continue
        return json.loads(candidate.read_text(encoding="utf-8"))
    return None


def _candidate_paths() -> tuple[Path, ...]:
    paths: list[Path] = []
    executable_dir = Path(sys.executable).resolve().parent
    paths.append(executable_dir / "build-info.json")

    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir is not None:
        paths.append(Path(bundle_dir) / "build-info.json")

    paths.append(Path(__file__).resolve().parents[3] / "build-info.json")
    return tuple(dict.fromkeys(paths))
