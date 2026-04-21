from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
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


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
