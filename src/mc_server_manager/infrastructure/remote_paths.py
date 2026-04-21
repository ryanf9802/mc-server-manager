from __future__ import annotations

from dataclasses import dataclass

from mc_server_manager.config.settings import SftpSettings


@dataclass(frozen=True, slots=True)
class RemotePaths:
    settings: SftpSettings

    @property
    def management_root(self) -> str:
        return self.combine(self.settings.normalized_server_root, ".mc-manager")

    @property
    def worlds_root(self) -> str:
        return self.combine(self.management_root, "worlds")

    @property
    def active_world_path(self) -> str:
        return self.combine(self.management_root, "active-world.json")

    @property
    def mod_lists_root(self) -> str:
        return self.combine(self.management_root, "mod-lists")

    @property
    def active_mod_lists_path(self) -> str:
        return self.combine(self.management_root, "active-mod-lists.json")

    @property
    def live_server_properties_path(self) -> str:
        return self.combine(self.settings.normalized_server_root, "server.properties")

    @property
    def live_whitelist_path(self) -> str:
        return self.combine(self.settings.normalized_server_root, "whitelist.json")

    @property
    def live_mods_root(self) -> str:
        return self.combine(self.settings.normalized_server_root, "mods")

    def world_root(self, slug: str) -> str:
        return self.combine(self.worlds_root, slug)

    def world_manifest_path(self, slug: str) -> str:
        return self.combine(self.world_root(slug), "world.json")

    def world_server_properties_path(self, slug: str) -> str:
        return self.combine(self.world_root(slug), "server.properties")

    def world_whitelist_path(self, slug: str) -> str:
        return self.combine(self.world_root(slug), "whitelist.json")

    def mod_list_root(self, slug: str) -> str:
        return self.combine(self.mod_lists_root, slug)

    def mod_list_manifest_path(self, slug: str) -> str:
        return self.combine(self.mod_list_root(slug), "mod-list.json")

    def mod_list_mods_root(self, slug: str) -> str:
        return self.combine(self.mod_list_root(slug), "mods")

    def mod_list_jar_path(self, slug: str, filename: str) -> str:
        return self.combine(self.mod_list_mods_root(slug), filename)

    def live_mod_path(self, filename: str) -> str:
        return self.combine(self.live_mods_root, filename)

    @staticmethod
    def combine(*segments: str) -> str:
        rooted = any(segment.startswith("/") for segment in segments if segment)
        combined = "/".join(segment.strip("/") for segment in segments if segment.strip("/"))
        return f"/{combined}" if rooted and not combined.startswith("/") else combined or "/"
