# Operations Docs

## Purpose

Documents runtime setup for running the app locally with `uv`.

## Contents

- Required `.env` keys.
- The remote layout under `${SFTP_SERVER_ROOT}/.mc-manager`.
- Local run commands with `uv`.

## Runtime Setup

- Copy `.env.example` to `.env`.
- Set `SFTP_HOST`, `SFTP_PORT`, `SFTP_USERNAME`, `SFTP_PASSWORD`, and `SFTP_SERVER_ROOT`.
- Install dependencies with `uv sync`.
- Start the app with `uv run mc-server-manager`.

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

- Keep environment key names aligned with `src/mc_server_manager/config/settings.py`.

## Change Notes

- Update this file when startup behavior or runtime configuration changes.
