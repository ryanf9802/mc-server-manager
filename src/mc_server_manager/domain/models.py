from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from enum import StrEnum


class WorldStatus(StrEnum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    PENDING_APPLY = "pending_apply"
    UNMANAGED_LIVE = "unmanaged_live"

    @property
    def label(self) -> str:
        return {
            WorldStatus.INACTIVE: "Inactive",
            WorldStatus.ACTIVE: "Active",
            WorldStatus.PENDING_APPLY: "Pending Apply",
            WorldStatus.UNMANAGED_LIVE: "Unmanaged Live",
        }[self]


@dataclass(frozen=True, slots=True)
class WorldManifest:
    slug: str
    display_name: str
    created_at_utc: datetime
    updated_at_utc: datetime


@dataclass(frozen=True, slots=True)
class ActiveWorldRecord:
    slug: str
    applied_at_utc: datetime
    server_properties_sha256: str
    whitelist_sha256: str


@dataclass(frozen=True, slots=True)
class WorldFileSet:
    server_properties_text: str
    whitelist_json_text: str


@dataclass(frozen=True, slots=True)
class WorldDetail:
    manifest: WorldManifest
    files: WorldFileSet
    status: WorldStatus


@dataclass(frozen=True, slots=True)
class WorldSummary:
    manifest: WorldManifest
    status: WorldStatus


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    message: str
    line_number: int | None = None


@dataclass(frozen=True, slots=True)
class ValidationResult:
    issues: tuple[ValidationIssue, ...] = ()

    @property
    def is_valid(self) -> bool:
        return not self.issues


@dataclass(frozen=True, slots=True)
class RconCommandResult:
    command: str
    response_text: str
    succeeded: bool
    executed_at: datetime


class HostingProvider(StrEnum):
    GAMEHOSTBROS = "gamehostbros"

    @property
    def label(self) -> str:
        return {
            HostingProvider.GAMEHOSTBROS: "GameHostBros",
        }[self]

    @property
    def default_panel_url(self) -> str:
        return {
            HostingProvider.GAMEHOSTBROS: "https://panel.gamehostbros.com",
        }[self]


class ProviderPowerSignal(StrEnum):
    START = "start"
    STOP = "stop"
    RESTART = "restart"
    KILL = "kill"


@dataclass(frozen=True, slots=True)
class ProviderConnection:
    provider: HostingProvider
    api_token: str
    server_id: str
    server_uuid: str
    server_name: str
    panel_url: str = ""

    @property
    def resolved_panel_url(self) -> str:
        configured = self.panel_url.strip()
        if configured:
            return configured.rstrip("/")
        return self.provider.default_panel_url


@dataclass(frozen=True, slots=True)
class SftpConnectionSettings:
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
class RconConnectionSettings:
    host: str
    port: int
    password: str

    @property
    def endpoint(self) -> str:
        return f"{self.host}:{self.port}"


@dataclass(frozen=True, slots=True)
class StoredServerConfig:
    local_id: str
    display_name: str
    provider: ProviderConnection
    sftp: SftpConnectionSettings | None = None
    rcon: RconConnectionSettings | None = None
    notes: str = ""


@dataclass(frozen=True, slots=True)
class AppState:
    servers: tuple[StoredServerConfig, ...] = ()
    selected_server_id: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderServerSummary:
    server_id: str
    server_uuid: str
    name: str
    description: str
    current_state: str | None = None

    @property
    def label(self) -> str:
        return self.name or self.server_id


@dataclass(frozen=True, slots=True)
class ProviderServerResources:
    current_state: str
    memory_bytes: int | None = None
    cpu_absolute: float | None = None
    disk_bytes: int | None = None
    network_rx_bytes: int | None = None
    network_tx_bytes: int | None = None
    players_online: int | None = None
    players_max: int | None = None


@dataclass(frozen=True, slots=True)
class SelectedServerStatus:
    summary: ProviderServerSummary
    resources: ProviderServerResources


@dataclass(frozen=True, slots=True)
class BuildInfo:
    release_tag: str
    commit_sha: str
    repo_owner: str
    repo_name: str
    installer_asset_name: str = "mc-server-manager-installer.exe"
    bundle_asset_name: str = "mc-server-manager-windows-x64.zip"

    @property
    def is_dev(self) -> bool:
        return self.release_tag.strip().lower() == "dev"

    @property
    def repo_full_name(self) -> str:
        if not self.repo_owner or not self.repo_name:
            return ""
        return f"{self.repo_owner}/{self.repo_name}"


@dataclass(frozen=True, slots=True)
class InstallLayout:
    root_dir: str
    current_dir: str
    current_app_exe: str
    installer_exe: str
    metadata_path: str
    staging_dir: str
    start_menu_shortcut: str


@dataclass(frozen=True, slots=True)
class InstalledAppMetadata:
    release_tag: str
    installed_at_utc: datetime
    current_exe_name: str
    installer_exe_name: str


@dataclass(frozen=True, slots=True)
class ReleaseAsset:
    name: str
    browser_download_url: str
    size_bytes: int
    content_type: str


@dataclass(frozen=True, slots=True)
class GitHubRelease:
    tag_name: str
    published_at_utc: datetime
    html_url: str
    assets: tuple[ReleaseAsset, ...]

    def get_asset(self, name: str) -> ReleaseAsset | None:
        return next((asset for asset in self.assets if asset.name == name), None)


@dataclass(frozen=True, slots=True)
class UpdateAvailability:
    current_build: BuildInfo
    latest_release: GitHubRelease | None
    is_managed_install: bool
    is_update_available: bool
    message: str


@dataclass(frozen=True, slots=True)
class EncryptedEnvelope:
    schema_version: int
    salt_b64: str
    ciphertext_b64: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
