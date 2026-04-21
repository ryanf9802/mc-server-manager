from __future__ import annotations

from contextlib import contextmanager
import logging
from pathlib import PurePosixPath
import stat
import sys
from typing import Iterator

import paramiko

from mc_server_manager.infrastructure.build_info import runtime_diagnostics
from mc_server_manager.infrastructure.runtime_logging import get_logs_dir
from mc_server_manager.config.settings import SftpSettings

logger = logging.getLogger(__name__)


class SftpGateway:
    def __init__(self, settings: SftpSettings) -> None:
        self._settings = settings

    @contextmanager
    def session(self) -> Iterator[paramiko.SFTPClient]:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        sftp: paramiko.SFTPClient | None = None
        try:
            client.connect(
                hostname=self._settings.host,
                port=self._settings.port,
                username=self._settings.username,
                password=self._settings.password,
                look_for_keys=False,
                allow_agent=False,
                timeout=15.0,
                auth_timeout=15.0,
                banner_timeout=15.0,
            )
            sftp = client.open_sftp()
            yield sftp
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "SFTP session failed for host=%s port=%s username=%s root=%s runtime=%s executable=%s frozen=%s",
                self._settings.host,
                self._settings.port,
                self._settings.username,
                self._settings.normalized_server_root,
                runtime_diagnostics(),
                sys.executable,
                bool(getattr(sys, "frozen", False)),
            )
            raise ConnectionError(self._format_connection_error(exc)) from exc
        finally:
            try:
                if sftp is not None:
                    sftp.close()
            except Exception:  # noqa: BLE001
                pass
            client.close()

    def exists(self, sftp: paramiko.SFTPClient, path: str) -> bool:
        try:
            sftp.stat(path)
            return True
        except FileNotFoundError:
            return False

    def read_text(self, sftp: paramiko.SFTPClient, path: str, *, default: str | None = None) -> str:
        if not self.exists(sftp, path):
            if default is None:
                raise FileNotFoundError(path)
            return default

        with sftp.file(path, "r") as remote_file:
            data = remote_file.read()
        return data.decode("utf-8")

    def read_bytes(
        self, sftp: paramiko.SFTPClient, path: str, *, default: bytes | None = None
    ) -> bytes:
        if not self.exists(sftp, path):
            if default is None:
                raise FileNotFoundError(path)
            return default

        with sftp.file(path, "rb") as remote_file:
            return remote_file.read()

    def write_text(self, sftp: paramiko.SFTPClient, path: str, content: str) -> None:
        self.ensure_dir(sftp, str(PurePosixPath(path).parent))
        with sftp.file(path, "w") as remote_file:
            remote_file.write(content.encode("utf-8"))

    def write_bytes(self, sftp: paramiko.SFTPClient, path: str, content: bytes) -> None:
        self.ensure_dir(sftp, str(PurePosixPath(path).parent))
        with sftp.file(path, "wb") as remote_file:
            remote_file.write(content)

    def ensure_dir(self, sftp: paramiko.SFTPClient, path: str) -> None:
        if path in {"", "."}:
            return

        current = PurePosixPath("/")
        for part in PurePosixPath(path).parts:
            if part == "/":
                current = PurePosixPath("/")
                continue
            current /= part
            current_text = current.as_posix()
            if not self.exists(sftp, current_text):
                sftp.mkdir(current_text)

    def remove_tree(self, sftp: paramiko.SFTPClient, path: str) -> None:
        for entry in sftp.listdir_attr(path):
            entry_path = PurePosixPath(path) / entry.filename
            if stat.S_ISDIR(entry.st_mode):
                self.remove_tree(sftp, entry_path.as_posix())
            else:
                sftp.remove(entry_path.as_posix())
        sftp.rmdir(path)

    def remove_file(self, sftp: paramiko.SFTPClient, path: str) -> None:
        if self.exists(sftp, path):
            sftp.remove(path)

    def _format_connection_error(self, exc: Exception) -> str:
        return (
            f"SFTP connection failed for {self._settings.username}@{self._settings.host}:{self._settings.port}. "
            f"See logs in {get_logs_dir()} for details. "
            f"Details: {exc or exc.__class__.__name__}"
        )
