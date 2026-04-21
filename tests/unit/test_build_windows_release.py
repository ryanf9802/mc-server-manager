import importlib.util
from pathlib import Path
from typing import cast


def _load_build_windows_release():
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "tools" / "packaging" / "build_windows_release.py"
    spec = importlib.util.spec_from_file_location("build_windows_release", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_run_pyinstaller_includes_icon_asset_flags(tmp_path: Path, monkeypatch) -> None:
    build_windows_release = _load_build_windows_release()
    icon_path = tmp_path / "src" / "mc_server_manager" / "assets" / "app.ico"
    icon_path.parent.mkdir(parents=True, exist_ok=True)
    icon_path.write_bytes(b"ico")

    captured: dict[str, object] = {}

    def fake_run(command: list[str], check: bool, cwd: Path) -> None:
        captured["command"] = command
        captured["check"] = check
        captured["cwd"] = cwd

    monkeypatch.setattr(build_windows_release.subprocess, "run", fake_run)

    build_windows_release._run_pyinstaller(
        tmp_path,
        tmp_path / "dist",
        tmp_path / "work",
        tmp_path / "build-info.json",
        "mc-server-manager",
        tmp_path / "src" / "mc_server_manager" / "main.py",
    )

    command = cast(list[str], captured["command"])
    assert captured["check"] is True
    assert captured["cwd"] == tmp_path
    assert "--icon" in command
    assert str(icon_path) == command[command.index("--icon") + 1]
    assert f"{tmp_path / 'build-info.json'};." in command
    assert f"{icon_path};mc_server_manager/assets" in command
