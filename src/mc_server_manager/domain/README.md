# Domain

## Purpose
Holds framework-free dataclasses and enums that describe world state.

## Contents
- `models.py`: world manifests, files, active pointer, validation types, and app update/install metadata.

## Dependency Rules
- Keep domain types portable and side-effect free.

## Change Notes
- Add reusable business types here before inventing ad hoc dictionaries elsewhere.
