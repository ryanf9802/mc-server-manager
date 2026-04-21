from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

import httpx

from mc_server_manager.domain.models import GitHubRelease, ReleaseAsset


class GitHubReleaseClient:
    def __init__(
        self,
        owner: str,
        repo: str,
        http_client_factory: Callable[[], httpx.Client] | None = None,
    ) -> None:
        self._owner = owner
        self._repo = repo
        self._http_client_factory = http_client_factory or self._default_http_client_factory
        self._base_url = f"https://api.github.com/repos/{owner}/{repo}"

    def latest_release(self) -> GitHubRelease:
        payload = self._request_json("/releases/latest")
        return _parse_release(payload)

    def get_release_by_tag(self, tag: str) -> GitHubRelease:
        payload = self._request_json(f"/releases/tags/{tag}")
        return _parse_release(payload)

    def download_asset(self, asset: ReleaseAsset, destination: Path) -> None:
        with self._http_client_factory() as client:
            try:
                with client.stream(
                    "GET",
                    asset.browser_download_url,
                    headers=self._headers(),
                    follow_redirects=True,
                ) as response:
                    response.raise_for_status()
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with destination.open("wb") as handle:
                        for chunk in response.iter_bytes():
                            handle.write(chunk)
            except httpx.HTTPStatusError as exc:
                raise ConnectionError(
                    f"Failed to download release asset with status {exc.response.status_code}."
                ) from exc
            except httpx.HTTPError as exc:
                raise ConnectionError(f"Failed to download release asset: {exc}") from exc

    def _request_json(self, path: str) -> dict[str, object]:
        with self._http_client_factory() as client:
            try:
                response = client.get(f"{self._base_url}{path}", headers=self._headers())
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    raise ConnectionError("GitHub release was not found.") from exc
                raise ConnectionError(
                    f"GitHub release request failed with status {exc.response.status_code}."
                ) from exc
            except httpx.HTTPError as exc:
                raise ConnectionError(f"GitHub release request failed: {exc}") from exc
        return cast(dict[str, object], response.json())

    @staticmethod
    def _default_http_client_factory() -> httpx.Client:
        return httpx.Client(timeout=30.0)

    @staticmethod
    def _headers() -> dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "User-Agent": "mc-server-manager",
        }


def _parse_release(payload: dict[str, object]) -> GitHubRelease:
    assets_payload = payload.get("assets")
    assets = tuple(
        ReleaseAsset(
            name=str(asset_map.get("name", "")),
            browser_download_url=str(asset_map.get("browser_download_url", "")),
            size_bytes=_to_int(asset_map.get("size", 0)),
            content_type=str(asset_map.get("content_type", "")),
        )
        for asset in _as_list(assets_payload)
        if (asset_map := _as_mapping(asset))
    )
    return GitHubRelease(
        tag_name=str(payload.get("tag_name", "")),
        published_at_utc=_parse_datetime(str(payload.get("published_at", ""))),
        html_url=str(payload.get("html_url", "")),
        assets=assets,
    )


def _as_list(value: object) -> list[object]:
    if isinstance(value, list):
        return cast(list[object], value)
    return []


def _as_mapping(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return cast(dict[str, object], value)
    return {}


def _parse_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    if not normalized:
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(normalized)


def _to_int(value: object) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0
