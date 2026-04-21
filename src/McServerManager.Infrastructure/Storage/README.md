# Storage Infrastructure

## Purpose
Maps application storage contracts onto the remote SFTP directory layout.

## Contents
- `RemotePathBuilder.cs`: centralized remote path construction.
- `SftpWorldRepository.cs`: managed world manifests and files.
- `SftpLiveConfigurationStore.cs`: live root files and active pointer.

## Dependency Rules
- All remote path rules and serialization details live here.

## Change Notes
- Update together when the remote layout under `.mc-manager` changes.

