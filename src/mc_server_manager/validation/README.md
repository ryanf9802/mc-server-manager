# Validation

## Purpose

Keeps file validation rules isolated, reusable, and testable.

## Contents

- `server_properties.py`: line-based validation for `server.properties`.
- `whitelist.py`: JSON shape validation for `whitelist.json`.

## Dependency Rules

- Validators should not perform remote I/O or GUI work.

## Change Notes

- Update this directory before adding UI-only validation shortcuts.
