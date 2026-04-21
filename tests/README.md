# Tests

## Purpose
Holds automated coverage for core rules and remote integration behavior.

## Contents
- `McServerManager.UnitTests/`: pure logic coverage.
- `McServerManager.IntegrationTests/`: opt-in remote SFTP integration coverage.

## Dependency Rules
- Unit tests should prefer fakes and avoid network access.
- Integration tests may use network resources only when explicitly configured through env vars.

## Change Notes
- Keep new test directories documented before adding files under them.

