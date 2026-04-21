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
    monkeypatch.setattr(app_main.tk, "Tk", lambda: root)
    monkeypatch.setattr(app_main, "apply_window_icon", lambda _window: events.append("apply"))
    monkeypatch.setattr(app_main, "AppStateStore", lambda: object())
    monkeypatch.setattr(app_main, "_load_or_initialize_state", lambda _root, _store: (None, None))

    assert app_main.main() == 0
    assert events[:2] == ["apply", "withdraw"]


def test_installer_main_applies_icon_before_withdraw(monkeypatch) -> None:
    events: list[str] = []
    root = FakeRoot(events)
    monkeypatch.setattr(installer_main, "configure_logging", lambda _name: "installer.log")
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
    assert events[:2] == ["apply", "withdraw"]
