# Packaging Tools

## Purpose

Contains Windows packaging assets for producing a single-file desktop executable with PyInstaller.

## Contents

- `build_windows_single_exe.py`: Windows-only wrapper that runs the repo's PyInstaller build with fixed output paths.
- `mc_server_manager.spec`: PyInstaller spec for the single-file `mc-server-manager.exe` build.

## Dependency Rules

- Keep packaging behavior isolated from the runtime app so source-run development stays simple.
- Prefer one stable build entrypoint over ad hoc shell commands.

## Change Notes

- Update this README when the build output path, build command, or packaging layout changes.
