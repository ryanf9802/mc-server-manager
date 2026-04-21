# App Host

## Purpose
Bootstraps dependency injection and application startup composition.

## Contents
- `Bootstrapper.cs`: registers services, settings, and the shell window.

## Dependency Rules
- Startup wiring belongs here, not inside feature view-models.

## Change Notes
- Update registrations here when adding new services or feature windows.

