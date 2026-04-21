# mc-server-manager

Cross-platform Python desktop app for managing multiple hosted Minecraft servers from one encrypted local library. The home screen handles provider-backed power controls and opens server-specific panels for SFTP world management and RCON commands.

## Root Contents

- `docs/`: product and operational documentation.
- `src/`: the Python application package.
- `tests/`: unit and opt-in integration coverage.
- `tools/`: repository maintenance utilities.
- `pyproject.toml`: `uv`-managed project metadata and entrypoint definition.

## Quick Start

1. Install `uv` and Python 3.12+.
2. Run `uv sync`.
3. Start the GUI with `uv run mc-server-manager`.
4. On first launch, create an application password to encrypt the local server library.
5. Add a server from the home screen, choose `GameHostBros`, discover the provider server, then save SFTP and optional RCON settings in the server settings window.
6. The GameHostBros panel URL is fixed in the app as `https://panel.gamehostbros.com`; you only provide the API token and server details.
7. For GameHostBros SFTP, enter one `Connection Address` such as `sftp://9950ece8c16c6dbc.daemon.panel.gg:2022`; the app parses host and port automatically and uses `/` as the fixed root.

## Runtime Model

- The app no longer reads runtime configuration from `.env`.
- Each saved server entry persists inside an encrypted local app-state file protected by the application password.
- Export/import writes a single encrypted server configuration file per server.
- RCON is optional per saved server. When absent, the RCON panel stays disabled for that server.

## Dev Commands

- Format: `uv run ruff format .`
- Type-check: `uv run ty check`
- Test: `uv run pytest`
- Start in the background: `make up`
- Stop the background app: `make down`
- Check runtime status: `make status`
- Tail recent logs: `make logs`

## Dependency Rules

- Business rules belong in `services/` and `validation/`, not directly in the GUI.
- Provider API, encrypted app-state, and remote transport logic belong in `infrastructure/`.
- Every committed directory must contain a `README.md`.

## Change Notes

- Update the nearest directory `README.md` whenever you add, remove, or repurpose files.
