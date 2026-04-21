# Domain Models

## Purpose
Defines the immutable records that represent managed world state and remote file payloads.

## Contents
- `WorldManifest.cs`: persisted metadata for a managed world.
- `ActiveWorldRecord.cs`: active pointer plus live-file hashes.
- `WorldFileSet.cs`: raw file contents for a world.
- `WorldDetail.cs`: manifest plus files plus status.
- `WorldSummary.cs`: list-friendly world projection.

## Dependency Rules
- Models may depend on domain value objects only.

## Change Notes
- Keep file payload models text-first to preserve raw remote content.

