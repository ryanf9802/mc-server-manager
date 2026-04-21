# GUI

## Purpose
Implements the tkinter desktop interface and keeps presentation state separate from service logic.

## Contents
- `main_window.py`: multi-server home screen with provider controls and panel launchers.
- `main_window.py` also owns app-level update prompts and updater handoff.
- `add_server_window.py`: provider discovery flow for onboarding a new server.
- `server_settings_window.py`: per-server provider, provider-specific SFTP, and RCON configuration editor.
- `world_management_window.py`: SFTP-backed world CRUD editor for a selected server.
- `console_window.py`: optional popup for RCON command execution.

## Dependency Rules
- The GUI talks to services only and should not know about Paramiko details.

## Change Notes
- Keep UI behavior thin; push reusable rules into services.
