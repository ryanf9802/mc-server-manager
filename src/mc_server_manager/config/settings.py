from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SftpSettings:
    host: str
    port: int
    username: str
    password: str
    server_root: str

    @property
    def normalized_server_root(self) -> str:
        stripped = self.server_root.strip()
        if not stripped:
            return "/"
        normalized = stripped.rstrip("/")
        return normalized or "/"


@dataclass(frozen=True, slots=True)
class RconSettings:
    host: str
    port: int
    password: str

    @property
    def endpoint(self) -> str:
        return f"{self.host}:{self.port}"


@dataclass(frozen=True, slots=True)
class AppSettings:
    sftp: SftpSettings
    rcon: RconSettings | None = None
    rcon_unavailable_reason: str | None = None
