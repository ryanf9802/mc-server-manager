# Domain

## Purpose
Holds framework-free dataclasses and enums that describe world state, mod-list state, validation results, and shared app metadata.

## Contents
- `models.py`: world manifests, mod-list manifests, active pointers, validation types, and app update/install metadata.

## Dependency Rules
- Keep domain types portable and side-effect free.

## Change Notes
- Add reusable business types here before inventing ad hoc dictionaries elsewhere.
