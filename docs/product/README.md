# Product Docs

## Purpose

Describes the intended behavior of world CRUD, validation, and activation.

## Contents

- A world is a remote-managed pair of `server.properties` and `whitelist.json`.
- Saving updates only the managed copy.
- Activating replaces the live files in the remote server root.
- Optional RCON console access allows request/response command execution without live console streaming.

## Dependency Rules

- Product behavior described here should match the GUI and service layer.

## Change Notes

- Update this file when world lifecycle rules or statuses change.
