# Services

## Purpose
Contains business workflows for world naming, listing, editing, activation, hashing, and RCON.

## Contents
- `world_name.py`: immutable slug generation.
- `hashing.py`: content hashing.
- `world_catalog.py`: list/load and status reconciliation.
- `world_editor.py`: create/save/delete logic.
- `activation.py`: live apply workflow.
- `rcon.py`: optional RCON connect and command execution.

## Dependency Rules
- Services may depend on domain, validation, and infrastructure-facing repositories.

## Change Notes
- Keep CRUD and activation rules centralized here instead of scattering them across the GUI.
