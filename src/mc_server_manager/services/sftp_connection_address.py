from __future__ import annotations

from urllib.parse import urlparse

from mc_server_manager.domain.models import SftpConnectionSettings


def format_gamehostbros_sftp_address(host: str, port: int) -> str:
    return f"sftp://{host}:{port}"


def build_gamehostbros_sftp_settings(
    *,
    connection_address: str,
    username: str,
    password: str,
    require: bool,
) -> SftpConnectionSettings | None:
    stripped_address = connection_address.strip()
    stripped_username = username.strip()
    stripped_password = password.strip()

    values = [stripped_address, stripped_username, stripped_password]
    if not any(values):
        if require:
            raise ValueError(
                "GameHostBros SFTP connection address, username, and password are required."
            )
        return None

    if not all(values):
        raise ValueError("Either fill all GameHostBros SFTP fields or leave all of them empty.")

    host, port = parse_gamehostbros_sftp_address(stripped_address)
    return SftpConnectionSettings(
        host=host,
        port=port,
        username=stripped_username,
        password=stripped_password,
        server_root="/",
    )


def parse_gamehostbros_sftp_address(value: str) -> tuple[str, int]:
    stripped = value.strip()
    if not stripped:
        raise ValueError("GameHostBros SFTP connection address is required.")

    candidate = stripped if "://" in stripped else f"sftp://{stripped}"
    parsed = urlparse(candidate)

    if parsed.scheme != "sftp":
        raise ValueError(
            "GameHostBros SFTP connection address must use sftp:// or plain host:port."
        )
    if parsed.username or parsed.password:
        raise ValueError(
            "GameHostBros SFTP connection address must not include a username or password."
        )
    if not parsed.hostname:
        raise ValueError("GameHostBros SFTP connection address must include a host.")
    if parsed.path not in {"", "/"}:
        raise ValueError("GameHostBros SFTP connection address must not include a path.")

    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("GameHostBros SFTP connection address must include a valid port.") from exc

    if port is None:
        raise ValueError("GameHostBros SFTP connection address must include a port.")

    return parsed.hostname, port
