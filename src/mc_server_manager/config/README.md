# Config

## Purpose
Owns runtime settings and `.env` loading.

## Contents
- `settings.py`: strongly typed SFTP, RCON, and app settings.
- `dotenv_loader.py`: default path resolution and `.env` parsing.

## Dependency Rules
- Keep runtime config loading free of GUI concerns.

## Change Notes
- Update this directory when required or optional env vars or lookup rules change.
