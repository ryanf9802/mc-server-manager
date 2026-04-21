# Unit Tests

## Purpose
Covers deterministic logic for naming, validation, env loading, paths, and world-status reconciliation.

## Contents
- `test_world_name.py`
- `test_validators.py`
- `test_dotenv_loader.py`
- `test_remote_paths.py`
- `test_world_catalog.py`
- `test_rcon_service.py`

## Dependency Rules
- Use simple fakes instead of real SFTP sessions.

## Change Notes
- Prefer adding pure logic coverage here before writing integration tests.
