from __future__ import annotations

import sys
import tkinter as tk
from tkinter import messagebox, simpledialog

from mc_server_manager.gui.main_window import MainWindow
from mc_server_manager.infrastructure.app_state_store import AppStateStore
from mc_server_manager.services.app_state import AppStateService


def main() -> int:
    root = tk.Tk()
    root.withdraw()
    try:
        store = AppStateStore()
        password, state = _load_or_initialize_state(root, store)
        if password is None or state is None:
            root.destroy()
            return 0

        main_window = MainWindow(root, AppStateService(store, state, password))
        main_window.run()
        return 0
    except Exception as exc:  # noqa: BLE001
        _show_startup_error(str(exc), root)
        try:
            root.destroy()
        except Exception:  # noqa: BLE001
            pass
        return 1


def _load_or_initialize_state(root: tk.Tk, store: AppStateStore):
    if not store.exists():
        return _create_new_state(root, store)
    return _unlock_existing_state(root, store)


def _create_new_state(root: tk.Tk, store: AppStateStore):
    while True:
        password = simpledialog.askstring(
            "Create Application Password",
            "Create an application password to encrypt the local server library.",
            parent=root,
            show="*",
        )
        if password is None:
            return None, None
        if not password.strip():
            messagebox.showerror(
                "Minecraft Server Manager",
                "Application password cannot be empty.",
                parent=root,
            )
            continue
        confirmation = simpledialog.askstring(
            "Confirm Application Password",
            "Re-enter the application password.",
            parent=root,
            show="*",
        )
        if confirmation is None:
            return None, None
        if confirmation != password:
            messagebox.showerror(
                "Minecraft Server Manager",
                "Passwords did not match. Try again.",
                parent=root,
            )
            continue
        state = store.initialize(password)
        return password, state


def _unlock_existing_state(root: tk.Tk, store: AppStateStore):
    while True:
        password = simpledialog.askstring(
            "Unlock Application State",
            "Enter the application password to unlock saved server configurations.",
            parent=root,
            show="*",
        )
        if password is None:
            return None, None
        try:
            return password, store.load(password)
        except ValueError as exc:
            retry = messagebox.askretrycancel(
                "Minecraft Server Manager",
                str(exc),
                parent=root,
            )
            if not retry:
                return None, None


def _show_startup_error(message: str, root: tk.Tk | None = None) -> None:
    try:
        if root is None:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Minecraft Server Manager", message, parent=root)
            root.destroy()
            return
        messagebox.showerror("Minecraft Server Manager", message, parent=root)
    except Exception:  # noqa: BLE001
        print(message, file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
