from __future__ import annotations

import logging
import sys
import tkinter as tk
from pathlib import Path


logger = logging.getLogger(__name__)

_ICON_NAME = "app.ico"


def resolve_app_icon_path() -> Path | None:
    for candidate in _candidate_icon_paths():
        if candidate.exists():
            return candidate
    return None


def apply_window_icon(window: tk.Misc) -> Path | None:
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
