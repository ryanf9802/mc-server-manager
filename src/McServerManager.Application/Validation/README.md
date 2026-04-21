# Validation

## Purpose
Keeps config-file validation rules explicit, testable, and reusable across UI and services.

## Contents
- `IServerPropertiesValidator.cs`: contract for text validation.
- `IWhitelistValidator.cs`: contract for whitelist validation.
- `ServerPropertiesValidator.cs`: line-based parser checks.
- `WhitelistValidator.cs`: JSON shape checks.

## Dependency Rules
- Validation stays pure and side-effect free.

## Change Notes
- Update these validators before adding UI-specific input restrictions.

