# Domain

## Purpose
Owns framework-free business types used by the rest of the solution.

## Contents
- `Models/`: world, file, and activation records.
- `ValueObjects/`: statuses and validation output.
- `McServerManager.Domain.csproj`: domain project definition.

## Dependency Rules
- No infrastructure or UI references.
- Keep types immutable where practical.

## Change Notes
- Expand this layer only for reusable domain concepts, not application workflows.

