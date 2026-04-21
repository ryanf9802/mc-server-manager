# Application Configuration

## Purpose
Defines runtime configuration contracts consumed by the rest of the application.

## Contents
- `SftpSettings.cs`: strongly typed runtime settings.
- `IEnvironmentLoader.cs`: abstraction for loading settings from `.env`.

## Dependency Rules
- Keep configuration loading behind interfaces so the desktop app can fail cleanly at startup.

## Change Notes
- Add new runtime settings here before wiring them into infrastructure.

