# Infrastructure

## Purpose
Contains provider API clients, encrypted local state storage, remote path rules, SFTP transport, and SFTP-backed persistence adapters.

## Contents
- `app_state_store.py`: encrypted local app-state and single-server export/import.
- `build_info.py`: runtime build metadata loading for packaged builds.
- `installations.py`: managed Windows install layout, install metadata, and shortcut creation.
- `provider_clients.py`: provider-agnostic client interfaces plus GameHostBros implementation.
- `releases.py`: public GitHub release API client and asset download support.
- `remote_paths.py`: remote file layout and path helpers.
- `sftp_gateway.py`: Paramiko session management and file primitives.
- `repositories.py`: world repository and live config store implementations.

## Dependency Rules
- Keep transport details here so the rest of the app talks in domain types.

## Change Notes
- Update this directory whenever the `.mc-manager` remote contract changes.
