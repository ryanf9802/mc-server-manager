from __future__ import annotations

import base64
import json
from dataclasses import asdict
from pathlib import Path
from typing import cast
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from platformdirs import user_data_dir

from mc_server_manager.domain.models import (
    AppState,
    EncryptedEnvelope,
    HostingProvider,
    ProviderConnection,
    RconConnectionSettings,
    SftpConnectionSettings,
    StoredServerConfig,
)


class AppStateStore:
    schema_version = 1

    def __init__(self, app_dir: Path | None = None) -> None:
        self._app_dir = app_dir or Path(user_data_dir("mc-server-manager", "mc-server-manager"))
        self._state_path = self._app_dir / "app-state.json.enc"

    @property
    def state_path(self) -> Path:
        return self._state_path

    def exists(self) -> bool:
        return self._state_path.exists()

    def initialize(self, password: str) -> AppState:
        state = AppState()
        self.save(state, password)
        return state

    def load(self, password: str) -> AppState:
        envelope_payload = json.loads(self._state_path.read_text(encoding="utf-8"))
        envelope = EncryptedEnvelope(
            schema_version=int(envelope_payload["schema_version"]),
            salt_b64=str(envelope_payload["salt_b64"]),
            ciphertext_b64=str(envelope_payload["ciphertext_b64"]),
        )
        plaintext = self._decrypt(envelope, password)
        payload = json.loads(plaintext)
        return _app_state_from_dict(payload)

    def save(self, state: AppState, password: str) -> None:
        self._app_dir.mkdir(parents=True, exist_ok=True)
        salt = self._generate_salt()
        ciphertext_b64 = self._encrypt(json.dumps(_app_state_to_dict(state)), password, salt)
        envelope = EncryptedEnvelope(
            schema_version=self.schema_version,
            salt_b64=base64.urlsafe_b64encode(salt).decode("utf-8"),
            ciphertext_b64=ciphertext_b64,
        )
        self._state_path.write_text(json.dumps(asdict(envelope), indent=2), encoding="utf-8")

    def export_server(self, server: StoredServerConfig, password: str, path: Path) -> None:
        salt = self._generate_salt()
        ciphertext_b64 = self._encrypt(json.dumps(_server_to_dict(server)), password, salt)
        envelope = EncryptedEnvelope(
            schema_version=self.schema_version,
            salt_b64=base64.urlsafe_b64encode(salt).decode("utf-8"),
            ciphertext_b64=ciphertext_b64,
        )
        path.write_text(json.dumps(asdict(envelope), indent=2), encoding="utf-8")

    def import_server(self, password: str, path: Path) -> StoredServerConfig:
        envelope_payload = json.loads(path.read_text(encoding="utf-8"))
        envelope = EncryptedEnvelope(
            schema_version=int(envelope_payload["schema_version"]),
            salt_b64=str(envelope_payload["salt_b64"]),
            ciphertext_b64=str(envelope_payload["ciphertext_b64"]),
        )
        plaintext = self._decrypt(envelope, password)
        return _server_from_dict(json.loads(plaintext))

    @staticmethod
    def create_local_id() -> str:
        return uuid4().hex

    def _decrypt(self, envelope: EncryptedEnvelope, password: str) -> str:
        key = _derive_key(password, base64.urlsafe_b64decode(envelope.salt_b64.encode("utf-8")))
        try:
            plaintext = Fernet(key).decrypt(envelope.ciphertext_b64.encode("utf-8"))
        except InvalidToken as exc:
            raise ValueError("Failed to decrypt app data. Check the application password.") from exc
        return plaintext.decode("utf-8")

    def _encrypt(self, plaintext: str, password: str, salt: bytes) -> str:
        key = _derive_key(password, salt)
        ciphertext = Fernet(key).encrypt(plaintext.encode("utf-8"))
        return ciphertext.decode("utf-8")

    @staticmethod
    def _generate_salt() -> bytes:
        return uuid4().bytes


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=390_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


def _app_state_to_dict(state: AppState) -> dict[str, object]:
    return {
        "schema_version": AppStateStore.schema_version,
        "selected_server_id": state.selected_server_id,
        "servers": [_server_to_dict(server) for server in state.servers],
    }


def _app_state_from_dict(payload: dict[str, object]) -> AppState:
    servers_value = payload.get("servers")
    servers_payload = cast(list[object], servers_value) if isinstance(servers_value, list) else []
    servers = tuple(
        _server_from_dict(cast(dict[str, object], item))
        for item in servers_payload
        if isinstance(item, dict)
    )
    selected_server_id = payload.get("selected_server_id")
    return AppState(
        servers=servers,
        selected_server_id=str(selected_server_id) if isinstance(selected_server_id, str) else None,
    )


def _server_to_dict(server: StoredServerConfig) -> dict[str, object]:
    return {
        "local_id": server.local_id,
        "display_name": server.display_name,
        "provider": {
            "provider": server.provider.provider.value,
            "panel_url": server.provider.panel_url,
            "api_token": server.provider.api_token,
            "server_id": server.provider.server_id,
            "server_uuid": server.provider.server_uuid,
            "server_name": server.provider.server_name,
        },
        "sftp": None
        if server.sftp is None
        else {
            "host": server.sftp.host,
            "port": server.sftp.port,
            "username": server.sftp.username,
            "password": server.sftp.password,
            "server_root": server.sftp.server_root,
        },
        "rcon": None
        if server.rcon is None
        else {
            "host": server.rcon.host,
            "port": server.rcon.port,
            "password": server.rcon.password,
        },
        "notes": server.notes,
    }


def _server_from_dict(payload: dict[str, object]) -> StoredServerConfig:
    provider_value = payload.get("provider")
    if not isinstance(provider_value, dict):
        raise ValueError("Stored server is missing provider details.")
    provider_payload = cast(dict[str, object], provider_value)
    sftp_payload = payload.get("sftp")
    rcon_payload = payload.get("rcon")
    notes = payload.get("notes", "")
    return StoredServerConfig(
        local_id=str(payload["local_id"]),
        display_name=str(payload["display_name"]),
        provider=ProviderConnection(
            provider=HostingProvider(str(provider_payload["provider"])),
            api_token=str(provider_payload["api_token"]),
            server_id=str(provider_payload["server_id"]),
            server_uuid=str(provider_payload["server_uuid"]),
            server_name=str(provider_payload["server_name"]),
            panel_url=str(provider_payload.get("panel_url", "")),
        ),
        sftp=_sftp_from_dict(sftp_payload),
        rcon=_rcon_from_dict(rcon_payload),
        notes=str(notes) if isinstance(notes, str) else "",
    )


def _sftp_from_dict(payload: object) -> SftpConnectionSettings | None:
    if not isinstance(payload, dict):
        return None
    data = cast(dict[str, object], payload)
    return SftpConnectionSettings(
        host=str(data["host"]),
        port=_to_int(data["port"]),
        username=str(data["username"]),
        password=str(data["password"]),
        server_root=str(data["server_root"]),
    )


def _rcon_from_dict(payload: object) -> RconConnectionSettings | None:
    if not isinstance(payload, dict):
        return None
    data = cast(dict[str, object], payload)
    return RconConnectionSettings(
        host=str(data["host"]),
        port=_to_int(data["port"]),
        password=str(data["password"]),
    )


def _to_int(value: object) -> int:
    return int(str(value))
