# Operations Docs

## Purpose

Documents runtime setup for running the app locally with `uv`.

## Contents

- The encrypted local app-state workflow.
- The remote layout under `${SFTP_SERVER_ROOT}/.mc-manager`.
- Local run commands with `uv`.
- Provider, SFTP, and optional RCON setup per saved server.

## Runtime Setup

- Install dependencies with `uv sync`.
- Start the app with `uv run mc-server-manager`.
- On first launch, create an application password.
- Use `Add` on the home screen to connect to the provider API, discover a server, and then save provider, SFTP, and optional RCON settings in the server settings window.
- For `GameHostBros`, the panel base URL is hard-coded to `https://panel.gamehostbros.com`; users do not enter it manually.
- For `GameHostBros` SFTP, the settings window accepts `Connection Address`, `Username`, and `Password`. The app accepts either `sftp://host:port` or `host:port` and always saves `/` as the root.
- Saved server configurations persist in an encrypted local state file under the platform app-data directory.

## Windows Packaging

- Install packaging dependencies on Windows with `uv sync --dev`.
- Build the single-file executable with `uv run python tools/packaging/build_windows_single_exe.py`.
- The build output is `dist/windows-single/mc-server-manager.exe`.
- The same build can be launched through `make package-windows-single` where `make` is available.
- PyInstaller builds are platform-specific, so create the Windows `.exe` on Windows rather than WSL/Linux.

## RCON Notes

- RCON is optional and does not block the app from starting.
- The console popup is enabled only for saved servers that include host, port, and password.
- The app sends request/response RCON commands; it does not stream the live server console.

## Provider API Notes

- GameHostBros uses bearer-token auth with `Accept: application/vnd.wisp.v1+json`.
- The app uses the fixed GameHostBros panel base URL `https://panel.gamehostbros.com`.
- The home screen uses the provider API for discovery, manual refresh, and power actions.
- World management remains SFTP-based and does not use the provider file-manager endpoints.

## Make Targets

- `make up` starts the GUI app in the background with `uv run python -m mc_server_manager.main`.
- `make down` stops the background process recorded in `.run/mc-server-manager.pid`.
- `make status` reports whether the managed background process is currently running.
- `make logs` tails `.run/mc-server-manager.log` for recent startup or runtime output.

## Development Checks

- Format the repo with `uv run ruff format .`.
- Run static checks with `uv run ty check`.
- Run tests with `uv run pytest`.

## Dependency Rules

- Keep startup and storage docs aligned with `src/mc_server_manager/main.py` and `src/mc_server_manager/infrastructure/app_state_store.py`.

## Change Notes

- Update this file when startup behavior or runtime configuration changes.
