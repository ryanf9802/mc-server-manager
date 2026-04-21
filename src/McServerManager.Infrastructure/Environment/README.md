# Environment Infrastructure

## Purpose
Loads runtime SFTP settings from a local `.env` file without storing secrets in source control.

## Contents
- `DotEnvLoader.cs`: key-value parser with required-variable checks.

## Dependency Rules
- Keep parsing deterministic and startup-focused.

## Change Notes
- Update alongside `SftpSettings` when required keys change.

