from __future__ import annotations

import sys
import tkinter as tk
from tkinter import messagebox

from mc_server_manager.config.dotenv_loader import DotEnvLoader
from mc_server_manager.gui.main_window import MainWindow
from mc_server_manager.infrastructure.remote_paths import RemotePaths
from mc_server_manager.infrastructure.repositories import (
    SftpLiveConfigStore,
    SftpWorldRepository,
)
from mc_server_manager.infrastructure.sftp_gateway import SftpGateway
from mc_server_manager.services.activation import ActivationService
from mc_server_manager.services.world_catalog import WorldCatalogService
from mc_server_manager.services.world_editor import WorldEditorService
from mc_server_manager.validation.server_properties import ServerPropertiesValidator
from mc_server_manager.validation.whitelist import WhitelistValidator


def main() -> int:
    try:
        loader = DotEnvLoader()
        settings = loader.load()
        paths = RemotePaths(settings)
        gateway = SftpGateway(settings)
        world_repository = SftpWorldRepository(gateway, paths)
        live_config_store = SftpLiveConfigStore(gateway, paths)
        main_window = MainWindow(
            world_catalog_service=WorldCatalogService(world_repository, live_config_store),
            world_editor_service=WorldEditorService(
                world_repository,
                live_config_store,
                ServerPropertiesValidator(),
                WhitelistValidator(),
            ),
            activation_service=ActivationService(world_repository, live_config_store),
        )
    except Exception as exc:  # noqa: BLE001
        _show_startup_error(str(exc))
        return 1

    main_window.run()
    return 0


def _show_startup_error(message: str) -> None:
    try:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Minecraft Server Manager", message, parent=root)
        root.destroy()
    except Exception:  # noqa: BLE001
        print(message, file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
