# Verify Directory READMEs

## Purpose

Fails fast when a committed directory under `docs`, `src`, `tests`, or `tools` is missing its local `README.md`.

## Contents

- `check_readmes.py`: scans the repository tree and reports undocumented directories.

## Dependency Rules

- Keep the script dependency-free so it can run in basic contributor environments.

## Change Notes

- Update ignore rules here when build tooling adds generated directories that should be excluded.
