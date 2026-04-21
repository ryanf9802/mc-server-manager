from __future__ import annotations

import tkinter as tk
from concurrent.futures import Future, ThreadPoolExecutor
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from mc_server_manager.app_icon import apply_window_icon
from mc_server_manager.domain.models import RconCommandResult
from mc_server_manager.services.rcon import RconService


class ConsoleWindow:
    def __init__(
        self,
        parent: tk.Misc,
        rcon_service: RconService,
        server_display_name: str | None = None,
    ) -> None:
        self._rcon_service = rcon_service
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._busy = False
        self._closed = False

        self.window = tk.Toplevel(parent)
        apply_window_icon(self.window)
        title_suffix = "" if not server_display_name else f": {server_display_name}"
        self.window.title(f"RCON Console{title_suffix}")
        self.window.geometry("920x560")
        self.window.minsize(720, 420)
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        self.command_var = tk.StringVar()
        self.status_var = tk.StringVar(value=self._rcon_service.availability_message)

        self._build_layout()
        self._bind_events()
        self._append_system_message(self._rcon_service.availability_message)
        self._update_button_states()

    def present(self) -> None:
        self.window.deiconify()
        self.window.lift()
        self.window.focus_force()

    def close(self) -> None:
        self._closed = True
        self._executor.shutdown(wait=False, cancel_futures=True)
        self._rcon_service.close()
        self.window.destroy()

    def _build_layout(self) -> None:
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(1, weight=1)

        header = ttk.Frame(self.window, padding=16)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        header.columnconfigure(1, weight=1)

        ttk.Label(
            header,
            text="Send Minecraft RCON commands and review session-only responses.",
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(header, textvariable=self.status_var).grid(row=0, column=1, sticky="e")

        transcript_frame = ttk.LabelFrame(self.window, text="Transcript", padding=12)
        transcript_frame.grid(row=1, column=0, sticky="nsew", padx=16)
        transcript_frame.columnconfigure(0, weight=1)
        transcript_frame.rowconfigure(0, weight=1)

        self.transcript_text = ScrolledText(
            transcript_frame,
            wrap="word",
            undo=False,
            font=("Courier New", 10),
            state=tk.DISABLED,
        )
        self.transcript_text.grid(row=0, column=0, sticky="nsew")

        controls = ttk.Frame(self.window, padding=16)
        controls.grid(row=2, column=0, sticky="ew")
        controls.columnconfigure(0, weight=1)

        self.command_entry = ttk.Entry(controls, textvariable=self.command_var)
        self.command_entry.grid(row=0, column=0, sticky="ew")

        self.send_button = ttk.Button(controls, text="Send", command=self.send_command)
        self.send_button.grid(row=0, column=1, padx=(8, 0))

        self.test_button = ttk.Button(
            controls,
            text="Test Connection",
            command=self.test_connection,
        )
        self.test_button.grid(row=0, column=2, padx=(8, 0))

        self.clear_button = ttk.Button(controls, text="Clear", command=self.clear_transcript)
        self.clear_button.grid(row=0, column=3, padx=(8, 0))

        self.close_button = ttk.Button(controls, text="Close", command=self.close)
        self.close_button.grid(row=0, column=4, padx=(8, 0))

    def _bind_events(self) -> None:
        self.command_var.trace_add("write", lambda *_: self._update_button_states())
        self.command_entry.bind("<Return>", self._on_enter_pressed)

    def send_command(self) -> None:
        command = self.command_var.get().strip()
        if not command:
            self._set_status("Enter an RCON command before sending.")
            return

        self._run_background(
            lambda: self._rcon_service.execute(command),
            self._handle_command_success,
            start_message=f"Sending RCON command: {command}",
        )

    def test_connection(self) -> None:
        self._run_background(
            self._rcon_service.test_connection,
            self._handle_test_success,
            start_message="Testing RCON connection...",
        )

    def clear_transcript(self) -> None:
        self.transcript_text.configure(state=tk.NORMAL)
        self.transcript_text.delete("1.0", tk.END)
        self.transcript_text.configure(state=tk.DISABLED)
        self._set_status(self._rcon_service.availability_message)

    def _handle_command_success(self, result: RconCommandResult) -> None:
        timestamp = result.executed_at.astimezone().strftime("%Y-%m-%d %H:%M:%S")
        self._append_transcript(f"[{timestamp}] > {result.command}")
        self._append_transcript(result.response_text)
        self._append_transcript("")
        self.command_var.set("")
        self._set_status("RCON command completed.")

    def _handle_test_success(self, message: str) -> None:
        self._append_system_message(message)
        self._set_status(message)

    def _append_system_message(self, message: str) -> None:
        self._append_transcript(f"[system] {message}")
        self._append_transcript("")

    def _append_transcript(self, text: str) -> None:
        self.transcript_text.configure(state=tk.NORMAL)
        self.transcript_text.insert(tk.END, f"{text}\n")
        self.transcript_text.see(tk.END)
        self.transcript_text.configure(state=tk.DISABLED)

    def _on_enter_pressed(self, _event: tk.Event) -> str | None:
        if self.send_button.instate(("disabled",)):
            return None
        self.send_command()
        return "break"

    def _run_background(self, task, on_success, *, start_message: str) -> None:
        if self._busy:
            return

        self._busy = True
        self._set_status(start_message)
        self._update_button_states()
        future: Future = self._executor.submit(task)

        def poll() -> None:
            if self._closed or not self.window.winfo_exists():
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
                self._append_system_message(message)
                self._set_status(message)
                messagebox.showerror("RCON Console", message, parent=self.window)
                return
            on_success(result)

        self.window.after(75, poll)

    def _update_button_states(self) -> None:
        rcon_available = self._rcon_service.is_available
        not_busy = not self._busy
        has_command = bool(self.command_var.get().strip())

        self.command_entry.configure(state="normal" if rcon_available and not_busy else "disabled")
        self.send_button.configure(
            state="normal" if rcon_available and not_busy and has_command else "disabled"
        )
        self.test_button.configure(state="normal" if rcon_available and not_busy else "disabled")
        self.clear_button.configure(state="normal" if not_busy else "disabled")
        self.close_button.configure(state="normal")

    def _set_status(self, message: str) -> None:
        self.status_var.set(message)
