# Unit Tests

## Purpose
Covers deterministic logic for encrypted state, provider adapters, naming, validation, paths, and world-status reconciliation.

## Contents
- `test_app_state_store.py`
- `test_provider_clients.py`
- `test_sftp_connection_address.py`
- `test_world_name.py`
- `test_validators.py`
- `test_remote_paths.py`
- `test_world_catalog.py`
- `test_rcon_service.py`

## Dependency Rules
- Use simple fakes instead of real SFTP sessions.

## Change Notes
- Prefer adding pure logic coverage here before writing integration tests.
