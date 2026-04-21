from __future__ import annotations

import tkinter as tk
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from mc_server_manager.domain.models import (
    ProviderPowerSignal,
    ProviderServerResources,
    ProviderServerSummary,
    SelectedServerStatus,
    StoredServerConfig,
)
from mc_server_manager.gui.add_server_window import AddServerWindow
from mc_server_manager.gui.console_window import ConsoleWindow
from mc_server_manager.gui.server_settings_window import ServerSettingsWindow
from mc_server_manager.gui.world_management_window import WorldManagementWindow
from mc_server_manager.services.app_state import AppStateService
from mc_server_manager.services.server_runtime import (
    create_provider_client,
    create_rcon_service,
    create_world_services,
)


class MainWindow:
    def __init__(self, root: tk.Tk, app_state_service: AppStateService) -> None:
        self.root = root
        self._app_state_service = app_state_service
        self._executor = ThreadPoolExecutor(max_workers=3)
        self._busy = False
        self._current_power_state: str | None = None
        self._server_lookup: dict[str, StoredServerConfig] = {}
        self._server_ids: list[str] = []
        self._world_windows: dict[str, WorldManagementWindow] = {}
        self._console_windows: dict[str, ConsoleWindow] = {}

        self.status_message_var = tk.StringVar(
            value="Select a server or add one from the provider API."
        )
        self.selected_server_name_var = tk.StringVar(value="No server selected")
        self.provider_summary_var = tk.StringVar(value="Provider: Not configured")
        self.server_identity_var = tk.StringVar(value="")
        self.sftp_summary_var = tk.StringVar(value="SFTP: Not configured")
        self.rcon_summary_var = tk.StringVar(value="RCON: Not configured")
        self.power_state_var = tk.StringVar(value="Power: Unknown")
        self.players_var = tk.StringVar(value="Players: Unknown")
        self.memory_var = tk.StringVar(value="Memory: Unknown")
        self.cpu_var = tk.StringVar(value="CPU: Unknown")
        self.disk_var = tk.StringVar(value="Disk: Unknown")
        self.network_var = tk.StringVar(value="Network: Unknown")

        self._configure_root()
        self._build_layout()
        self._bind_events()
        self._render_servers()

    def run(self) -> None:
        self.root.deiconify()
        self.root.mainloop()

    def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
        self.root.destroy()

    def _configure_root(self) -> None:
        self.root.title("Minecraft Server Manager")
        self.root.geometry("1260x760")
        self.root.minsize(1080, 680)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

    def _build_layout(self) -> None:
        sidebar = ttk.Frame(self.root, padding=16)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.columnconfigure(0, weight=1)
        sidebar.rowconfigure(1, weight=1)

        sidebar_actions = ttk.Frame(sidebar)
        sidebar_actions.grid(row=0, column=0, sticky="ew")
        sidebar_actions.columnconfigure(0, weight=1)
        sidebar_actions.columnconfigure(1, weight=1)
        sidebar_actions.columnconfigure(2, weight=1)
        sidebar_actions.columnconfigure(3, weight=1)

        self.add_button = ttk.Button(sidebar_actions, text="Add", command=self.add_server)
        self.add_button.grid(row=0, column=0, sticky="ew")
        self.edit_button = ttk.Button(
            sidebar_actions, text="Settings", command=self.edit_selected_server
        )
        self.edit_button.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        self.import_button = ttk.Button(sidebar_actions, text="Import", command=self.import_server)
        self.import_button.grid(row=0, column=2, sticky="ew", padx=(8, 0))
        self.export_button = ttk.Button(
            sidebar_actions, text="Export", command=self.export_selected_server
        )
        self.export_button.grid(row=0, column=3, sticky="ew", padx=(8, 0))

        list_frame = ttk.LabelFrame(sidebar, text="Servers", padding=12)
        list_frame.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        self.server_listbox = tk.Listbox(
            list_frame,
            activestyle="dotbox",
            exportselection=False,
        )
        self.server_listbox.grid(row=0, column=0, sticky="nsew")
        list_scrollbar = ttk.Scrollbar(
            list_frame,
            orient="vertical",
            command=self.server_listbox.yview,
        )
        list_scrollbar.grid(row=0, column=1, sticky="ns")
        self.server_listbox.configure(yscrollcommand=list_scrollbar.set)

        delete_row = ttk.Frame(sidebar)
        delete_row.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        delete_row.columnconfigure(0, weight=1)
        self.delete_button = ttk.Button(
            delete_row,
            text="Delete Saved Server",
            command=self.delete_selected_server,
        )
        self.delete_button.grid(row=0, column=0, sticky="ew")

        content = ttk.Frame(self.root, padding=(0, 16, 16, 16))
        content.grid(row=0, column=1, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(2, weight=1)

        summary = ttk.LabelFrame(content, text="Selected Server", padding=16)
        summary.grid(row=0, column=0, sticky="ew")
        summary.columnconfigure(0, weight=1)

        ttk.Label(summary, textvariable=self.selected_server_name_var).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(summary, textvariable=self.provider_summary_var).grid(
            row=1, column=0, sticky="w", pady=(8, 0)
        )
        ttk.Label(summary, textvariable=self.server_identity_var).grid(
            row=2, column=0, sticky="w", pady=(4, 0)
        )
        ttk.Label(summary, textvariable=self.sftp_summary_var).grid(
            row=3, column=0, sticky="w", pady=(4, 0)
        )
        ttk.Label(summary, textvariable=self.rcon_summary_var).grid(
            row=4, column=0, sticky="w", pady=(4, 0)
        )

        power_frame = ttk.LabelFrame(content, text="Provider Controls", padding=16)
        power_frame.grid(row=1, column=0, sticky="ew", pady=(16, 0))
        for column in range(5):
            power_frame.columnconfigure(column, weight=1)

        self.refresh_button = ttk.Button(
            power_frame, text="Refresh Status", command=self.refresh_selected_server
        )
        self.refresh_button.grid(row=0, column=0, sticky="ew")
        self.start_button = ttk.Button(
            power_frame,
            text="Start",
            command=lambda: self.send_power_signal(ProviderPowerSignal.START),
        )
        self.start_button.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        self.stop_button = ttk.Button(
            power_frame,
            text="Stop",
            command=lambda: self.send_power_signal(ProviderPowerSignal.STOP),
        )
        self.stop_button.grid(row=0, column=2, sticky="ew", padx=(8, 0))
        self.restart_button = ttk.Button(
            power_frame,
            text="Restart",
            command=lambda: self.send_power_signal(ProviderPowerSignal.RESTART),
        )
        self.restart_button.grid(row=0, column=3, sticky="ew", padx=(8, 0))
        self.kill_button = ttk.Button(
            power_frame,
            text="Kill",
            command=lambda: self.send_power_signal(ProviderPowerSignal.KILL),
        )
        self.kill_button.grid(row=0, column=4, sticky="ew", padx=(8, 0))

        details = ttk.LabelFrame(content, text="Status and Panels", padding=16)
        details.grid(row=2, column=0, sticky="nsew", pady=(16, 0))
        details.columnconfigure(0, weight=1)
        details.columnconfigure(1, weight=1)

        status_frame = ttk.Frame(details)
        status_frame.grid(row=0, column=0, sticky="nsew")
        status_frame.columnconfigure(0, weight=1)
        ttk.Label(status_frame, textvariable=self.power_state_var).grid(row=0, column=0, sticky="w")
        ttk.Label(status_frame, textvariable=self.players_var).grid(
            row=1, column=0, sticky="w", pady=(8, 0)
        )
        ttk.Label(status_frame, textvariable=self.memory_var).grid(
            row=2, column=0, sticky="w", pady=(8, 0)
        )
        ttk.Label(status_frame, textvariable=self.cpu_var).grid(
            row=3, column=0, sticky="w", pady=(8, 0)
        )
        ttk.Label(status_frame, textvariable=self.disk_var).grid(
            row=4, column=0, sticky="w", pady=(8, 0)
        )
        ttk.Label(status_frame, textvariable=self.network_var).grid(
            row=5, column=0, sticky="w", pady=(8, 0)
        )

        panel_frame = ttk.Frame(details)
        panel_frame.grid(row=0, column=1, sticky="nsew", padx=(24, 0))
        panel_frame.columnconfigure(0, weight=1)
        ttk.Label(
            panel_frame,
            text="Panels",
        ).grid(row=0, column=0, sticky="w")
        self.worlds_button = ttk.Button(
            panel_frame,
            text="Open World Management",
            command=self.open_world_management,
        )
        self.worlds_button.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        self.console_button = ttk.Button(
            panel_frame,
            text="Open RCON Console",
            command=self.open_rcon_console,
        )
        self.console_button.grid(row=2, column=0, sticky="ew", pady=(12, 0))

        status_bar = ttk.Frame(self.root, padding=(16, 0, 16, 12))
        status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        status_bar.columnconfigure(0, weight=1)
        ttk.Label(status_bar, textvariable=self.status_message_var).grid(
            row=0, column=0, sticky="w"
        )

    def _bind_events(self) -> None:
        self.server_listbox.bind("<<ListboxSelect>>", self._on_server_selected)

    def _selected_server(self) -> StoredServerConfig | None:
        selection = self.server_listbox.curselection()
        if not selection:
            return None
        local_id = self._server_ids[selection[0]]
        return self._server_lookup.get(local_id)

    def _render_servers(self) -> None:
        servers = self._app_state_service.list_servers()
        self._server_lookup = {server.local_id: server for server in servers}
        self._server_ids = [server.local_id for server in servers]

        self.server_listbox.delete(0, tk.END)
        for server in servers:
            self.server_listbox.insert(tk.END, server.display_name)

        selected = self._app_state_service.get_selected_server()
        if selected is not None and selected.local_id in self._server_lookup:
            index = next(
                idx for idx, server in enumerate(servers) if server.local_id == selected.local_id
            )
            self.server_listbox.selection_set(index)
            self.server_listbox.activate(index)
            self.server_listbox.see(index)
        elif servers:
            self.server_listbox.selection_set(0)
            self.server_listbox.activate(0)
            self._app_state_service.set_selected_server(servers[0].local_id)

        selected_server = self._app_state_service.get_selected_server()
        self._apply_selected_server(selected_server)
        self._auto_refresh_server_status(selected_server)

    def _apply_selected_server(self, server: StoredServerConfig | None) -> None:
        if server is None:
            self.selected_server_name_var.set("No server selected")
            self.provider_summary_var.set("Provider: Not configured")
            self.server_identity_var.set("")
            self.sftp_summary_var.set("SFTP: Not configured")
            self.rcon_summary_var.set("RCON: Not configured")
            self._apply_status_labels(None, None)
            self._update_button_states()
            return

        self.selected_server_name_var.set(server.display_name)
        self.provider_summary_var.set(
            f"Provider: {server.provider.provider.label} | {server.provider.server_name}"
        )
        self.server_identity_var.set(
            f"Panel: {server.provider.resolved_panel_url} | Server ID: {server.provider.server_id}"
        )
        if server.sftp is None:
            self.sftp_summary_var.set("SFTP: Not configured")
        else:
            self.sftp_summary_var.set(
                f"SFTP: {server.sftp.host}:{server.sftp.port} {server.sftp.normalized_server_root}"
            )
        if server.rcon is None:
            self.rcon_summary_var.set("RCON: Not configured")
        else:
            self.rcon_summary_var.set(f"RCON: {server.rcon.endpoint}")
        self._apply_status_labels(None, None)
        self._update_button_states()

    def _apply_status_labels(
        self,
        summary: ProviderServerSummary | None,
        resources: ProviderServerResources | None,
    ) -> None:
        if summary is None or resources is None:
            self._current_power_state = None
            self.power_state_var.set("Power: Unknown")
            self.players_var.set("Players: Unknown")
            self.memory_var.set("Memory: Unknown")
            self.cpu_var.set("CPU: Unknown")
            self.disk_var.set("Disk: Unknown")
            self.network_var.set("Network: Unknown")
            self._update_button_states()
            return

        self._current_power_state = resources.current_state.strip().lower()
        self.power_state_var.set(f"Power: {resources.current_state}")
        if resources.players_online is None or resources.players_max is None:
            self.players_var.set("Players: Unknown")
        else:
            self.players_var.set(f"Players: {resources.players_online}/{resources.players_max}")
        self.memory_var.set(f"Memory: {_format_bytes(resources.memory_bytes)}")
        self.cpu_var.set(f"CPU: {_format_cpu(resources.cpu_absolute)}")
        self.disk_var.set(f"Disk: {_format_bytes(resources.disk_bytes)}")
        self.network_var.set(
            "Network: "
            f"RX {_format_bytes(resources.network_rx_bytes)} | "
            f"TX {_format_bytes(resources.network_tx_bytes)}"
        )
        self._update_button_states()

    def _update_button_states(self) -> None:
        selected_server = self._app_state_service.get_selected_server()
        has_server = selected_server is not None
        state = "disabled" if self._busy else "normal"

        self.add_button.configure(state=state)
        self.import_button.configure(state=state)
        self.edit_button.configure(state=state if has_server else "disabled")
        self.export_button.configure(state=state if has_server else "disabled")
        self.delete_button.configure(state=state if has_server else "disabled")
        self.refresh_button.configure(state=state if has_server else "disabled")
        self.start_button.configure(
            state=_button_state(
                state,
                has_server
                and _power_signal_enabled(ProviderPowerSignal.START, self._current_power_state),
            )
        )
        self.stop_button.configure(
            state=_button_state(
                state,
                has_server
                and _power_signal_enabled(ProviderPowerSignal.STOP, self._current_power_state),
            )
        )
        self.restart_button.configure(
            state=_button_state(
                state,
                has_server
                and _power_signal_enabled(ProviderPowerSignal.RESTART, self._current_power_state),
            )
        )
        self.kill_button.configure(
            state=_button_state(
                state,
                has_server
                and _power_signal_enabled(ProviderPowerSignal.KILL, self._current_power_state),
            )
        )

        worlds_enabled = selected_server is not None and selected_server.sftp is not None
        rcon_enabled = selected_server is not None and selected_server.rcon is not None
        self.worlds_button.configure(state=state if worlds_enabled else "disabled")
        self.console_button.configure(state=state if rcon_enabled else "disabled")

    def _on_server_selected(self, _event: tk.Event) -> None:
        server = self._selected_server()
        local_id = server.local_id if server is not None else None
        self._app_state_service.set_selected_server(local_id)
        self._apply_selected_server(server)
        if server is not None:
            self._auto_refresh_server_status(server)
            return
        self._set_status("Select a server or add one from the provider API.")

    def add_server(self) -> None:
        draft = AddServerWindow(self.root).show()
        if draft is None:
            return

        saved = self._show_settings_window(draft, mode="create")
        if saved is not None:
            self._app_state_service.upsert_server(saved)
            self._render_servers()
            self._set_status(f"Saved server {saved.display_name}.")

    def edit_selected_server(self) -> None:
        server = self._app_state_service.get_selected_server()
        if server is None:
            self._set_status("Select a server before opening settings.")
            return

        saved = self._show_settings_window(server, mode="edit")
        if saved is not None:
            self._app_state_service.upsert_server(saved)
            self._render_servers()
            self._set_status(f"Updated settings for {saved.display_name}.")

    def _show_settings_window(
        self,
        server: StoredServerConfig,
        *,
        mode: str,
    ) -> StoredServerConfig | None:
        return ServerSettingsWindow(self.root, server, mode=mode).show()

    def delete_selected_server(self) -> None:
        server = self._app_state_service.get_selected_server()
        if server is None:
            self._set_status("Select a server before deleting it.")
            return
        confirmed = messagebox.askyesno(
            "Delete Saved Server",
            f"Delete the saved configuration for {server.display_name}?\n\n"
            "This only removes the local encrypted app state entry.",
            parent=self.root,
        )
        if not confirmed:
            return

        self._app_state_service.delete_server(server.local_id)
        self._render_servers()
        self._set_status(f"Deleted saved configuration for {server.display_name}.")

    def export_selected_server(self) -> None:
        server = self._app_state_service.get_selected_server()
        if server is None:
            self._set_status("Select a server before exporting it.")
            return

        destination = filedialog.asksaveasfilename(
            parent=self.root,
            title="Export Server Configuration",
            defaultextension=".mcserver",
            filetypes=[("Encrypted server config", "*.mcserver"), ("JSON", "*.json")],
            initialfile=f"{server.display_name}.mcserver",
        )
        if not destination:
            return

        self._app_state_service.export_server(server.local_id, Path(destination))
        self._set_status(f"Exported {server.display_name} to {destination}.")

    def import_server(self) -> None:
        source = filedialog.askopenfilename(
            parent=self.root,
            title="Import Server Configuration",
            filetypes=[
                ("Encrypted server config", "*.mcserver"),
                ("JSON", "*.json"),
                ("All files", "*.*"),
            ],
        )
        if not source:
            return

        try:
            imported = self._app_state_service.import_server(Path(source))
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Import Server", str(exc), parent=self.root)
            self._set_status(str(exc))
            return

        duplicate = self._app_state_service.find_by_provider_server(imported.provider)
        target = imported
        if duplicate is not None:
            choice = messagebox.askyesnocancel(
                "Import Server",
                "A saved server already points at this provider server.\n\n"
                "Yes = replace the existing saved server.\n"
                "No = import as a duplicate with a new local name.\n"
                "Cancel = abort.",
                parent=self.root,
            )
            if choice is None:
                return
            if choice:
                target = StoredServerConfig(
                    local_id=duplicate.local_id,
                    display_name=imported.display_name,
                    provider=imported.provider,
                    sftp=imported.sftp,
                    rcon=imported.rcon,
                    notes=imported.notes,
                )
            else:
                duplicate_name = simpledialog.askstring(
                    "Import Server",
                    "Name for the duplicated server entry:",
                    parent=self.root,
                    initialvalue=f"{imported.display_name} (Imported)",
                )
                if duplicate_name is None:
                    return
                target = self._app_state_service.duplicate_with_new_identity(
                    imported,
                    duplicate_name.strip() or f"{imported.display_name} (Imported)",
                )

        self._app_state_service.save_imported_server(target)
        self._render_servers()
        self._set_status(f"Imported {target.display_name}.")

    def refresh_selected_server(self) -> None:
        server = self._app_state_service.get_selected_server()
        if server is None:
            self._set_status("Select a server before refreshing status.")
            return

        def task() -> SelectedServerStatus:
            client = create_provider_client(server)
            summary = client.get_server_details(server.provider.server_id)
            resources = client.get_resources(server.provider.server_id)
            return SelectedServerStatus(summary=summary, resources=resources)

        def on_success(status: SelectedServerStatus) -> None:
            self._apply_status_labels(status.summary, status.resources)
            self._set_status(f"Refreshed provider status for {server.display_name}.")

        self._run_background(
            task,
            on_success,
            start_message=f"Refreshing provider status for {server.display_name}...",
        )

    def _auto_refresh_server_status(self, server: StoredServerConfig | None) -> None:
        if server is None or self._busy:
            return
        self._set_status(f"Loading provider status for {server.display_name}...")
        self.refresh_selected_server()

    def send_power_signal(self, signal: ProviderPowerSignal) -> None:
        server = self._app_state_service.get_selected_server()
        if server is None:
            self._set_status("Select a server before sending power controls.")
            return

        def task() -> SelectedServerStatus:
            client = create_provider_client(server)
            client.send_power_signal(server.provider.server_id, signal)
            summary = client.get_server_details(server.provider.server_id)
            resources = client.get_resources(server.provider.server_id)
            return SelectedServerStatus(summary=summary, resources=resources)

        def on_success(status: SelectedServerStatus) -> None:
            self._apply_status_labels(status.summary, status.resources)
            self._set_status(
                f"Sent {signal.value} to {server.display_name} and refreshed provider status."
            )

        self._run_background(
            task,
            on_success,
            start_message=f"Sending {signal.value} request to {server.display_name}...",
        )

    def open_world_management(self) -> None:
        server = self._app_state_service.get_selected_server()
        if server is None:
            self._set_status("Select a server before opening world management.")
            return
        if server.sftp is None:
            messagebox.showerror(
                "World Management",
                "SFTP is not configured for this server.",
                parent=self.root,
            )
            self._set_status("World management is unavailable until SFTP is configured.")
            return

        existing = self._world_windows.get(server.local_id)
        if existing is not None and existing.window.winfo_exists():
            existing.present()
            return

        services = create_world_services(server)
        window = WorldManagementWindow(self.root, server, *services)
        self._world_windows[server.local_id] = window
        window.present()

    def open_rcon_console(self) -> None:
        server = self._app_state_service.get_selected_server()
        if server is None:
            self._set_status("Select a server before opening the RCON console.")
            return
        if server.rcon is None:
            messagebox.showerror(
                "RCON Console",
                "RCON is not configured for this server.",
                parent=self.root,
            )
            self._set_status("RCON is unavailable until RCON host, port, and password are saved.")
            return

        existing = self._console_windows.get(server.local_id)
        if existing is not None and existing.window.winfo_exists():
            existing.present()
            return

        console = ConsoleWindow(self.root, create_rcon_service(server), server.display_name)
        self._console_windows[server.local_id] = console
        console.present()

    def _run_background(self, task, on_success, *, start_message: str) -> None:
        if self._busy:
            return

        self._busy = True
        self._set_status(start_message)
        self._update_button_states()
        future: Future = self._executor.submit(task)

        def poll() -> None:
            if not self.root.winfo_exists():
                return
            if not future.done():
                self.root.after(75, poll)
                return

            self._busy = False
            self._update_button_states()
            try:
                result = future.result()
            except Exception as exc:  # noqa: BLE001
                message = str(exc)
                messagebox.showerror("Minecraft Server Manager", message, parent=self.root)
                self._set_status(message)
                return

            on_success(result)

        self.root.after(75, poll)

    def _set_status(self, message: str) -> None:
        self.status_message_var.set(message)


def _format_bytes(value: int | None) -> str:
    if value is None:
        return "Unknown"
    size = float(value)
    units = ["B", "KB", "MB", "GB", "TB"]
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _format_cpu(value: float | None) -> str:
    if value is None:
        return "Unknown"
    return f"{value:.2f}%"


def _button_state(base_state: str, enabled: bool) -> str:
    return base_state if enabled else "disabled"


def _power_signal_enabled(signal: ProviderPowerSignal, power_state: str | None) -> bool:
    if power_state is None:
        return True

    normalized = power_state.strip().lower()
    if normalized == "running":
        return signal is not ProviderPowerSignal.START
    if normalized in {"offline", "stopped"}:
        return signal is ProviderPowerSignal.START
    if normalized in {"starting", "stopping", "restarting"}:
        return False
    return True
