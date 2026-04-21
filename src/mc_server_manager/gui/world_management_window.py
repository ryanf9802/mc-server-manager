from __future__ import annotations

import tkinter as tk
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from mc_server_manager.domain.models import (
    StoredServerConfig,
    WorldDetail,
    WorldFileSet,
    WorldManifest,
    WorldStatus,
)


@dataclass(slots=True)
class EditorSession:
    manifest: WorldManifest
    status: WorldStatus
    persisted: bool
    original_server_properties_text: str
    original_whitelist_json_text: str


class WorldManagementWindow:
    def __init__(
        self,
        parent: tk.Misc,
        server: StoredServerConfig,
        world_catalog_service,
        world_editor_service,
        activation_service,
    ) -> None:
        self._server = server
        self._world_catalog_service = world_catalog_service
        self._world_editor_service = world_editor_service
        self._activation_service = activation_service

        self._executor = ThreadPoolExecutor(max_workers=1)
        self._session: EditorSession | None = None
        self._world_summaries = []
        self._selected_slug: str | None = None
        self._busy = False
        self._closed = False
        self._suspend_dirty_tracking = False

        self.window = tk.Toplevel(parent)
        self.window.title(f"World Management: {server.display_name}")
        self.window.geometry("1320x860")
        self.window.minsize(1100, 720)
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        self.new_world_name_var = tk.StringVar()
        self.display_name_var = tk.StringVar()
        self.current_status_var = tk.StringVar(value="Status: No world selected")
        self.current_slug_var = tk.StringVar(value="")
        self.dirty_var = tk.StringVar(value="Saved state loaded")
        self.status_message_var = tk.StringVar(value="Load a world or create a draft to begin.")

        self._build_layout()
        self._bind_events()
        self._update_button_states()
        self.refresh_worlds()

    def present(self) -> None:
        self.window.deiconify()
        self.window.lift()
        self.window.focus_force()

    def close(self) -> None:
        self._closed = True
        self._executor.shutdown(wait=False, cancel_futures=True)
        self.window.destroy()

    def _build_layout(self) -> None:
        self.window.columnconfigure(0, weight=3, minsize=360)
        self.window.columnconfigure(1, weight=7)
        self.window.rowconfigure(1, weight=1)

        sidebar = ttk.Frame(self.window, padding=16)
        sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        sidebar.columnconfigure(0, weight=1)
        sidebar.rowconfigure(3, weight=1)

        self.refresh_button = ttk.Button(sidebar, text="Refresh", command=self.refresh_worlds)
        self.refresh_button.grid(row=0, column=0, sticky="ew")

        new_world_frame = ttk.LabelFrame(sidebar, text="Create World", padding=12)
        new_world_frame.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        new_world_frame.columnconfigure(0, weight=1)
        ttk.Entry(new_world_frame, textvariable=self.new_world_name_var).grid(
            row=0, column=0, sticky="ew"
        )
        self.create_button = ttk.Button(
            new_world_frame, text="Create Draft", command=self.create_draft
        )
        self.create_button.grid(row=1, column=0, sticky="ew", pady=(10, 0))

        worlds_frame = ttk.LabelFrame(sidebar, text="Worlds", padding=12)
        worlds_frame.grid(row=3, column=0, sticky="nsew", pady=(12, 0))
        worlds_frame.columnconfigure(0, weight=1)
        worlds_frame.rowconfigure(0, weight=1)

        self.world_listbox = tk.Listbox(worlds_frame, activestyle="dotbox")
        self.world_listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(worlds_frame, orient="vertical", command=self.world_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.world_listbox.configure(yscrollcommand=scrollbar.set)

        header = ttk.LabelFrame(self.window, text="Selected World", padding=16)
        header.grid(row=0, column=1, sticky="nsew", padx=(0, 16), pady=(16, 0))
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="Display name").grid(row=0, column=0, sticky="w")
        self.display_name_entry = ttk.Entry(header, textvariable=self.display_name_var)
        self.display_name_entry.grid(row=1, column=0, sticky="ew", pady=(4, 12))

        actions = ttk.Frame(header)
        actions.grid(row=2, column=0, sticky="ew")
        for column in range(4):
            actions.columnconfigure(column, weight=1)

        self.save_button = ttk.Button(actions, text="Save", command=self.save_world)
        self.save_button.grid(row=0, column=0, sticky="ew")
        self.activate_button = ttk.Button(actions, text="Activate", command=self.activate_world)
        self.activate_button.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        self.revert_button = ttk.Button(actions, text="Revert", command=self.revert_world)
        self.revert_button.grid(row=0, column=2, sticky="ew", padx=(8, 0))
        self.delete_button = ttk.Button(actions, text="Delete", command=self.delete_world)
        self.delete_button.grid(row=0, column=3, sticky="ew", padx=(8, 0))

        metadata = ttk.Frame(header)
        metadata.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        metadata.columnconfigure(0, weight=1)
        metadata.columnconfigure(1, weight=1)
        metadata.columnconfigure(2, weight=1)
        ttk.Label(metadata, textvariable=self.current_status_var).grid(row=0, column=0, sticky="w")
        ttk.Label(metadata, textvariable=self.current_slug_var).grid(row=0, column=1, sticky="w")
        ttk.Label(metadata, textvariable=self.dirty_var).grid(row=0, column=2, sticky="w")

        editors = ttk.Frame(self.window, padding=(0, 16, 16, 0))
        editors.grid(row=1, column=1, sticky="nsew")
        editors.columnconfigure(0, weight=1)
        editors.columnconfigure(1, weight=1)
        editors.rowconfigure(0, weight=1)

        server_frame = ttk.LabelFrame(editors, text="server.properties", padding=12)
        server_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        server_frame.columnconfigure(0, weight=1)
        server_frame.rowconfigure(0, weight=1)
        self.server_properties_text = ScrolledText(
            server_frame, wrap="none", undo=True, font=("Courier New", 10)
        )
        self.server_properties_text.grid(row=0, column=0, sticky="nsew")

        whitelist_frame = ttk.LabelFrame(editors, text="whitelist.json", padding=12)
        whitelist_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        whitelist_frame.columnconfigure(0, weight=1)
        whitelist_frame.rowconfigure(0, weight=1)
        self.whitelist_text = ScrolledText(
            whitelist_frame, wrap="none", undo=True, font=("Courier New", 10)
        )
        self.whitelist_text.grid(row=0, column=0, sticky="nsew")

        status_bar = ttk.Frame(self.window, padding=(16, 8))
        status_bar.grid(row=2, column=0, columnspan=2, sticky="ew")
        status_bar.columnconfigure(0, weight=1)
        ttk.Label(status_bar, textvariable=self.status_message_var, anchor="w").grid(
            row=0, column=0, sticky="ew"
        )

    def _bind_events(self) -> None:
        self.world_listbox.bind("<<ListboxSelect>>", self._on_world_selected)
        self.new_world_name_var.trace_add("write", lambda *_: self._update_button_states())
        self.display_name_var.trace_add("write", lambda *_: self._on_editor_changed())
        self.server_properties_text.bind("<<Modified>>", self._on_text_modified)
        self.whitelist_text.bind("<<Modified>>", self._on_text_modified)

    def _on_text_modified(self, event: tk.Event) -> None:
        widget = event.widget
        if isinstance(widget, ScrolledText):
            widget.edit_modified(False)
        self._on_editor_changed()

    def _on_editor_changed(self) -> None:
        if self._suspend_dirty_tracking:
            return
        self._update_dirty_label()

    def refresh_worlds(self) -> None:
        current_slug = (
            self._session.manifest.slug if self._session and self._session.persisted else None
        )

        def task() -> tuple[list, WorldDetail | None]:
            worlds = self._world_catalog_service.get_worlds()
            current_detail = (
                self._world_catalog_service.get_world(current_slug) if current_slug else None
            )
            return worlds, current_detail

        def on_success(result: tuple[list, WorldDetail | None]) -> None:
            worlds, current_detail = result
            self._world_summaries = worlds
            self._render_worlds()
            if current_detail is not None:
                self._apply_detail(current_detail, persisted=True)
                self._select_slug(current_detail.manifest.slug)
            elif current_slug is not None and self._session and self._session.persisted:
                self._clear_editor()
            self._set_status(
                "No managed worlds found yet. Create a draft from the live files to start."
                if not worlds
                else f"Loaded {len(worlds)} managed world(s)."
            )

        self._run_background(task, on_success, start_message="Refreshing remote worlds...")

    def create_draft(self) -> None:
        display_name = self.new_world_name_var.get().strip()
        if not display_name:
            self._set_status("Enter a world name before creating a draft.")
            return

        def task() -> WorldDetail:
            return self._world_editor_service.create_draft_from_live(display_name)

        def on_success(detail: WorldDetail) -> None:
            self._apply_detail(detail, persisted=False)
            self.new_world_name_var.set("")
            self.world_listbox.selection_clear(0, tk.END)
            self._selected_slug = None
            self._set_status(
                f"Drafted '{detail.manifest.display_name}' from the current live remote files."
            )

        self._run_background(
            task, on_success, start_message="Creating draft from live remote files..."
        )

    def save_world(self) -> None:
        detail = self._collect_current_detail()
        if detail is None:
            return

        def task() -> tuple[list, WorldDetail | None]:
            saved = self._world_editor_service.save_world(detail)
            worlds = self._world_catalog_service.get_worlds()
            refreshed = self._world_catalog_service.get_world(saved.manifest.slug)
            return worlds, refreshed

        def on_success(result: tuple[list, WorldDetail | None]) -> None:
            worlds, refreshed = result
            self._world_summaries = worlds
            self._render_worlds()
            if refreshed is not None:
                self._apply_detail(refreshed, persisted=True)
                self._select_slug(refreshed.manifest.slug)
            self._set_status(
                f"Saved '{detail.manifest.display_name.strip()}' to the managed remote world store."
            )

        self._run_background(task, on_success, start_message="Saving managed world to SFTP...")

    def activate_world(self) -> None:
        detail = self._collect_current_detail()
        if detail is None:
            return

        def task() -> tuple[list, WorldDetail | None]:
            target_detail = detail
            if not self._session or not self._session.persisted or self._is_dirty():
                target_detail = self._world_editor_service.save_world(detail)
            self._activation_service.activate_world(target_detail.manifest.slug)
            worlds = self._world_catalog_service.get_worlds()
            refreshed = self._world_catalog_service.get_world(target_detail.manifest.slug)
            return worlds, refreshed

        def on_success(result: tuple[list, WorldDetail | None]) -> None:
            worlds, refreshed = result
            self._world_summaries = worlds
            self._render_worlds()
            if refreshed is not None:
                self._apply_detail(refreshed, persisted=True)
                self._select_slug(refreshed.manifest.slug)
                self._set_status(
                    f"Activated '{refreshed.manifest.display_name}'. Live files now match this world."
                )

        self._run_background(
            task, on_success, start_message="Activating world on the remote server..."
        )

    def revert_world(self) -> None:
        if self._session is None:
            self._clear_editor()
            self._set_status("Draft cleared.")
            return

        if not self._session.persisted:
            self._clear_editor()
            self._set_status("Discarded the unsaved draft.")
            return

        slug = self._session.manifest.slug

        def task() -> WorldDetail | None:
            return self._world_catalog_service.get_world(slug)

        def on_success(detail: WorldDetail | None) -> None:
            if detail is None:
                self._clear_editor()
                self._set_status(f"World '{slug}' no longer exists on the remote host.")
                return
            self._apply_detail(detail, persisted=True)
            self._select_slug(slug)
            self._set_status(
                f"Reloaded '{detail.manifest.display_name}' from the remote world store."
            )

        self._run_background(task, on_success, start_message="Reloading world from SFTP...")

    def delete_world(self) -> None:
        if self._session is None:
            return

        if not self._session.persisted:
            self._clear_editor()
            self._set_status("Discarded the unsaved draft.")
            return

        if not messagebox.askyesno(
            "Delete World",
            f"Delete '{self._session.manifest.display_name}' from the managed remote store?",
            parent=self.window,
        ):
            return

        slug = self._session.manifest.slug

        def task() -> list:
            self._world_editor_service.delete_world(slug)
            return self._world_catalog_service.get_worlds()

        def on_success(worlds: list) -> None:
            self._world_summaries = worlds
            self._render_worlds()
            self._clear_editor()
            self._set_status("Deleted the selected managed world.")

        self._run_background(task, on_success, start_message="Deleting managed world from SFTP...")

    def _on_world_selected(self, _event: tk.Event) -> None:
        selection = self.world_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        slug = self._world_summaries[index].manifest.slug
        if slug == self._selected_slug:
            return

        def task() -> WorldDetail | None:
            return self._world_catalog_service.get_world(slug)

        def on_success(detail: WorldDetail | None) -> None:
            self._selected_slug = slug
            if detail is None:
                self._set_status(f"World '{slug}' no longer exists on the remote host.")
                self.refresh_worlds()
                return
            self._apply_detail(detail, persisted=True)
            self._set_status(
                f"Loaded '{detail.manifest.display_name}' from the remote world store."
            )

        self._run_background(task, on_success, start_message="Loading world from SFTP...")

    def _collect_current_detail(self) -> WorldDetail | None:
        if self._session is None:
            self._set_status("No world is currently selected.")
            return None

        return WorldDetail(
            manifest=WorldManifest(
                slug=self._session.manifest.slug,
                display_name=self.display_name_var.get().strip(),
                created_at_utc=self._session.manifest.created_at_utc,
                updated_at_utc=self._session.manifest.updated_at_utc,
            ),
            files=self._collect_files(),
            status=self._session.status,
        )

    def _collect_files(self) -> WorldFileSet:
        return WorldFileSet(
            server_properties_text=self.server_properties_text.get("1.0", "end-1c"),
            whitelist_json_text=self.whitelist_text.get("1.0", "end-1c"),
        )

    def _apply_detail(self, detail: WorldDetail, *, persisted: bool) -> None:
        self._session = EditorSession(
            manifest=detail.manifest,
            status=detail.status,
            persisted=persisted,
            original_server_properties_text=detail.files.server_properties_text,
            original_whitelist_json_text=detail.files.whitelist_json_text,
        )
        self._suspend_dirty_tracking = True
        try:
            self.display_name_var.set(detail.manifest.display_name)
            self._set_text(self.server_properties_text, detail.files.server_properties_text)
            self._set_text(self.whitelist_text, detail.files.whitelist_json_text)
            self.current_status_var.set(f"Status: {detail.status.label}")
            self.current_slug_var.set(f"Slug: {detail.manifest.slug}")
            self._update_dirty_label()
            self._update_button_states()
        finally:
            self._suspend_dirty_tracking = False

    def _clear_editor(self) -> None:
        self._session = None
        self._selected_slug = None
        self._suspend_dirty_tracking = True
        try:
            self.display_name_var.set("")
            self._set_text(self.server_properties_text, "")
            self._set_text(self.whitelist_text, "[]")
            self.current_status_var.set("Status: No world selected")
            self.current_slug_var.set("")
            self.dirty_var.set("Saved state loaded")
        finally:
            self._suspend_dirty_tracking = False
        self._update_button_states()

    def _render_worlds(self) -> None:
        self.world_listbox.delete(0, tk.END)
        for summary in self._world_summaries:
            self.world_listbox.insert(
                tk.END, f"{summary.manifest.display_name} [{summary.status.label}]"
            )

    def _select_slug(self, slug: str) -> None:
        for index, summary in enumerate(self._world_summaries):
            if summary.manifest.slug == slug:
                self.world_listbox.selection_clear(0, tk.END)
                self.world_listbox.selection_set(index)
                self.world_listbox.activate(index)
                self._selected_slug = slug
                return

    def _update_dirty_label(self) -> None:
        self.dirty_var.set("Unsaved changes" if self._is_dirty() else "Saved state loaded")
        self._update_button_states()

    def _is_dirty(self) -> bool:
        if self._session is None:
            return False

        return (
            self.display_name_var.get().strip() != self._session.manifest.display_name
            or self.server_properties_text.get("1.0", "end-1c")
            != self._session.original_server_properties_text
            or self.whitelist_text.get("1.0", "end-1c")
            != self._session.original_whitelist_json_text
        )

    def _update_button_states(self) -> None:
        has_session = self._session is not None
        create_enabled = bool(self.new_world_name_var.get().strip()) and not self._busy
        common_state = "disabled" if self._busy else "normal"
        self.refresh_button.configure(state=common_state)
        self.create_button.configure(state="normal" if create_enabled else "disabled")
        self.save_button.configure(state="normal" if has_session and not self._busy else "disabled")
        self.activate_button.configure(
            state="normal" if has_session and not self._busy else "disabled"
        )
        self.revert_button.configure(
            state="normal" if has_session and not self._busy else "disabled"
        )
        self.delete_button.configure(
            state="normal" if has_session and not self._busy else "disabled"
        )
        list_state = tk.DISABLED if self._busy else tk.NORMAL
        self.world_listbox.configure(state=list_state)
        entry_state = "disabled" if self._busy else "normal"
        self.display_name_entry.configure(state=entry_state)
        self.server_properties_text.configure(state=tk.DISABLED if self._busy else tk.NORMAL)
        self.whitelist_text.configure(state=tk.DISABLED if self._busy else tk.NORMAL)

    def _set_text(self, widget: ScrolledText, text: str) -> None:
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)
        widget.edit_modified(False)

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
                self._set_status(str(exc))
                messagebox.showerror("World Management", str(exc), parent=self.window)
                return
            on_success(result)

        self.window.after(75, poll)

    def _set_status(self, message: str) -> None:
        self.status_message_var.set(message)
