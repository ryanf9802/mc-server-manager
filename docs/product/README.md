# Product Docs

## Purpose

Describes the intended behavior of the multi-server home screen, provider controls, world CRUD, mod-list management, validation, and activation.

## Contents

- The app starts on a multi-server home screen backed by encrypted local state.
- Each saved server carries provider, SFTP, and optional RCON settings.
- GameHostBros SFTP is entered as one `Connection Address` plus credentials, and the SFTP root is fixed to `/`.
- The home screen supports manual status refresh plus provider-backed `start`, `stop`, `restart`, and `kill`.
- The home screen also exposes app-level build information and a manual in-app update action for managed Windows installs.
- A world is a remote-managed pair of `server.properties` and `whitelist.json`.
- Saving updates only the managed copy.
- Activating replaces the live files in the remote server root.
- A mod list is a remote-managed collection of `.jar` files stored under `.mc-manager/mod-lists`.
- The UI can snapshot the live `mods` folder into a managed mod list or upload local `.jar` files into a managed mod list.
- Multiple mod lists can be staged as active at the same time, and later active lists override earlier ones when jar filenames conflict.
- Applying the staged active mod lists rewrites only the top-level live `.jar` files in the remote `mods` folder.
- Optional RCON console access allows request/response command execution without live console streaming.
- Server configurations can be exported or imported as encrypted single-server files.

## Dependency Rules

- Product behavior described here should match the GUI and service layer.

## Change Notes

- Update this file when world or mod-list lifecycle rules or statuses change.
