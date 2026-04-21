# Packaging Tools

## Purpose

Contains Windows packaging assets for producing release artifacts used by the installer and in-app updater.

## Contents

- `build_windows_release.py`: Windows-only wrapper that builds the app exe, installer exe, release bundle zip, and checksums.

## Dependency Rules

- Keep packaging behavior isolated from the runtime app so source-run development stays simple.
- Prefer one stable build entrypoint over ad hoc shell commands.

## Change Notes

- Update this README when the build output path, build command, or packaging layout changes.
