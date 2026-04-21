# Application Package

## Purpose
Defines the full Python app, including encrypted app-state startup, domain models, services, infrastructure, validation, and GUI.

## Contents
- `config/`: typed connection settings aliases.
- `domain/`: dataclasses and enums.
- `assets/`: packaged runtime assets such as the canonical Windows app icon.
- `services/`: business workflows.
- `infrastructure/`: provider API clients, encrypted app-state, remote paths, and SFTP-backed persistence.
- `validation/`: file validators.
- `gui/`: tkinter UI for the home screen, discovery/settings dialogs, world management, and RCON.
- `main.py`: package entrypoint.
- `installer_main.py`: Windows installer and updater helper entrypoint.

## Dependency Rules
- Cross-cutting behavior should be implemented once in the lowest sensible layer.

## Change Notes
- Expand by subsystem, not by dumping unrelated helpers into package root.
