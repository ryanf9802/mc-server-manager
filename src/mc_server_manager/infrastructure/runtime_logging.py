from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path

from platformdirs import user_data_dir


_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def configure_logging(log_file_name: str) -> Path:
    log_path = get_logs_dir() / log_file_name
    log_path.parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        try:
            handler.close()
        except Exception:  # noqa: BLE001
            pass

    formatter = logging.Formatter(_LOG_FORMAT)
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    logging.captureWarnings(True)
    logging.getLogger("paramiko").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    sys.excepthook = _log_uncaught_exception
    threading.excepthook = _log_uncaught_thread_exception

    logging.getLogger(__name__).info("Runtime logging configured at %s", log_path)
    return log_path


def get_logs_dir() -> Path:
    return Path(user_data_dir("mc-server-manager", "mc-server-manager")).parent / "logs"


def open_logs_dir() -> Path:
    logs_dir = get_logs_dir()
    logs_dir.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        os.startfile(str(logs_dir))  # type: ignore[attr-defined]
        return logs_dir
    if sys.platform == "darwin":
        subprocess.run(["open", str(logs_dir)], check=True)
        return logs_dir
    if sys.platform.startswith("linux"):
        subprocess.run(["xdg-open", str(logs_dir)], check=True)
        return logs_dir
    raise ValueError(f"Opening the logs folder is not supported on {sys.platform}.")


def log_background_exception(logger: logging.Logger, context: str, exc: Exception) -> None:
    logger.exception("%s failed: %s", context, exc)


def _log_uncaught_exception(exc_type, exc_value, exc_traceback) -> None:
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.getLogger("mc_server_manager.crash").error(
        "Unhandled exception\n%s",
        "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)),
    )


def _log_uncaught_thread_exception(args: threading.ExceptHookArgs) -> None:
    logging.getLogger("mc_server_manager.thread").error(
        "Unhandled thread exception in %s\n%s",
        args.thread.name if args.thread else "<unknown>",
        "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback)),
    )
