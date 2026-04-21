# Infrastructure

## Purpose
Contains the remote path rules, SFTP transport, and SFTP-backed persistence adapters.

## Contents
- `remote_paths.py`: remote file layout and path helpers.
- `sftp_gateway.py`: Paramiko session management and file primitives.
- `repositories.py`: world repository and live config store implementations.

## Dependency Rules
- Keep transport details here so the rest of the app talks in domain types.

## Change Notes
- Update this directory whenever the `.mc-manager` remote contract changes.

