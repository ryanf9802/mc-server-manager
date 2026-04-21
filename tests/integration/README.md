# Integration Tests

## Purpose

Provides an opt-in place for real SFTP-backed smoke coverage.

## Contents

- `test_sftp_smoke.py`: gated by explicit env vars and skipped by default.

## Dependency Rules

- Never require a network target for the default contributor workflow.

## Change Notes

- Extend this directory only for behavior that cannot be trusted with fakes.
