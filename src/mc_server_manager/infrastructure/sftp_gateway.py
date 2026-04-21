from __future__ import annotations

from contextlib import contextmanager
from pathlib import PurePosixPath
import stat
from typing import Iterator

import paramiko

from mc_server_manager.config.settings import SftpSettings


class SftpGateway:
    def __init__(self, settings: SftpSettings) -> None:
        self._settings = settings

    @contextmanager
    def session(self) -> Iterator[paramiko.SFTPClient]:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=self._settings.host,
            port=self._settings.port,
            username=self._settings.username,
            password=self._settings.password,
        )
        sftp = client.open_sftp()
        try:
            yield sftp
        finally:
            sftp.close()
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

    def write_text(self, sftp: paramiko.SFTPClient, path: str, content: str) -> None:
        self.ensure_dir(sftp, str(PurePosixPath(path).parent))
        with sftp.file(path, "w") as remote_file:
            remote_file.write(content.encode("utf-8"))

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
