from __future__ import annotations

import logging
import tkinter as tk
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from tkinter import filedialog, messagebox, ttk

from mc_server_manager.domain.models import (
    LocalModFile,
    LiveModFile,
    ManagedModFile,
    ModJarMetadata,
    ModJarStatus,
    ModListDetail,
    ModListManifest,
    ModListSaveRequest,
    ModListStatus,
    ModListSummary,
    StoredServerConfig,
)
from mc_server_manager.infrastructure.runtime_logging import log_background_exception
from mc_server_manager.services.mod_resolution import resolve_active_mods

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class EditableModEntry:
    filename: str
    size_bytes: int
    source_kind: str
    sha256: str | None = None
    local_path: str | None = None
    modified_time_epoch_seconds: int | None = None


@dataclass(slots=True)
class EditorSession:
    manifest: ModListManifest
    status: ModListStatus
    active_position: int | None
    persisted: bool
    original_display_name: str
    original_entries: tuple[EditableModEntry, ...]


class ModManagementWindow:
    def __init__(
        self,
        parent: tk.Misc,
        server: StoredServerConfig,
        mod_catalog_service,
        mod_editor_service,
        mod_activation_service,
    ) -> None:
        self._server = server
        self._mod_catalog_service = mod_catalog_service
        self._mod_editor_service = mod_editor_service
        self._mod_activation_service = mod_activation_service

        self._executor = ThreadPoolExecutor(max_workers=1)
        self._session: EditorSession | None = None
        self._mod_summaries: list[ModListSummary] = []
        self._selected_slug: str | None = None
        self._selected_jar_filename: str | None = None
        self._staged_active_slugs: list[str] = []
        self._applied_active_slugs: tuple[str, ...] = ()
        self._jar_entries: list[EditableModEntry] = []
        self._busy = False
        self._closed = False
        self._suspend_dirty_tracking = False

        self.window = tk.Toplevel(parent)
        self.window.title(f"Mod Management: {server.display_name}")
        self.window.geometry("1460x920")
        self.window.minsize(1220, 760)
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        self.new_list_name_var = tk.StringVar()
        self.display_name_var = tk.StringVar()
        self.current_status_var = tk.StringVar(value="Status: No mod list selected")
        self.current_slug_var = tk.StringVar(value="")
        self.dirty_var = tk.StringVar(value="Saved state loaded")
        self.active_dirty_var = tk.StringVar(value="Active order matches applied state")
        self.status_message_var = tk.StringVar(value="Create or load a mod list to begin.")

        self._build_layout()
        self._bind_events()
        self._update_button_states()
        self.refresh_mod_lists()

    def present(self) -> None:
        self.window.deiconify()
        self.window.lift()
        self.window.focus_force()

    def close(self) -> None:
        self._closed = True
        self._executor.shutdown(wait=False, cancel_futures=True)
        self.window.destroy()

    def _build_layout(self) -> None:
        self.window.columnconfigure(0, weight=4, minsize=420)
        self.window.columnconfigure(1, weight=6)
        self.window.rowconfigure(1, weight=1)

        sidebar = ttk.Frame(self.window, padding=16)
        sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        sidebar.columnconfigure(0, weight=1)
        sidebar.rowconfigure(3, weight=1)

        self.refresh_button = ttk.Button(sidebar, text="Refresh", command=self.refresh_mod_lists)
        self.refresh_button.grid(row=0, column=0, sticky="ew")

        create_frame = ttk.LabelFrame(sidebar, text="Create Mod List", padding=12)
        create_frame.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        create_frame.columnconfigure(0, weight=1)
        ttk.Entry(create_frame, textvariable=self.new_list_name_var).grid(
            row=0, column=0, sticky="ew"
        )
        self.snapshot_button = ttk.Button(
            create_frame,
            text="Save Current Live Mods As List",
            command=self.create_draft_from_live,
        )
        self.snapshot_button.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        self.create_local_button = ttk.Button(
            create_frame,
            text="Create List From Local Jars",
            command=self.create_draft_from_local,
        )
        self.create_local_button.grid(row=2, column=0, sticky="ew", pady=(8, 0))

        info_frame = ttk.LabelFrame(sidebar, text="Active Order", padding=12)
        info_frame.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        info_frame.columnconfigure(0, weight=1)
        ttk.Label(
            info_frame,
            text="Later active lists override earlier ones when jar filenames collide.",
            wraplength=330,
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(info_frame, textvariable=self.active_dirty_var).grid(
            row=1, column=0, sticky="w", pady=(8, 0)
        )

        overview_frame = ttk.LabelFrame(sidebar, text="Mod Lists", padding=12)
        overview_frame.grid(row=3, column=0, sticky="nsew", pady=(12, 0))
        overview_frame.columnconfigure(0, weight=1)
        overview_frame.rowconfigure(0, weight=1)

        self.mod_tree = ttk.Treeview(
            overview_frame,
            columns=("applied", "staged", "mods", "note"),
            show="tree headings",
            selectmode="browse",
        )
        self.mod_tree.heading("#0", text="Name")
        self.mod_tree.heading("applied", text="Applied Status")
        self.mod_tree.heading("staged", text="Staged")
        self.mod_tree.heading("mods", text="Mods")
        self.mod_tree.heading("note", text="Notes")
        self.mod_tree.column("#0", width=210, stretch=True)
        self.mod_tree.column("applied", width=120, stretch=False, anchor="w")
        self.mod_tree.column("staged", width=90, stretch=False, anchor="w")
        self.mod_tree.column("mods", width=110, stretch=False, anchor="w")
        self.mod_tree.column("note", width=240, stretch=True, anchor="w")
        self.mod_tree.grid(row=0, column=0, sticky="nsew")
        overview_scroll = ttk.Scrollbar(
            overview_frame,
            orient="vertical",
            command=self.mod_tree.yview,
        )
        overview_scroll.grid(row=0, column=1, sticky="ns")
        self.mod_tree.configure(yscrollcommand=overview_scroll.set)

        header = ttk.LabelFrame(self.window, text="Selected Mod List", padding=16)
        header.grid(row=0, column=1, sticky="nsew", padx=(0, 16), pady=(16, 0))
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="Display name").grid(row=0, column=0, sticky="w")
        self.display_name_entry = ttk.Entry(header, textvariable=self.display_name_var)
        self.display_name_entry.grid(row=1, column=0, sticky="ew", pady=(4, 12))

        actions = ttk.Frame(header)
        actions.grid(row=2, column=0, sticky="ew")
        for column in range(5):
            actions.columnconfigure(column, weight=1)

        self.save_button = ttk.Button(actions, text="Save", command=self.save_mod_list)
        self.save_button.grid(row=0, column=0, sticky="ew")
        self.revert_button = ttk.Button(actions, text="Revert", command=self.revert_mod_list)
        self.revert_button.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        self.add_jars_button = ttk.Button(
            actions, text="Add Local Jars", command=self.add_local_jars
        )
        self.add_jars_button.grid(row=0, column=2, sticky="ew", padx=(8, 0))
        self.remove_jar_button = ttk.Button(
            actions, text="Remove Selected Jar", command=self.remove_selected_jar
        )
        self.remove_jar_button.grid(row=0, column=3, sticky="ew", padx=(8, 0))
        self.delete_button = ttk.Button(actions, text="Delete", command=self.delete_mod_list)
        self.delete_button.grid(row=0, column=4, sticky="ew", padx=(8, 0))

        metadata = ttk.Frame(header)
        metadata.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        metadata.columnconfigure(0, weight=1)
        metadata.columnconfigure(1, weight=1)
        metadata.columnconfigure(2, weight=1)
        ttk.Label(metadata, textvariable=self.current_status_var).grid(row=0, column=0, sticky="w")
        ttk.Label(metadata, textvariable=self.current_slug_var).grid(row=0, column=1, sticky="w")
        ttk.Label(metadata, textvariable=self.dirty_var).grid(row=0, column=2, sticky="w")

        content = ttk.Frame(self.window, padding=(0, 16, 16, 0))
        content.grid(row=1, column=1, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=3)
        content.rowconfigure(1, weight=2)

        jars_frame = ttk.LabelFrame(content, text="Jars In Selected List", padding=12)
        jars_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        jars_frame.columnconfigure(0, weight=1)
        jars_frame.rowconfigure(0, weight=1)

        self.jar_tree = ttk.Treeview(
            jars_frame,
            columns=("size", "source"),
            show="headings",
            selectmode="browse",
        )
        self.jar_tree.heading("size", text="Size")
        self.jar_tree.heading("source", text="Source")
        self.jar_tree.column("size", width=120, stretch=False, anchor="w")
        self.jar_tree.column("source", width=140, stretch=True, anchor="w")
        self.jar_tree.grid(row=0, column=0, sticky="nsew")
        jar_scroll = ttk.Scrollbar(jars_frame, orient="vertical", command=self.jar_tree.yview)
        jar_scroll.grid(row=0, column=1, sticky="ns")
        self.jar_tree.configure(yscrollcommand=jar_scroll.set)

        active_frame = ttk.LabelFrame(content, text="Staged Active Mod Lists", padding=12)
        active_frame.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        active_frame.columnconfigure(0, weight=1)
        active_frame.rowconfigure(0, weight=1)

        self.active_listbox = tk.Listbox(active_frame, exportselection=False, activestyle="dotbox")
        self.active_listbox.grid(row=0, column=0, sticky="nsew")
        active_scroll = ttk.Scrollbar(
            active_frame,
            orient="vertical",
            command=self.active_listbox.yview,
        )
        active_scroll.grid(row=0, column=1, sticky="ns")
        self.active_listbox.configure(yscrollcommand=active_scroll.set)

        active_actions = ttk.Frame(active_frame)
        active_actions.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        for column in range(5):
            active_actions.columnconfigure(column, weight=1)

        self.add_active_button = ttk.Button(
            active_actions,
            text="Add Selected",
            command=self.add_selected_to_active,
        )
        self.add_active_button.grid(row=0, column=0, sticky="ew")
        self.remove_active_button = ttk.Button(
            active_actions,
            text="Remove",
            command=self.remove_selected_from_active,
        )
        self.remove_active_button.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        self.move_up_button = ttk.Button(
            active_actions,
            text="Move Up",
            command=lambda: self.move_active_selection(-1),
        )
        self.move_up_button.grid(row=0, column=2, sticky="ew", padx=(8, 0))
        self.move_down_button = ttk.Button(
            active_actions,
            text="Move Down",
            command=lambda: self.move_active_selection(1),
        )
        self.move_down_button.grid(row=0, column=3, sticky="ew", padx=(8, 0))
        self.apply_active_button = ttk.Button(
            active_actions,
            text="Apply Active Mod Lists",
            command=self.apply_active_mod_lists,
        )
        self.apply_active_button.grid(row=0, column=4, sticky="ew", padx=(8, 0))

        status_bar = ttk.Frame(self.window, padding=(16, 8))
        status_bar.grid(row=2, column=0, columnspan=2, sticky="ew")
        status_bar.columnconfigure(0, weight=1)
        ttk.Label(status_bar, textvariable=self.status_message_var, anchor="w").grid(
            row=0, column=0, sticky="ew"
        )

    def _bind_events(self) -> None:
        self.mod_tree.bind("<<TreeviewSelect>>", self._on_tree_selected)
        self.jar_tree.bind("<<TreeviewSelect>>", lambda *_: self._update_button_states())
        self.active_listbox.bind("<<ListboxSelect>>", lambda *_: self._update_button_states())
        self.new_list_name_var.trace_add("write", lambda *_: self._update_button_states())
        self.display_name_var.trace_add("write", lambda *_: self._on_editor_changed())

    def refresh_mod_lists(self) -> None:
        current_slug = (
            self._session.manifest.slug if self._session and self._session.persisted else None
        )

        def task():
            summaries = self._mod_catalog_service.get_mod_lists()
            detail = self._mod_catalog_service.get_mod_list(current_slug) if current_slug else None
            active_slugs = self._mod_catalog_service.get_active_slugs()
            return summaries, detail, active_slugs

        def on_success(result) -> None:
            summaries, detail, active_slugs = result
            self._mod_summaries = summaries
            self._applied_active_slugs = tuple(active_slugs)
            if not self._has_staged_active_changes():
                self._staged_active_slugs = list(active_slugs)
            else:
                self._staged_active_slugs = [
                    slug for slug in self._staged_active_slugs if self._has_summary(slug)
                ]
            self._render_active_listbox()
            self._render_mod_tree()
            if detail is not None:
                self._apply_detail(detail, persisted=True)
                self._select_tree_slug(detail.manifest.slug)
            elif current_slug is not None and self._session and self._session.persisted:
                self._clear_editor()
            self._update_active_dirty_label()
            self._set_status(
                "No managed mod lists found yet. Save the current live mods or create one from local jars."
                if not summaries
                else f"Loaded {len(summaries)} managed mod list(s)."
            )

        self._run_background(task, on_success, start_message="Refreshing remote mod lists...")

    def create_draft_from_live(self) -> None:
        display_name = self.new_list_name_var.get().strip()
        if not display_name:
            self._set_status("Enter a mod-list name before saving the current live mods.")
            return

        def task() -> tuple[ModListManifest, tuple[LiveModFile, ...]]:
            return self._mod_editor_service.create_draft_from_live(display_name)

        def on_success(result: tuple[ModListManifest, tuple[LiveModFile, ...]]) -> None:
            manifest, live_files = result
            self._apply_manifest_draft(manifest, (), live_files)
            self.new_list_name_var.set("")
            self._set_status(
                f"Drafted '{manifest.display_name}' from the current live remote mods folder."
            )

        self._run_background(
            task,
            on_success,
            start_message="Creating draft from live remote mods...",
        )

    def create_draft_from_local(self) -> None:
        display_name = self.new_list_name_var.get().strip()
        if not display_name:
            self._set_status("Enter a mod-list name before choosing local jar files.")
            return
        local_paths = filedialog.askopenfilenames(
            parent=self.window,
            title="Choose Local Mod Jars",
            filetypes=[("Jar files", "*.jar"), ("All files", "*.*")],
        )
        if not local_paths:
            return

        def task():
            manifest = self._mod_editor_service.create_empty_draft(display_name)
            local_files = self._mod_editor_service.describe_local_files(tuple(local_paths))
            return manifest, local_files

        def on_success(result) -> None:
            manifest, local_files = result
            self._apply_manifest_draft(manifest, local_files)
            self.new_list_name_var.set("")
            self._set_status(
                f"Drafted '{manifest.display_name}' from {len(local_files)} local jar file(s)."
            )

        self._run_background(
            task,
            on_success,
            start_message="Inspecting local jar files...",
        )

    def save_mod_list(self) -> None:
        request = self._collect_save_request()
        if request is None:
            return

        def task():
            saved = self._mod_editor_service.save_mod_list(request)
            summaries = self._mod_catalog_service.get_mod_lists()
            detail = self._mod_catalog_service.get_mod_list(saved.slug)
            active_slugs = self._mod_catalog_service.get_active_slugs()
            return summaries, detail, active_slugs

        def on_success(result) -> None:
            summaries, detail, active_slugs = result
            self._mod_summaries = summaries
            self._applied_active_slugs = tuple(active_slugs)
            self._staged_active_slugs = [
                slug for slug in self._staged_active_slugs if self._has_summary(slug)
            ]
            self._render_active_listbox()
            self._render_mod_tree()
            if detail is not None:
                self._apply_detail(detail, persisted=True)
                self._select_tree_slug(detail.manifest.slug)
                self._set_status(
                    f"Saved '{detail.manifest.display_name}' to the managed remote mod store."
                )
            self._update_active_dirty_label()

        self._run_background(task, on_success, start_message="Saving managed mod list to SFTP...")

    def revert_mod_list(self) -> None:
        if self._session is None:
            self._clear_editor()
            self._set_status("Draft cleared.")
            return

        if not self._session.persisted:
            self._clear_editor()
            self._set_status("Discarded the unsaved draft.")
            return

        slug = self._session.manifest.slug

        def task():
            return self._mod_catalog_service.get_mod_list(slug)

        def on_success(detail: ModListDetail | None) -> None:
            if detail is None:
                self._clear_editor()
                self._set_status(f"Mod list '{slug}' no longer exists on the remote host.")
                return
            self._apply_detail(detail, persisted=True)
            self._select_tree_slug(slug)
            self._set_status(
                f"Reloaded '{detail.manifest.display_name}' from the remote mod store."
            )

        self._run_background(task, on_success, start_message="Reloading mod list from SFTP...")

    def delete_mod_list(self) -> None:
        if self._session is None:
            return

        if not self._session.persisted:
            self._clear_editor()
            self._set_status("Discarded the unsaved draft.")
            return

        if not messagebox.askyesno(
            "Delete Mod List",
            f"Delete '{self._session.manifest.display_name}' from the managed remote store?",
            parent=self.window,
        ):
            return

        slug = self._session.manifest.slug

        def task():
            self._mod_editor_service.delete_mod_list(slug)
            summaries = self._mod_catalog_service.get_mod_lists()
            active_slugs = self._mod_catalog_service.get_active_slugs()
            return summaries, active_slugs

        def on_success(result) -> None:
            summaries, active_slugs = result
            self._mod_summaries = summaries
            self._applied_active_slugs = tuple(active_slugs)
            self._staged_active_slugs = [item for item in self._staged_active_slugs if item != slug]
            self._render_active_listbox()
            self._render_mod_tree()
            self._clear_editor()
            self._update_active_dirty_label()
            self._set_status("Deleted the selected managed mod list.")

        self._run_background(
            task, on_success, start_message="Deleting managed mod list from SFTP..."
        )

    def add_local_jars(self) -> None:
        if self._session is None:
            self._set_status("Load or create a mod list before adding local jar files.")
            return
        local_paths = filedialog.askopenfilenames(
            parent=self.window,
            title="Add Local Mod Jars",
            filetypes=[("Jar files", "*.jar"), ("All files", "*.*")],
        )
        if not local_paths:
            return

        def task() -> tuple[LocalModFile, ...]:
            return self._mod_editor_service.describe_local_files(tuple(local_paths))

        def on_success(local_files: tuple[LocalModFile, ...]) -> None:
            for file in local_files:
                self._upsert_entry(_local_entry_from_file(file))
            self._render_jar_tree()
            self._render_mod_tree()
            self._update_dirty_label()
            self._set_status(f"Added {len(local_files)} local jar file(s) to the current draft.")

        self._run_background(task, on_success, start_message="Inspecting local jar files...")

    def remove_selected_jar(self) -> None:
        if self._session is None:
            return
        selection = self.jar_tree.selection()
        if not selection:
            self._set_status("Select a jar in the selected mod list before removing it.")
            return
        target_filename = selection[0]
        self._jar_entries = [
            entry for entry in self._jar_entries if entry.filename != target_filename
        ]
        self._selected_jar_filename = None
        self._render_jar_tree()
        self._render_mod_tree()
        self._update_dirty_label()
        self._set_status(f"Removed '{target_filename}' from the current draft.")

    def add_selected_to_active(self) -> None:
        if self._session is None or not self._session.persisted:
            self._set_status("Save the current mod list before adding it to the active set.")
            return
        slug = self._session.manifest.slug
        if slug in self._staged_active_slugs:
            self._set_status(
                f"'{self._session.manifest.display_name}' is already in the staged active set."
            )
            return
        self._staged_active_slugs.append(slug)
        self._render_active_listbox()
        self._render_mod_tree()
        self._update_active_dirty_label()
        self._set_status(f"Added '{self._session.manifest.display_name}' to the staged active set.")

    def remove_selected_from_active(self) -> None:
        selection = self.active_listbox.curselection()
        if not selection:
            self._set_status("Select an active mod list before removing it.")
            return
        index = selection[0]
        removed_slug = self._staged_active_slugs.pop(index)
        self._render_active_listbox()
        self._render_mod_tree()
        self._update_active_dirty_label()
        self._set_status(
            f"Removed '{self._display_name_for_slug(removed_slug)}' from the staged active set."
        )

    def move_active_selection(self, delta: int) -> None:
        selection = self.active_listbox.curselection()
        if not selection:
            self._set_status("Select an active mod list before changing its order.")
            return
        current_index = selection[0]
        new_index = current_index + delta
        if not (0 <= new_index < len(self._staged_active_slugs)):
            return
        self._staged_active_slugs[current_index], self._staged_active_slugs[new_index] = (
            self._staged_active_slugs[new_index],
            self._staged_active_slugs[current_index],
        )
        self._render_active_listbox()
        self.active_listbox.selection_set(new_index)
        self.active_listbox.activate(new_index)
        self._render_mod_tree()
        self._update_active_dirty_label()
        self._set_status("Updated the staged active mod-list order.")

    def apply_active_mod_lists(self) -> None:
        staged = tuple(self._staged_active_slugs)

        def task():
            self._mod_activation_service.apply_active_mod_lists(staged)
            summaries = self._mod_catalog_service.get_mod_lists()
            detail = (
                self._mod_catalog_service.get_mod_list(self._session.manifest.slug)
                if self._session and self._session.persisted
                else None
            )
            active_slugs = self._mod_catalog_service.get_active_slugs()
            return summaries, detail, active_slugs

        def on_success(result) -> None:
            summaries, detail, active_slugs = result
            self._mod_summaries = summaries
            self._applied_active_slugs = tuple(active_slugs)
            self._staged_active_slugs = list(active_slugs)
            self._render_active_listbox()
            self._render_mod_tree()
            if detail is not None:
                self._apply_detail(detail, persisted=True)
                self._select_tree_slug(detail.manifest.slug)
            self._update_active_dirty_label()
            self._set_status("Applied the staged active mod lists to the live remote mods folder.")

        self._run_background(
            task,
            on_success,
            start_message="Applying staged mod lists to the live remote mods folder...",
        )

    def _on_tree_selected(self, _event: tk.Event) -> None:
        selection = self.mod_tree.selection()
        if not selection:
            return
        item_id = selection[0]
        slug, jar_filename = _tree_item_to_selection(item_id)
        if slug == self._selected_slug and jar_filename is None:
            return

        def task():
            return self._mod_catalog_service.get_mod_list(slug)

        def on_success(detail: ModListDetail | None) -> None:
            if detail is None:
                self._set_status(f"Mod list '{slug}' no longer exists on the remote host.")
                self.refresh_mod_lists()
                return
            self._selected_slug = slug
            self._apply_detail(detail, persisted=True)
            self._select_tree_slug(slug, jar_filename=jar_filename)
            if jar_filename is not None:
                self._select_jar_filename(jar_filename)
            self._set_status(f"Loaded '{detail.manifest.display_name}' from the remote mod store.")

        self._run_background(task, on_success, start_message="Loading mod list from SFTP...")

    def _apply_manifest_draft(
        self,
        manifest: ModListManifest,
        local_files: tuple[LocalModFile, ...],
        live_files: tuple[LiveModFile, ...] = (),
    ) -> None:
        entries = [_managed_entry_from_metadata(item) for item in manifest.jars]
        entries.extend(_live_entry_from_file(item) for item in live_files)
        entries.extend(_local_entry_from_file(item) for item in local_files)
        self._apply_session(
            manifest=manifest,
            status=ModListStatus.INACTIVE,
            active_position=None,
            persisted=False,
            entries=entries,
        )

    def _apply_detail(self, detail: ModListDetail, *, persisted: bool) -> None:
        entries = [_managed_entry_from_metadata(item.metadata) for item in detail.jars]
        self._apply_session(
            manifest=detail.manifest,
            status=detail.status,
            active_position=detail.active_position,
            persisted=persisted,
            entries=entries,
        )

    def _apply_session(
        self,
        *,
        manifest: ModListManifest,
        status: ModListStatus,
        active_position: int | None,
        persisted: bool,
        entries: list[EditableModEntry],
    ) -> None:
        sorted_entries = sorted(entries, key=lambda item: item.filename.lower())
        self._session = EditorSession(
            manifest=manifest,
            status=status,
            active_position=active_position,
            persisted=persisted,
            original_display_name=manifest.display_name,
            original_entries=tuple(sorted_entries),
        )
        self._jar_entries = list(sorted_entries)
        self._selected_slug = manifest.slug if persisted else None
        self._selected_jar_filename = None
        self._suspend_dirty_tracking = True
        try:
            self.display_name_var.set(manifest.display_name)
            self.current_status_var.set(f"Status: {status.label}")
            self.current_slug_var.set(f"Slug: {manifest.slug}")
            self._render_jar_tree()
            self._update_dirty_label()
        finally:
            self._suspend_dirty_tracking = False
        self._update_button_states()

    def _clear_editor(self) -> None:
        self._session = None
        self._jar_entries = []
        self._selected_slug = None
        self._selected_jar_filename = None
        self._suspend_dirty_tracking = True
        try:
            self.display_name_var.set("")
            self.current_status_var.set("Status: No mod list selected")
            self.current_slug_var.set("")
            self.dirty_var.set("Saved state loaded")
            self.jar_tree.delete(*self.jar_tree.get_children())
        finally:
            self._suspend_dirty_tracking = False
        self._update_button_states()

    def _render_mod_tree(self) -> None:
        selected = self.mod_tree.selection()
        expanded = {
            item for item in self.mod_tree.get_children("") if self.mod_tree.item(item, "open")
        }
        self.mod_tree.delete(*self.mod_tree.get_children())

        manifests_by_slug = {
            summary.manifest.slug: summary.manifest for summary in self._mod_summaries
        }
        resolved = resolve_active_mods(manifests_by_slug, tuple(self._staged_active_slugs))

        for summary in self._mod_summaries:
            slug = summary.manifest.slug
            staged_text = ""
            if slug in self._staged_active_slugs:
                staged_text = f"Staged #{self._staged_active_slugs.index(slug) + 1}"
            note = ""
            if slug in self._staged_active_slugs and summary.overridden_count:
                note = f"{summary.overridden_count} mod(s) overridden by later active lists"
            item_id = self.mod_tree.insert(
                "",
                "end",
                iid=slug,
                text=summary.manifest.display_name,
                values=(
                    summary.status.label,
                    staged_text,
                    f"{summary.included_count}/{len(summary.manifest.jars)} included",
                    note,
                ),
                open=slug in expanded or slug == self._selected_slug,
            )
            jar_views = resolved.jar_views_by_slug.get(slug, ())
            view_by_name = {item.metadata.filename: item for item in jar_views}
            for jar in summary.manifest.jars:
                jar_view = view_by_name.get(jar.filename)
                note_text = ""
                staged_value = ""
                if jar_view is not None:
                    staged_value = jar_view.status.label
                    if (
                        jar_view.status is ModJarStatus.OVERRIDDEN
                        and jar_view.overridden_by_display_name
                    ):
                        note_text = f"Overridden by {jar_view.overridden_by_display_name}"
                self.mod_tree.insert(
                    item_id,
                    "end",
                    iid=_tree_child_id(slug, jar.filename),
                    text=jar.filename,
                    values=(
                        "",
                        staged_value,
                        _format_size(jar.size_bytes),
                        note_text,
                    ),
                )

        if selected:
            for item_id in selected:
                if self.mod_tree.exists(item_id):
                    self.mod_tree.selection_set(item_id)
                    break

    def _render_jar_tree(self) -> None:
        selected = self.jar_tree.selection()
        self.jar_tree.delete(*self.jar_tree.get_children())
        for entry in sorted(self._jar_entries, key=lambda item: item.filename.lower()):
            if entry.source_kind == "managed":
                source_label = "Managed remote copy"
            elif entry.source_kind == "live":
                source_label = "Live remote copy"
            else:
                source_label = "Local upload"
            self.jar_tree.insert(
                "",
                "end",
                iid=entry.filename,
                values=(_format_size(entry.size_bytes), source_label),
                text=entry.filename,
            )
        if self._selected_jar_filename and self.jar_tree.exists(self._selected_jar_filename):
            self.jar_tree.selection_set(self._selected_jar_filename)
            self.jar_tree.focus(self._selected_jar_filename)
        elif selected:
            for item_id in selected:
                if self.jar_tree.exists(item_id):
                    self.jar_tree.selection_set(item_id)
                    self.jar_tree.focus(item_id)
                    break
        self._update_button_states()

    def _render_active_listbox(self) -> None:
        current_selection = self.active_listbox.curselection()
        self.active_listbox.delete(0, tk.END)
        for index, slug in enumerate(self._staged_active_slugs, start=1):
            self.active_listbox.insert(tk.END, f"{index}. {self._display_name_for_slug(slug)}")
        if current_selection:
            index = min(current_selection[0], len(self._staged_active_slugs) - 1)
            if index >= 0:
                self.active_listbox.selection_set(index)
                self.active_listbox.activate(index)
        self._update_button_states()

    def _collect_save_request(self) -> ModListSaveRequest | None:
        if self._session is None:
            self._set_status("No mod list is currently selected.")
            return None
        display_name = self.display_name_var.get().strip()
        managed_files = []
        live_files = []
        local_files = []
        for entry in self._jar_entries:
            if entry.source_kind == "managed" and entry.sha256 is not None:
                managed_files.append(ManagedModFile(filename=entry.filename, sha256=entry.sha256))
            elif entry.source_kind == "live" and entry.modified_time_epoch_seconds is not None:
                live_files.append(
                    LiveModFile(
                        filename=entry.filename,
                        size_bytes=entry.size_bytes,
                        modified_time_epoch_seconds=entry.modified_time_epoch_seconds,
                    )
                )
            elif entry.source_kind == "local" and entry.local_path is not None:
                local_files.append(
                    LocalModFile(
                        filename=entry.filename,
                        local_path=entry.local_path,
                        size_bytes=entry.size_bytes,
                    )
                )

        return ModListSaveRequest(
            slug=self._session.manifest.slug,
            display_name=display_name,
            created_at_utc=self._session.manifest.created_at_utc,
            managed_files=tuple(sorted(managed_files, key=lambda item: item.filename.lower())),
            live_files=tuple(sorted(live_files, key=lambda item: item.filename.lower())),
            local_files=tuple(sorted(local_files, key=lambda item: item.filename.lower())),
        )

    def _on_editor_changed(self) -> None:
        if self._suspend_dirty_tracking:
            return
        self._update_dirty_label()

    def _update_dirty_label(self) -> None:
        self.dirty_var.set("Unsaved changes" if self._is_dirty() else "Saved state loaded")
        self._update_button_states()

    def _update_active_dirty_label(self) -> None:
        if tuple(self._staged_active_slugs) == self._applied_active_slugs:
            self.active_dirty_var.set("Active order matches applied state")
        else:
            self.active_dirty_var.set("Active order has unapplied changes")
        self._update_button_states()

    def _is_dirty(self) -> bool:
        if self._session is None:
            return False
        return (
            self.display_name_var.get().strip() != self._session.original_display_name
            or tuple(sorted(self._jar_entries, key=lambda item: item.filename.lower()))
            != self._session.original_entries
        )

    def _has_staged_active_changes(self) -> bool:
        return (
            bool(self._staged_active_slugs)
            and tuple(self._staged_active_slugs) != self._applied_active_slugs
        )

    def _update_button_states(self) -> None:
        has_session = self._session is not None
        can_create = bool(self.new_list_name_var.get().strip()) and not self._busy
        common_state = "disabled" if self._busy else "normal"
        self.refresh_button.configure(state=common_state)
        self.snapshot_button.configure(state="normal" if can_create else "disabled")
        self.create_local_button.configure(state="normal" if can_create else "disabled")
        self.save_button.configure(state="normal" if has_session and not self._busy else "disabled")
        self.revert_button.configure(
            state="normal" if has_session and not self._busy else "disabled"
        )
        self.add_jars_button.configure(
            state="normal" if has_session and not self._busy else "disabled"
        )
        jar_selected = bool(self.jar_tree.selection())
        self.remove_jar_button.configure(
            state="normal" if has_session and jar_selected and not self._busy else "disabled"
        )
        self.delete_button.configure(
            state="normal" if has_session and not self._busy else "disabled"
        )
        can_add_active = (
            has_session
            and self._session is not None
            and self._session.persisted
            and self._session.manifest.slug not in self._staged_active_slugs
            and not self._busy
        )
        self.add_active_button.configure(state="normal" if can_add_active else "disabled")
        active_selected = bool(self.active_listbox.curselection())
        self.remove_active_button.configure(
            state="normal" if active_selected and not self._busy else "disabled"
        )
        self.move_up_button.configure(
            state="normal"
            if active_selected and self.active_listbox.curselection()[0] > 0 and not self._busy
            else "disabled"
        )
        self.move_down_button.configure(
            state="normal"
            if active_selected
            and self.active_listbox.curselection()[0] < len(self._staged_active_slugs) - 1
            and not self._busy
            else "disabled"
        )
        self.apply_active_button.configure(
            state="normal"
            if tuple(self._staged_active_slugs) != self._applied_active_slugs and not self._busy
            else "disabled"
        )
        self.mod_tree.configure(selectmode="browse")
        self.jar_tree.configure(selectmode="browse")
        self.active_listbox.configure(state=tk.DISABLED if self._busy else tk.NORMAL)
        self.display_name_entry.configure(state=common_state if has_session else "disabled")

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
                log_background_exception(
                    logger,
                    (
                        f"{start_message} server={self._server.display_name} "
                        f"selected_slug={self._selected_slug or '<none>'}"
                    ),
                    exc,
                )
                self._set_status(str(exc))
                messagebox.showerror("Mod Management", str(exc), parent=self.window)
                return
            on_success(result)

        self.window.after(75, poll)

    def _set_status(self, message: str) -> None:
        self.status_message_var.set(message)

    def _upsert_entry(self, entry: EditableModEntry) -> None:
        self._jar_entries = [item for item in self._jar_entries if item.filename != entry.filename]
        self._jar_entries.append(entry)
        self._jar_entries.sort(key=lambda item: item.filename.lower())

    def _select_tree_slug(self, slug: str, *, jar_filename: str | None = None) -> None:
        item_id = _tree_child_id(slug, jar_filename) if jar_filename else slug
        if self.mod_tree.exists(item_id):
            self.mod_tree.selection_set(item_id)
            self.mod_tree.focus(item_id)
            self.mod_tree.see(item_id)
            self._selected_slug = slug

    def _select_jar_filename(self, filename: str) -> None:
        self._selected_jar_filename = filename
        if self.jar_tree.exists(filename):
            self.jar_tree.selection_set(filename)
            self.jar_tree.focus(filename)
            self.jar_tree.see(filename)

    def _display_name_for_slug(self, slug: str) -> str:
        summary = next((item for item in self._mod_summaries if item.manifest.slug == slug), None)
        return summary.manifest.display_name if summary is not None else slug

    def _has_summary(self, slug: str) -> bool:
        return any(summary.manifest.slug == slug for summary in self._mod_summaries)


