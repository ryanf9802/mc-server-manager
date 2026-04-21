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

## Development Checks

- Format the repo with `uv run ruff format .`.
- Run static checks with `uv run ty check`.
- Run tests with `uv run pytest`.

## Dependency Rules

- Keep environment key names aligned with `src/mc_server_manager/config/settings.py`.

## Change Notes

- Update this file when startup behavior or runtime configuration changes.
