# GUI

## Purpose
Implements the tkinter desktop interface and keeps presentation state separate from service logic.

## Contents
- `main_window.py`: world list, editors, commands, and background task handling.
- `console_window.py`: optional popup for RCON command execution.

## Dependency Rules
- The GUI talks to services only and should not know about Paramiko details.

## Change Notes
- Keep UI behavior thin; push reusable rules into services.
