# Assets

## Purpose

Contains packaged runtime assets that ship with the desktop application.

## Contents

- `app.ico`: canonical Windows icon used for the packaged executables and runtime window branding.

## Dependency Rules

- Keep one canonical icon asset here and update packaging/runtime code to reference it directly.
- Replace `app.ico` in place when updating branding so build scripts and runtime lookup keep working.

## Change Notes

- Update this README if additional packaged assets are introduced here.
