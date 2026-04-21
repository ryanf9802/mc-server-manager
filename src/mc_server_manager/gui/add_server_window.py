from __future__ import annotations

import tkinter as tk
from concurrent.futures import Future, ThreadPoolExecutor
from tkinter import messagebox, ttk
from typing import cast

from mc_server_manager.app_icon import apply_window_icon
from mc_server_manager.domain.models import (
    HostingProvider,
    ProviderConnection,
    ProviderServerSummary,
    StoredServerConfig,
)
from mc_server_manager.infrastructure.app_state_store import AppStateStore
from mc_server_manager.infrastructure.provider_clients import ProviderClientFactory


class AddServerWindow:
    def __init__(self, parent: tk.Misc) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._busy = False
        self._result: StoredServerConfig | None = None
        self._servers: list[ProviderServerSummary] = []

        self.window = tk.Toplevel(parent)
        apply_window_icon(self.window)
        self.window.title("Add Server")
        self.window.geometry("760x520")
        self.window.minsize(680, 480)
        self.window.transient(cast(tk.Wm, parent))
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        self.provider_var = tk.StringVar(value=HostingProvider.GAMEHOSTBROS.label)
        self.api_token_var = tk.StringVar()
        self.status_var = tk.StringVar(
            value="Enter the GameHostBros API token and fetch available servers."
        )

        self._build_layout()
        self._bind_events()
        self._update_button_states()

    def show(self) -> StoredServerConfig | None:
        self.window.grab_set()
        self.window.wait_window()
        return self._result

    def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
        if self.window.winfo_exists():
            self.window.destroy()

    def _build_layout(self) -> None:
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(1, weight=1)

        form = ttk.LabelFrame(self.window, text="Provider Discovery", padding=16)
        form.grid(row=0, column=0, sticky="ew", padx=16, pady=16)
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Provider").grid(row=0, column=0, sticky="w")
        provider_box = ttk.Combobox(
            form,
            textvariable=self.provider_var,
            values=[HostingProvider.GAMEHOSTBROS.label],
            state="readonly",
        )
        provider_box.grid(row=0, column=1, sticky="ew")

        ttk.Label(form, text="Panel").grid(row=1, column=0, sticky="w", pady=(12, 0))
        ttk.Label(
            form,
            text=HostingProvider.GAMEHOSTBROS.default_panel_url,
        ).grid(row=1, column=1, sticky="w", pady=(12, 0))

        ttk.Label(form, text="API Token").grid(row=2, column=0, sticky="w", pady=(12, 0))
        ttk.Entry(form, textvariable=self.api_token_var, show="*").grid(
            row=2,
            column=1,
            sticky="ew",
            pady=(12, 0),
        )

        self.fetch_button = ttk.Button(
            form,
            text="Fetch Accessible Servers",
            command=self.fetch_servers,
        )
        self.fetch_button.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(16, 0))

        list_frame = ttk.LabelFrame(self.window, text="Discovered Servers", padding=16)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=16)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        self.server_listbox = tk.Listbox(list_frame, activestyle="dotbox", exportselection=False)
        self.server_listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.server_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.server_listbox.configure(yscrollcommand=scrollbar.set)

        footer = ttk.Frame(self.window, padding=16)
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=self.status_var).grid(row=0, column=0, sticky="w")

        action_row = ttk.Frame(footer)
        action_row.grid(row=1, column=0, sticky="e", pady=(12, 0))
        self.continue_button = ttk.Button(
            action_row,
            text="Continue",
            command=self.continue_with_selected,
        )
        self.continue_button.grid(row=0, column=0)
        ttk.Button(action_row, text="Cancel", command=self.close).grid(row=0, column=1, padx=(8, 0))

    def _bind_events(self) -> None:
        self.api_token_var.trace_add("write", lambda *_: self._update_button_states())
        self.server_listbox.bind("<<ListboxSelect>>", lambda _event: self._update_button_states())

    def fetch_servers(self) -> None:
        api_token = self.api_token_var.get().strip()
        if not api_token:
            self._set_status("API token is required before discovery.")
            return

        connection = ProviderConnection(
            provider=HostingProvider.GAMEHOSTBROS,
            api_token=api_token,
            server_id="",
            server_uuid="",
            server_name="",
        )

        def task() -> list[ProviderServerSummary]:
            client = ProviderClientFactory().create(connection)
            return client.list_servers()

        def on_success(servers: list[ProviderServerSummary]) -> None:
            self._servers = servers
            self.server_listbox.delete(0, tk.END)
            for server in servers:
                self.server_listbox.insert(tk.END, f"{server.name} ({server.server_id})")
            if servers:
                self.server_listbox.selection_set(0)
                self.server_listbox.activate(0)
            self._set_status(f"Discovered {len(servers)} server(s).")
            self._update_button_states()

        self._run_background(
            task,
            on_success,
            start_message="Fetching GameHostBros servers...",
        )

    def continue_with_selected(self) -> None:
        selection = self.server_listbox.curselection()
        if not selection:
            self._set_status("Select a discovered server before continuing.")
            return
        summary = self._servers[selection[0]]
        self._result = StoredServerConfig(
            local_id=AppStateStore.create_local_id(),
            display_name=summary.name,
            provider=ProviderConnection(
                provider=HostingProvider.GAMEHOSTBROS,
                api_token=self.api_token_var.get().strip(),
                server_id=summary.server_id,
                server_uuid=summary.server_uuid,
                server_name=summary.name,
            ),
        )
        self.close()

    def _run_background(self, task, on_success, *, start_message: str) -> None:
        if self._busy:
            return

        self._busy = True
        self._set_status(start_message)
        self._update_button_states()
        future: Future = self._executor.submit(task)

        def poll() -> None:
            if not self.window.winfo_exists():
                return
            if not future.done():
                self.window.after(75, poll)
                return

            self._busy = False
            try:
                result = future.result()
            except Exception as exc:  # noqa: BLE001
                message = str(exc)
                messagebox.showerror("Add Server", message, parent=self.window)
                self._set_status(message)
                self._update_button_states()
                return

            on_success(result)
            self._update_button_states()

        self.window.after(75, poll)

    def _set_status(self, message: str) -> None:
        self.status_var.set(message)

    def _update_button_states(self) -> None:
        not_busy = not self._busy
        has_credentials = bool(self.api_token_var.get().strip())
        has_selection = bool(self.server_listbox.curselection())
        self.fetch_button.configure(state="normal" if not_busy and has_credentials else "disabled")
        self.continue_button.configure(state="normal" if not_busy and has_selection else "disabled")
