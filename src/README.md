# Source

## Purpose

Contains the production code split by architectural responsibility.

## Contents

- `McServerManager.Desktop/`: WinUI shell and feature-facing UI.
- `McServerManager.Application/`: use-case orchestration and interfaces.
- `McServerManager.Domain/`: pure domain models and value objects.
- `McServerManager.Infrastructure/`: SFTP, env loading, and hashing adapters.

## Dependency Rules

- Dependencies flow inward: Desktop -> Application -> Domain.
- Infrastructure implements Application-facing interfaces and references Domain as needed.

## Change Notes

- Preserve single responsibility across projects and avoid pushing UI concerns into services.
