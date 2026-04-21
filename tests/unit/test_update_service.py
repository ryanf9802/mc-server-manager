from pathlib import Path

import pytest

from mc_server_manager.domain.models import (
    BuildInfo,
    GitHubRelease,
    ReleaseAsset,
    UpdateAvailability,
)
from mc_server_manager.infrastructure.installations import InstallLayoutResolver
from mc_server_manager.services.updates import UpdateService


class _FakeReleaseClient:
    def __init__(self, release: GitHubRelease) -> None:
        self._release = release

    def latest_release(self) -> GitHubRelease:
        return self._release


class _TestUpdateService(UpdateService):
    def __init__(
        self,
        build_info: BuildInfo,
        release: GitHubRelease,
        *,
        layout_resolver: InstallLayoutResolver,
        current_executable: Path,
    ) -> None:
        super().__init__(
            build_info,
            layout_resolver=layout_resolver,
            current_executable=current_executable,
        )
        self._release = release

    def _release_client(self):  # type: ignore[override]
        return _FakeReleaseClient(self._release)


def test_update_service_reports_dev_builds_as_unmanaged(tmp_path: Path) -> None:
    service = _TestUpdateService(
        BuildInfo(release_tag="dev", commit_sha="", repo_owner="", repo_name=""),
        _release("main-12-abcdef0"),
        layout_resolver=InstallLayoutResolver(
            install_root=tmp_path / "install",
            start_menu_dir=tmp_path / "start-menu",
        ),
        current_executable=tmp_path / "python",
    )

    availability = service.check_for_updates()

    assert availability.is_managed_install is False
    assert availability.is_update_available is False


def test_update_service_detects_available_update(tmp_path: Path) -> None:
    layout_resolver = InstallLayoutResolver(
        install_root=tmp_path / "install",
        start_menu_dir=tmp_path / "start-menu",
    )
    layout = layout_resolver.resolve()
    current_executable = Path(layout.current_app_exe)
    current_executable.parent.mkdir(parents=True, exist_ok=True)
    current_executable.write_text("exe", encoding="utf-8")

    service = _TestUpdateService(
        BuildInfo(
            release_tag="main-11-aaaaaaa",
            commit_sha="abc",
            repo_owner="ryanf9802",
            repo_name="mc-server-manager",
        ),
        _release("main-12-abcdef0"),
        layout_resolver=layout_resolver,
        current_executable=current_executable,
    )

    availability = service.check_for_updates()

    assert availability == UpdateAvailability(
        current_build=service.build_info,
        latest_release=_release("main-12-abcdef0"),
        is_managed_install=True,
        is_update_available=True,
        message="Update available: main-12-abcdef0",
    )


def test_update_service_launches_temp_updater_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    layout_resolver = InstallLayoutResolver(
        install_root=tmp_path / "install",
        start_menu_dir=tmp_path / "start-menu",
    )
    layout = layout_resolver.resolve()
    current_executable = Path(layout.current_app_exe)
    installer_path = Path(layout.installer_exe)
    current_executable.parent.mkdir(parents=True, exist_ok=True)
    installer_path.parent.mkdir(parents=True, exist_ok=True)
    current_executable.write_text("exe", encoding="utf-8")
    installer_path.write_text("installer", encoding="utf-8")

    service = _TestUpdateService(
        BuildInfo(
            release_tag="main-11-aaaaaaa",
            commit_sha="abc",
            repo_owner="ryanf9802",
            repo_name="mc-server-manager",
        ),
        _release("main-12-abcdef0"),
        layout_resolver=layout_resolver,
        current_executable=current_executable,
    )
    captured: dict[str, object] = {}

    def fake_popen(args, close_fds, creationflags=0, cwd=None):  # noqa: ANN001
        captured["args"] = args
        captured["close_fds"] = close_fds
        captured["creationflags"] = creationflags
        captured["cwd"] = cwd

        class _Process:
            pass

        return _Process()

    monkeypatch.setattr("subprocess.Popen", fake_popen)

    service.launch_update(_release("main-12-abcdef0"), wait_pid=4242)

    assert captured["close_fds"] is True
    command = captured["args"]
    assert isinstance(command, list)
    assert isinstance(command[0], str)
    assert command[1:] == [
        "--mode",
        "update",
        "--wait-pid",
        "4242",
        "--release-tag",
        "main-12-abcdef0",
        "--silent",
    ]
    assert Path(command[0]).exists()
    assert captured["cwd"] == str(Path(command[0]).parent)


def _release(tag_name: str) -> GitHubRelease:
    from datetime import datetime, timezone

    return GitHubRelease(
        tag_name=tag_name,
        published_at_utc=datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc),
        html_url=f"https://github.com/ryanf9802/mc-server-manager/releases/tag/{tag_name}",
        assets=(
            ReleaseAsset(
                name="mc-server-manager-windows-x64.zip",
                browser_download_url="https://example.com/bundle.zip",
                size_bytes=123,
                content_type="application/zip",
            ),
        ),
    )
