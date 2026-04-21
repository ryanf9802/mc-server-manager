from pathlib import Path

import httpx

from mc_server_manager.infrastructure.releases import GitHubReleaseClient


def test_release_client_parses_latest_release() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/repos/ryanf9802/mc-server-manager/releases/latest"
        return httpx.Response(
            200,
            json={
                "tag_name": "main-12-abcdef0",
                "published_at": "2026-04-21T12:00:00Z",
                "html_url": "https://github.com/ryanf9802/mc-server-manager/releases/tag/main-12-abcdef0",
                "assets": [
                    {
                        "name": "mc-server-manager-windows-x64.zip",
                        "browser_download_url": "https://example.com/bundle.zip",
                        "size": 123,
                        "content_type": "application/zip",
                    }
                ],
            },
        )

    client = GitHubReleaseClient(
        "ryanf9802",
        "mc-server-manager",
        http_client_factory=lambda: httpx.Client(transport=httpx.MockTransport(handler)),
    )

    release = client.latest_release()

    assert release.tag_name == "main-12-abcdef0"
    assert release.get_asset("mc-server-manager-windows-x64.zip") is not None


def test_release_client_downloads_asset(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"zip-bytes")

    client = GitHubReleaseClient(
        "ryanf9802",
        "mc-server-manager",
        http_client_factory=lambda: httpx.Client(transport=httpx.MockTransport(handler)),
    )
    asset_path = tmp_path / "bundle.zip"
    asset = client.latest_release.__annotations__  # sentinel to avoid redefining asset type
    del asset

    from mc_server_manager.domain.models import ReleaseAsset

    client.download_asset(
        ReleaseAsset(
            name="bundle.zip",
            browser_download_url="https://example.com/bundle.zip",
            size_bytes=9,
            content_type="application/zip",
        ),
        asset_path,
    )

    assert asset_path.read_bytes() == b"zip-bytes"
