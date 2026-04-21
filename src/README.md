# Source

## Purpose

Contains the production Python package organized by responsibility.

## Contents

- `mc_server_manager/`: application package root.

## Dependency Rules

- GUI code depends on services, not on raw Paramiko calls.
- Infrastructure depends on config and domain types, not on tkinter.

## Change Notes

- Keep the package nested and intentional; avoid a flat utility bucket.
