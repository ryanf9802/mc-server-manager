from types import SimpleNamespace

from mc_server_manager import installer_main
from mc_server_manager import main as app_main


class FakeRoot:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    def withdraw(self) -> None:
        self._events.append("withdraw")

    def destroy(self) -> None:
        self._events.append("destroy")


def test_main_applies_icon_before_withdraw(monkeypatch) -> None:
    events: list[str] = []
    root = FakeRoot(events)
    monkeypatch.setattr(app_main, "configure_logging", lambda _name: "app.log")
    monkeypatch.setattr(
        app_main, "configure_windows_app_identity", lambda _kind: events.append("identity")
    )
    monkeypatch.setattr(app_main.tk, "Tk", lambda: root)
    monkeypatch.setattr(app_main, "apply_window_icon", lambda _window: events.append("apply"))
    monkeypatch.setattr(app_main, "AppStateStore", lambda: object())
    monkeypatch.setattr(app_main, "_load_or_initialize_state", lambda _root, _store: (None, None))

    assert app_main.main() == 0
    assert events[:3] == ["identity", "apply", "withdraw"]


def test_installer_main_applies_icon_before_withdraw(monkeypatch) -> None:
    events: list[str] = []
    root = FakeRoot(events)
    monkeypatch.setattr(installer_main, "configure_logging", lambda _name: "installer.log")
    monkeypatch.setattr(
        installer_main, "configure_windows_app_identity", lambda _kind: events.append("identity")
    )
    monkeypatch.setattr(installer_main.tk, "Tk", lambda: root)
    monkeypatch.setattr(installer_main, "apply_window_icon", lambda _window: events.append("apply"))
    monkeypatch.setattr(
        installer_main,
        "_parse_args",
        lambda: SimpleNamespace(wait_pid=None, release_tag="", silent=True),
    )
    monkeypatch.setattr(
        installer_main,
        "load_build_info",
        lambda: SimpleNamespace(is_dev=True, repo_owner="", repo_name=""),
    )
    monkeypatch.setattr(installer_main, "_show_error", lambda _message, _root: None)

    assert installer_main.main() == 1
    assert events[:3] == ["identity", "apply", "withdraw"]


def test_installer_launch_uses_app_directory_as_cwd(monkeypatch, tmp_path) -> None:
    captured: dict[str, object] = {}
    app_path = tmp_path / "install" / "current" / "mc-server-manager.exe"

    def fake_popen(args, close_fds, creationflags=0, cwd=None):  # noqa: ANN001
        captured["args"] = args
        captured["close_fds"] = close_fds
        captured["creationflags"] = creationflags
        captured["cwd"] = cwd

        class _Process:
            pass

        return _Process()

    monkeypatch.setattr(installer_main.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(installer_main.sys, "platform", "win32")
    monkeypatch.setattr(installer_main.subprocess, "DETACHED_PROCESS", 0x00000008, raising=False)
    monkeypatch.setattr(
        installer_main.subprocess,
        "CREATE_NEW_PROCESS_GROUP",
        0x00000200,
        raising=False,
    )

    installer_main._launch(app_path)

    assert captured["args"] == [str(app_path)]
    assert captured["close_fds"] is True
    assert captured["cwd"] == str(app_path.parent)
