# mc-server-manager

Cross-platform Python desktop app for managing remote Minecraft `server.properties` and `whitelist.json` files over SFTP. Each managed "world" lives on the remote host under a dedicated `.mc-manager` directory, and activating a world replaces the live config pair in the server root.

## Root Contents

- `docs/`: product and operational documentation.
- `src/`: the Python application package.
- `tests/`: unit and opt-in integration coverage.
- `tools/`: repository maintenance utilities.
- `pyproject.toml`: `uv`-managed project metadata and entrypoint definition.
- `.env.example`: runtime SFTP configuration template.

## Quick Start

1. Install `uv` and Python 3.12+.
2. Copy `.env.example` to `.env` and fill in your SFTP settings.
3. Run `uv sync`.
4. Start the GUI with `uv run mc-server-manager`.

## Optional RCON

- Add `RCON_HOST`, `RCON_PORT`, and `RCON_PASSWORD` to `.env` to enable console command execution.
- RCON is optional. The app still starts for SFTP world management when those vars are absent.
- The console UI uses request/response RCON commands; it does not stream the full live server console.

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
- Remote layout and transport logic belong in `infrastructure/`.
- Every committed directory must contain a `README.md`.

## Change Notes

- Update the nearest directory `README.md` whenever you add, remove, or repurpose files.
