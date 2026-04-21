from __future__ import annotations

import tkinter as tk
from concurrent.futures import Future, ThreadPoolExecutor
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from typing import cast

from mc_server_manager.domain.models import (
    HostingProvider,
    ProviderConnection,
    RconConnectionSettings,
    StoredServerConfig,
)
from mc_server_manager.services.server_runtime import (
    create_provider_client,
    create_rcon_service,
    test_sftp_connection,
)
from mc_server_manager.services.sftp_connection_address import (
    build_gamehostbros_sftp_settings,
    format_gamehostbros_sftp_address,
)


class ServerSettingsWindow:
    def __init__(self, parent: tk.Misc, server: StoredServerConfig, *, mode: str) -> None:
        self._server = server
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._busy = False
        self._result: StoredServerConfig | None = None

        self.window = tk.Toplevel(parent)
        self.window.title("Complete Server Settings" if mode == "create" else "Server Settings")
        self.window.geometry("880x760")
        self.window.minsize(760, 680)
        self.window.transient(cast(tk.Wm, parent))
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        self.display_name_var = tk.StringVar(value=server.display_name)
        self.provider_var = tk.StringVar(value=server.provider.provider.label)
        self.api_token_var = tk.StringVar(value=server.provider.api_token)
        self.server_id_var = tk.StringVar(value=server.provider.server_id)
        self.server_uuid_var = tk.StringVar(value=server.provider.server_uuid)
        self.server_name_var = tk.StringVar(value=server.provider.server_name)
        self.sftp_connection_address_var = tk.StringVar(
            value=""
            if server.sftp is None
            else format_gamehostbros_sftp_address(server.sftp.host, server.sftp.port)
        )
        self.sftp_username_var = tk.StringVar(
            value="" if server.sftp is None else server.sftp.username
        )
        self.sftp_password_var = tk.StringVar(
            value="" if server.sftp is None else server.sftp.password
        )
        self.rcon_host_var = tk.StringVar(value="" if server.rcon is None else server.rcon.host)
        self.rcon_port_var = tk.StringVar(
            value="" if server.rcon is None else str(server.rcon.port)
        )
        self.rcon_password_var = tk.StringVar(
            value="" if server.rcon is None else server.rcon.password
        )
        self.status_var = tk.StringVar(
            value="Complete the GameHostBros, SFTP, and optional RCON settings for this server."
        )

        self._build_layout()
        self._load_notes(server.notes)
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
        self.window.rowconfigure(3, weight=1)

        basics = ttk.LabelFrame(self.window, text="Server Identity", padding=16)
        basics.grid(row=0, column=0, sticky="ew", padx=16, pady=16)
        basics.columnconfigure(1, weight=1)

        ttk.Label(basics, text="Display Name").grid(row=0, column=0, sticky="w")
        ttk.Entry(basics, textvariable=self.display_name_var).grid(row=0, column=1, sticky="ew")

        ttk.Label(basics, text="Provider").grid(row=1, column=0, sticky="w", pady=(12, 0))
        provider_box = ttk.Combobox(
            basics,
            textvariable=self.provider_var,
            values=[HostingProvider.GAMEHOSTBROS.label],
            state="readonly",
        )
        provider_box.grid(row=1, column=1, sticky="ew", pady=(12, 0))

        provider = ttk.LabelFrame(self.window, text="Provider Connection", padding=16)
        provider.grid(row=1, column=0, sticky="ew", padx=16)
        provider.columnconfigure(1, weight=1)

        ttk.Label(provider, text="Panel").grid(row=0, column=0, sticky="w")
        ttk.Label(provider, text=HostingProvider.GAMEHOSTBROS.default_panel_url).grid(
            row=0, column=1, sticky="w"
        )
        ttk.Label(provider, text="API Token").grid(row=1, column=0, sticky="w", pady=(12, 0))
        ttk.Entry(provider, textvariable=self.api_token_var, show="*").grid(
            row=1, column=1, sticky="ew", pady=(12, 0)
        )
        ttk.Label(provider, text="Server ID").grid(row=2, column=0, sticky="w", pady=(12, 0))
        ttk.Entry(provider, textvariable=self.server_id_var).grid(
            row=2, column=1, sticky="ew", pady=(12, 0)
        )
        ttk.Label(provider, text="Server UUID").grid(row=3, column=0, sticky="w", pady=(12, 0))
        ttk.Entry(provider, textvariable=self.server_uuid_var).grid(
            row=3, column=1, sticky="ew", pady=(12, 0)
        )
        ttk.Label(provider, text="Provider Server Name").grid(
            row=4, column=0, sticky="w", pady=(12, 0)
        )
        ttk.Entry(provider, textvariable=self.server_name_var).grid(
            row=4, column=1, sticky="ew", pady=(12, 0)
        )
        self.provider_test_button = ttk.Button(
            provider,
            text="Test Provider API",
            command=self.test_provider_connection,
        )
        self.provider_test_button.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(16, 0))

        lower = ttk.Frame(self.window, padding=16)
        lower.grid(row=2, column=0, sticky="nsew")
        lower.columnconfigure(0, weight=1)
        lower.columnconfigure(1, weight=1)
        lower.rowconfigure(0, weight=1)

        sftp = ttk.LabelFrame(lower, text="SFTP", padding=16)
        sftp.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        sftp.columnconfigure(1, weight=1)
        self._build_sftp_fields(sftp)
        self.sftp_test_button = ttk.Button(sftp, text="Test SFTP", command=self.test_sftp)
        self.sftp_test_button.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(16, 0))

        rcon = ttk.LabelFrame(lower, text="RCON", padding=16)
        rcon.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        rcon.columnconfigure(1, weight=1)
        _add_entry_row(rcon, 0, "Host", self.rcon_host_var)
        _add_entry_row(rcon, 1, "Port", self.rcon_port_var)
        _add_entry_row(rcon, 2, "Password", self.rcon_password_var, show="*")
        self.rcon_test_button = ttk.Button(rcon, text="Test RCON", command=self.test_rcon)
        self.rcon_test_button.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(16, 0))

        notes_frame = ttk.LabelFrame(self.window, text="Notes", padding=16)
        notes_frame.grid(row=3, column=0, sticky="nsew", padx=16, pady=(0, 16))
        notes_frame.columnconfigure(0, weight=1)
        notes_frame.rowconfigure(0, weight=1)
        self.notes_text = ScrolledText(notes_frame, height=5, wrap="word")
        self.notes_text.grid(row=0, column=0, sticky="nsew")

        footer = ttk.Frame(self.window, padding=(16, 0, 16, 16))
        footer.grid(row=4, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=self.status_var).grid(row=0, column=0, sticky="w")

        actions = ttk.Frame(footer)
        actions.grid(row=1, column=0, sticky="e", pady=(12, 0))
        self.save_button = ttk.Button(actions, text="Save", command=self.save)
        self.save_button.grid(row=0, column=0)
        ttk.Button(actions, text="Cancel", command=self.close).grid(row=0, column=1, padx=(8, 0))

    def _load_notes(self, notes: str) -> None:
        self.notes_text.insert("1.0", notes)

    def save(self) -> None:
        try:
            self._result = self._build_server()
        except ValueError as exc:
            self._set_status(str(exc))
            messagebox.showerror("Server Settings", str(exc), parent=self.window)
            return
        self.close()

    def test_provider_connection(self) -> None:
        try:
            server = self._build_server()
        except ValueError as exc:
            self._set_status(str(exc))
            return

        def task() -> str:
            client = create_provider_client(server)
            return client.test_connection()

        self._run_background(task, self._set_status, start_message="Testing provider API...")

    def test_sftp(self) -> None:
        try:
            server = self._build_server(require_sftp=True)
        except ValueError as exc:
            self._set_status(str(exc))
            return

        def task() -> str:
            return test_sftp_connection(server)

        self._run_background(task, self._set_status, start_message="Testing SFTP...")

    def test_rcon(self) -> None:
        try:
            server = self._build_server(require_rcon=True)
        except ValueError as exc:
            self._set_status(str(exc))
            return

        def task() -> str:
            service = create_rcon_service(server)
            try:
                return service.test_connection()
            finally:
                service.close()

        self._run_background(task, self._set_status, start_message="Testing RCON...")

    def _build_server(
        self,
        *,
        require_sftp: bool = False,
        require_rcon: bool = False,
    ) -> StoredServerConfig:
        display_name = self.display_name_var.get().strip()
        if not display_name:
            raise ValueError("Display name is required.")

        api_token = self.api_token_var.get().strip()
        server_id = self.server_id_var.get().strip()
        server_uuid = self.server_uuid_var.get().strip()
        server_name = self.server_name_var.get().strip()
        if not api_token or not server_id or not server_uuid or not server_name:
            raise ValueError(
                "API token, server ID, server UUID, and provider server name are required."
            )

        provider = self._selected_provider()
        sftp = self._build_provider_sftp_settings(provider, require=require_sftp)
        rcon = _build_optional_rcon(
            host=self.rcon_host_var.get().strip(),
            port=self.rcon_port_var.get().strip(),
            password=self.rcon_password_var.get().strip(),
            require=require_rcon,
        )
        return StoredServerConfig(
            local_id=self._server.local_id,
            display_name=display_name,
            provider=ProviderConnection(
                provider=provider,
                api_token=api_token,
                server_id=server_id,
                server_uuid=server_uuid,
                server_name=server_name,
            ),
            sftp=sftp,
            rcon=rcon,
            notes=self.notes_text.get("1.0", tk.END).strip(),
        )

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
            self._update_button_states()
            try:
                result = future.result()
            except Exception as exc:  # noqa: BLE001
                message = str(exc)
                messagebox.showerror("Server Settings", message, parent=self.window)
                self._set_status(message)
                return
            on_success(result)

        self.window.after(75, poll)

    def _set_status(self, message: str) -> None:
        self.status_var.set(message)

    def _update_button_states(self) -> None:
        state = "disabled" if self._busy else "normal"
        self.provider_test_button.configure(state=state)
        self.sftp_test_button.configure(state=state)
        self.rcon_test_button.configure(state=state)
        self.save_button.configure(state=state)

    def _build_sftp_fields(self, frame: ttk.LabelFrame) -> None:
        provider = self._selected_provider()
        if provider is HostingProvider.GAMEHOSTBROS:
            _add_entry_row(frame, 0, "Connection Address", self.sftp_connection_address_var)
            _add_entry_row(frame, 1, "Username", self.sftp_username_var)
            _add_entry_row(frame, 2, "Password", self.sftp_password_var, show="*")
            ttk.Label(
                frame,
                text="GameHostBros mounts the server filesystem at / for SFTP.",
            ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(12, 0))
            return
        raise ValueError(f"Unsupported hosting provider: {provider}")

    def _build_provider_sftp_settings(
        self,
        provider: HostingProvider,
        *,
        require: bool,
    ):
        if provider is HostingProvider.GAMEHOSTBROS:
            return build_gamehostbros_sftp_settings(
                connection_address=self.sftp_connection_address_var.get(),
                username=self.sftp_username_var.get(),
                password=self.sftp_password_var.get(),
                require=require,
            )
        raise ValueError(f"Unsupported hosting provider: {provider}")

    def _selected_provider(self) -> HostingProvider:
        selected_label = self.provider_var.get().strip()
        for provider in HostingProvider:
            if provider.label == selected_label:
                return provider
        raise ValueError(f"Unsupported hosting provider: {selected_label}")


def _add_entry_row(
    frame: ttk.LabelFrame | ttk.Frame,
    row: int,
    label: str,
    variable: tk.StringVar,
    *,
    show: str | None = None,
) -> None:
    ttk.Label(frame, text=label).grid(
        row=row, column=0, sticky="w", pady=(0 if row == 0 else 12, 0)
    )
    entry = ttk.Entry(frame, textvariable=variable, show=show or "")
    entry.grid(row=row, column=1, sticky="ew", pady=(0 if row == 0 else 12, 0))


def _build_optional_rcon(
    *,
    host: str,
    port: str,
    password: str,
    require: bool,
) -> RconConnectionSettings | None:
    values = [host, port, password]
    if not any(values):
        if require:
            raise ValueError("RCON host, port, and password are required.")
        return None
    if not all(values):
        raise ValueError("Either fill all RCON fields or leave all of them empty.")
    try:
        parsed_port = int(port)
    except ValueError as exc:
        raise ValueError("RCON port must be a valid integer.") from exc
    return RconConnectionSettings(host=host, port=parsed_port, password=password)
