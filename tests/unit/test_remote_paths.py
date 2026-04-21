from mc_server_manager.config.settings import SftpSettings
from mc_server_manager.infrastructure.remote_paths import RemotePaths


def test_remote_paths_preserve_rooted_server_path() -> None:
    paths = RemotePaths(
        SftpSettings(
            host="example.org",
            port=22,
            username="tester",
            password="secret",
            server_root="/minecraft/server/",
        )
    )

    assert paths.management_root == "/minecraft/server/.mc-manager"
    assert (
        paths.world_manifest_path("weekend")
        == "/minecraft/server/.mc-manager/worlds/weekend/world.json"
    )
    assert (
        paths.mod_list_manifest_path("fabric")
        == "/minecraft/server/.mc-manager/mod-lists/fabric/mod-list.json"
    )
    assert paths.active_mod_lists_path == "/minecraft/server/.mc-manager/active-mod-lists.json"
    assert paths.live_mod_path("sodium.jar") == "/minecraft/server/mods/sodium.jar"
