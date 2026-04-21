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
