from __future__ import annotations

import ctypes
import logging
import sys
from pathlib import Path
from typing import Literal
from typing import Protocol


logger = logging.getLogger(__name__)

_ICON_NAME = "app.ico"
_APP_USER_MODEL_IDS = {
    "app": "ryanf9802.mc-server-manager",
    "installer": "ryanf9802.mc-server-manager.installer",
}


class SupportsIconBitmap(Protocol):
    def iconbitmap(self, bitmap: str | None = None, default: str | None = None) -> object: ...


def configure_windows_app_identity(kind: Literal["app", "installer"]) -> str | None:
    if sys.platform != "win32":
        return None

    app_id = _APP_USER_MODEL_IDS[kind]
    try:
        shell32 = ctypes.windll.shell32
        set_app_id = shell32.SetCurrentProcessExplicitAppUserModelID
        try:
            set_app_id.argtypes = [ctypes.c_wchar_p]
            set_app_id.restype = ctypes.c_long
        except Exception:  # noqa: BLE001
            pass
        result = set_app_id(app_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to configure Windows AppUserModelID %s: %s", app_id, exc)
        return None

    if result != 0:
        logger.warning(
            "SetCurrentProcessExplicitAppUserModelID returned %s for %s.",
            hex(result & 0xFFFFFFFF),
            app_id,
        )
        return None
    return app_id


def resolve_app_icon_path() -> Path | None:
    for candidate in _candidate_icon_paths():
        if candidate.exists():
            return candidate
    return None


def apply_window_icon(window: SupportsIconBitmap) -> Path | None:
    if sys.platform != "win32":
        return None

    icon_path = resolve_app_icon_path()
    if icon_path is None:
        logger.warning("Application icon asset is missing.")
        return None

    try:
        window.iconbitmap(default=str(icon_path))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to apply application icon from %s: %s", icon_path, exc)
        return None
    return icon_path


def _candidate_icon_paths() -> tuple[Path, ...]:
    paths: list[Path] = []

    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir is not None:
        paths.append(Path(bundle_dir) / "mc_server_manager" / "assets" / _ICON_NAME)

    paths.append(Path(__file__).resolve().parent / "assets" / _ICON_NAME)
    return tuple(dict.fromkeys(paths))
