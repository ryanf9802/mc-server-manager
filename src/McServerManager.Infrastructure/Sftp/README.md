# SFTP Infrastructure

## Purpose
Owns low-level SSH.NET connection setup for remote file operations.

## Contents
- `SftpConnectionFactory.cs`: builds connected `SftpClient` instances from runtime settings.

## Dependency Rules
- Connection management stays here so storage adapters focus on file layout and serialization.

## Change Notes
- Expand this directory before introducing alternate auth modes or retry policies.

