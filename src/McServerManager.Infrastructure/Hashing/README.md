# Hashing Infrastructure

## Purpose
Supplies deterministic hashing used for activation tracking and drift detection.

## Contents
- `Sha256HashService.cs`: SHA-256 string hashing adapter.

## Dependency Rules
- Hashing should stay isolated so callers never hand-roll digest logic.

## Change Notes
- Update here if content normalization rules change before hashing.

