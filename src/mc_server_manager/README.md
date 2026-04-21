# Application Package

## Purpose
Defines the full Python app, including configuration loading, domain models, services, infrastructure, validation, and GUI.

## Contents
- `config/`: settings and `.env` loading.
- `domain/`: dataclasses and enums.
- `services/`: business workflows.
- `infrastructure/`: remote paths and SFTP-backed persistence.
- `validation/`: file validators.
- `gui/`: tkinter UI.
- `main.py`: package entrypoint.

## Dependency Rules
- Cross-cutting behavior should be implemented once in the lowest sensible layer.

## Change Notes
- Expand by subsystem, not by dumping unrelated helpers into package root.