def _managed_entry_from_metadata(metadata: ModJarMetadata) -> EditableModEntry:
    return EditableModEntry(
        filename=metadata.filename,
        size_bytes=metadata.size_bytes,
        source_kind="managed",
        sha256=metadata.sha256,
    )


def _live_entry_from_file(live_file: LiveModFile) -> EditableModEntry:
    return EditableModEntry(
        filename=live_file.filename,
        size_bytes=live_file.size_bytes,
        source_kind="live",
        modified_time_epoch_seconds=live_file.modified_time_epoch_seconds,
    )


def _local_entry_from_file(local_file: LocalModFile) -> EditableModEntry:
    return EditableModEntry(
        filename=local_file.filename,
        size_bytes=local_file.size_bytes,
        source_kind="local",
        local_path=local_file.local_path,
    )


def _format_size(size_bytes: int) -> str:
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MiB"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KiB"
    return f"{size_bytes} B"


def _tree_child_id(slug: str, jar_filename: str | None) -> str:
    if jar_filename is None:
        return slug
    return f"{slug}::{jar_filename}"


def _tree_item_to_selection(item_id: str) -> tuple[str, str | None]:
    if "::" not in item_id:
        return item_id, None
    slug, jar_filename = item_id.split("::", 1)
    return slug, jar_filename
