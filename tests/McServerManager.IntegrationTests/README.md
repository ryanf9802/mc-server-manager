# Integration Tests

## Purpose
Exercises the real SFTP-backed adapters when a contributor explicitly provides remote test credentials.

## Contents
- `SftpRepositoryIntegrationTests.cs`: smoke coverage for `.env` loading and remote adapters.

## Dependency Rules
- Keep tests opt-in and environment-driven so local contributors are not forced to hit a network target.

## Change Notes
- Extend this directory only for scenarios that need real remote behavior.

