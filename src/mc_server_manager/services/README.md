# Services

## Purpose
Contains business workflows for encrypted app-state, world and mod-list management, hashing, and RCON.

## Contents
- `app_state.py`: in-memory encrypted app-state workflow and server uniqueness rules.
- `server_runtime.py`: builds provider, SFTP, and RCON service stacks for a selected server.
- `sftp_connection_address.py`: GameHostBros SFTP connection-address parsing and normalization.
- `updates.py`: managed-install update checks and updater handoff.
- `world_name.py`: immutable slug generation.
- `hashing.py`: content hashing.
- `world_catalog.py`: list/load and status reconciliation.
- `world_editor.py`: create/save/delete logic.
- `activation.py`: live apply workflow.
- `mod_catalog.py`: mod-list summary/detail loading and applied-state reconciliation.
- `mod_editor.py`: create/save/delete logic for managed mod lists.
- `mod_activation.py`: staged active-mod-list apply workflow.
- `mod_resolution.py`: filename-conflict resolution for ordered active mod lists.
- `rcon.py`: optional RCON connect and command execution.

## Dependency Rules
- Services may depend on domain, validation, and infrastructure-facing repositories.

## Change Notes
- Keep CRUD, activation, and saved-server rules centralized here instead of scattering them across the GUI.
