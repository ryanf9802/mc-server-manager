# Config

## Purpose
Owns typed connection setting aliases shared by infrastructure and service code.

## Contents
- `settings.py`: aliases for SFTP and RCON connection settings dataclasses.

## Dependency Rules
- Keep typed setting aliases thin and free of GUI or storage concerns.

## Change Notes
- Update this directory when shared connection setting types move or are renamed.
