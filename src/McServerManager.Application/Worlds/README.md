# World Workflows

## Purpose
Defines CRUD contracts and orchestration for managed world configurations.

## Contents
- Repository contracts for managed world storage and live config access.
- Catalog and editor services for list, load, create, save, and delete.
- `WorldNameGenerator.cs` for immutable slug creation.

## Dependency Rules
- Keep remote storage behind interfaces.
- Use services here instead of duplicating rules in the UI.

## Change Notes
- Update this directory when world status or persistence rules change.

