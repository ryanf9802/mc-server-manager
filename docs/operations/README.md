# Operations Docs

## Purpose
Captures runtime setup and support guidance for running the Windows app against an SFTP host.

## Contents
- Required `.env` keys.
- Expected remote folder layout under `${SFTP_SERVER_ROOT}`.
- README verification workflow via `tools/verify-directory-readmes`.
- Windows build expectation: use Visual Studio 2022 or a Windows .NET 8 SDK install with WinUI tooling.

## Runtime Setup
- Copy `.env.example` to `.env` beside the built executable.
- Fill in the SFTP host, port, username, password, and remote server root provided by GameHostBros.
- Managed worlds are stored remotely under `${SFTP_SERVER_ROOT}/.mc-manager/worlds/<slug>/`.
- Live files remain `${SFTP_SERVER_ROOT}/server.properties` and `${SFTP_SERVER_ROOT}/whitelist.json`.

## Dependency Rules
- Keep environment key names aligned with `SftpSettings`.

## Change Notes
- Update when env vars, packaging steps, or operational constraints change.
