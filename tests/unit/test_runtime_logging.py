import logging
import subprocess
from pathlib import Path

from mc_server_manager.infrastructure import runtime_logging


def test_configure_logging_creates_log_file_and_records_messages(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(
        runtime_logging, "user_data_dir", lambda *_args: str(tmp_path / "app-data" / "inner")
    )

    log_path = runtime_logging.configure_logging("app.log")
    logging.getLogger("test").warning("hello log")
    for handler in logging.getLogger().handlers:
        handler.flush()

    assert log_path == tmp_path / "app-data" / "logs" / "app.log"
    assert "hello log" in log_path.read_text(encoding="utf-8")


def test_open_logs_dir_uses_platform_launcher(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        runtime_logging, "user_data_dir", lambda *_args: str(tmp_path / "app-data" / "inner")
    )
    monkeypatch.setattr(runtime_logging.sys, "platform", "linux")
    captured: dict[str, object] = {}

    def fake_run(command: list[str], check: bool) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        captured["check"] = check
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(runtime_logging.subprocess, "run", fake_run)

    logs_dir = runtime_logging.open_logs_dir()

    assert logs_dir == tmp_path / "app-data" / "logs"
    assert logs_dir.exists()
    assert captured["command"] == ["xdg-open", str(logs_dir)]
    assert captured["check"] is True
