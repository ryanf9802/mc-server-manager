# McServerManager

Windows desktop app for managing remote Minecraft server configurations over SFTP. The tool keeps each managed world's `server.properties` and `whitelist.json` on the remote host, then swaps the live files in place when a world is activated.

## Root Contents

- `docs/`: product notes and operating guidance.
- `src/`: application source split by layer and feature.
- `tests/`: unit and integration coverage.
- `tools/`: repo maintenance scripts, including README enforcement.
- `.env.example`: runtime SFTP configuration template.
- `McServerManager.sln`: solution entry point for Visual Studio and `dotnet`.

## Dependency Rules

- UI code lives only in `src/McServerManager.Desktop`.
- Application orchestration lives in `src/McServerManager.Application`.
- Domain types stay framework-free in `src/McServerManager.Domain`.
- Remote I/O and hashing adapters live in `src/McServerManager.Infrastructure`.

## Change Notes

- Every committed directory contains a `README.md`.
- Any structural change must update the nearest directory README in the same edit.
