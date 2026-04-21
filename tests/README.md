# Tests

## Purpose
Contains automated coverage for encrypted app state, provider adapters, pure logic, and opt-in SFTP integration behavior.

## Contents
- `unit/`: deterministic unit and service tests.
- `integration/`: environment-gated integration coverage.

## Dependency Rules
- Keep unit tests network-free.
- Integration tests must skip unless explicitly configured.

## Change Notes
- Keep new test directories documented before adding files under them.
