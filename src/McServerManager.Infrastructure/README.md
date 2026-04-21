# Infrastructure

## Purpose
Provides adapters for env loading, SFTP file access, and hash generation.

## Contents
- `Environment/`: `.env` parsing.
- `Sftp/`: connection factory.
- `Storage/`: remote world and live-file persistence.
- `Hashing/`: SHA-256 implementation.

## Dependency Rules
- Infrastructure references Application and Domain but should not leak transport details back into callers.

## Change Notes
- Keep remote path conventions centralized to avoid drift across adapters.

