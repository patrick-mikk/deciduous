# 0002. cPanel MySQL (not SQLite) for storage

- **Status:** Accepted
- **Date:** 2026-07-07

## Context

The planner is multi-user with logins and per-user encrypted records. cPanel provides
managed MySQL (backups, users, remote access). SQLite is single-file and weak under
concurrent writes on shared hosting.

## Decision

Use **cPanel MySQL** via SQLAlchemy (PyMySQL driver). Credentials from environment
variables. Course/offering/program caches live in the same database.

## Consequences

- Real concurrency and multi-user support; native to the hosting.
- Requires a DB provisioning step in cPanel and connection config per environment.
- Local dev points at a dev MySQL (or a MySQL container); tests avoid the DB where possible.
- Reversing to SQLite would sacrifice concurrency and is not planned.
