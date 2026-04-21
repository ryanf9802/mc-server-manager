from pathlib import Path
from types import SimpleNamespace

from mc_server_manager import app_icon


class FakeWindow:
    def __init__(self) -> None:
        self.default_icons: list[str] = []

    def iconbitmap(self, bitmap: str | None = None, default: str | None = None) -> None:
        del bitmap
        if default is not None:
            self.default_icons.append(default)


def test_resolve_app_icon_path_prefers_pyinstaller_bundle(tmp_path: Path, monkeypatch) -> None:
    bundled_icon = tmp_path / "mc_server_manager" / "assets" / "app.ico"
    bundled_icon.parent.mkdir(parents=True, exist_ok=True)
    bundled_icon.write_bytes(b"ico")
    monkeypatch.setattr(app_icon.sys, "_MEIPASS", str(tmp_path), raising=False)

    assert app_icon.resolve_app_icon_path() == bundled_icon


def test_resolve_app_icon_path_finds_repo_asset(monkeypatch) -> None:
    monkeypatch.delattr(app_icon.sys, "_MEIPASS", raising=False)

    resolved = app_icon.resolve_app_icon_path()

    assert resolved is not None
    assert resolved.name == "app.ico"
    assert resolved.exists()


def test_apply_window_icon_uses_resolved_icon_on_windows(tmp_path: Path, monkeypatch) -> None:
    icon_path = tmp_path / "app.ico"
    icon_path.write_bytes(b"ico")
    window = FakeWindow()
    monkeypatch.setattr(app_icon.sys, "platform", "win32")
    monkeypatch.setattr(app_icon, "resolve_app_icon_path", lambda: icon_path)

    assert app_icon.apply_window_icon(window) == icon_path
    assert window.default_icons == [str(icon_path)]


def test_apply_window_icon_skips_lookup_outside_windows(monkeypatch) -> None:
    called = False

    def fake_resolve() -> Path | None:
        nonlocal called
        called = True
        return None

    monkeypatch.setattr(app_icon.sys, "platform", "linux")
    monkeypatch.setattr(app_icon, "resolve_app_icon_path", fake_resolve)

    assert app_icon.apply_window_icon(FakeWindow()) is None
    assert called is False


def test_apply_window_icon_logs_when_asset_is_missing(caplog, monkeypatch) -> None:
    monkeypatch.setattr(app_icon.sys, "platform", "win32")
    monkeypatch.setattr(app_icon, "resolve_app_icon_path", lambda: None)

    assert app_icon.apply_window_icon(FakeWindow()) is None
    assert "Application icon asset is missing." in caplog.text


def test_configure_windows_app_identity_sets_process_id(monkeypatch) -> None:
    class FakeShell32:
        def __init__(self) -> None:
            self.argtypes = None
            self.restype = None
            self.calls: list[str] = []

        def SetCurrentProcessExplicitAppUserModelID(self, app_id: str) -> int:
            self.calls.append(app_id)
            return 0

    shell32 = FakeShell32()
    monkeypatch.setattr(app_icon.sys, "platform", "win32")
    monkeypatch.setattr(app_icon.ctypes, "windll", SimpleNamespace(shell32=shell32), raising=False)

    assert app_icon.configure_windows_app_identity("app") == "ryanf9802.mc-server-manager"
    assert shell32.calls == ["ryanf9802.mc-server-manager"]


def test_configure_windows_app_identity_skips_non_windows(monkeypatch) -> None:
    monkeypatch.setattr(app_icon.sys, "platform", "linux")

    assert app_icon.configure_windows_app_identity("app") is None
