# 0005. Fernet per-user encryption at rest

- **Status:** Accepted
- **Date:** 2026-07-07

## Context

Transcripts and plans are sensitive academic records. A plain DB dump should not
expose grades/marks/notes. We want field-level encryption where even the server
operator's DB access alone is insufficient to read a user's records.

## Decision

Encrypt sensitive columns (grades, marks, plan notes) with **Fernet**
(AES-128-CBC + HMAC, from the `cryptography` library). Each user has a random
**data key**, stored **wrapped** by a key derived from their password (Argon2/PBKDF2)
at login and held only in the session. A server-side pepper/master key lives in an
environment variable outside the webroot. All transport over HTTPS.

## Consequences

- DB dump alone can't decrypt transcripts (needs the user's session-derived key).
- **Password reset loses the data key** unless a recovery mechanism (e.g. recovery
  code that also wraps the data key) is added — must design this into auth.
- Encrypted columns aren't queryable/searchable server-side; acceptable for this data.
- Slight complexity in the session lifecycle (unwrap on login, hold in session).
