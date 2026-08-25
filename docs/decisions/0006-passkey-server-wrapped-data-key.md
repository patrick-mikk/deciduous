# 0006. Server-wrapped data key for passkey sign-in

- **Status:** Accepted
- **Date:** 2026-07-26

## Context

ADR-0005 wraps each user's Fernet data key with a KEK derived from their
**password** (+ per-user salt + server pepper), so only a live sign-in can
unwrap it. Passkey (WebAuthn) sign-in breaks that assumption: an assertion
proves possession of the authenticator but carries **no secret** the server
can derive a KEK from. The WebAuthn PRF extension could provide one, but
browser/authenticator support is still uneven and it would make passkeys
unusable on many devices.

## Decision

When a user registers their **first passkey** (which requires a live session,
so the unwrapped data key is in hand), store one additional wrap of the same
data key on `User.server_wrapped_data_key`, encrypted with a KEK derived from
`DATA_KEY_PEPPER` alone (`backend/security/crypto.py::server_wrap_data_key`,
fixed versioned salt). A passkey sign-in verifies the WebAuthn assertion, then
unwraps that copy to populate the session. Deleting the last passkey deletes
the server-wrapped copy, restoring the stricter password-only model.

## Consequences

- Passkey sign-in fully unlocks encrypted transcript/plan data — no password
  prompt after a biometric sign-in.
- **Weakened threat model, but only for passkey users**: a DB dump alone still
  decrypts nothing (the pepper is env-only), but an attacker with both the DB
  and the server environment can unwrap these users' data keys. Under ADR-0005
  alone they would additionally need each user's password. Accounts that never
  register a passkey are unaffected.
- Rotating `DATA_KEY_PEPPER` invalidates every `server_wrapped_data_key`
  (passkey sign-in fails closed with a logged error; password sign-in still
  works and re-registering a passkey re-creates the wrap) — same "the pepper is
  one-way" warning as `docs/deploy-cpanel.md` already carries.
- If PRF support matures, a per-credential PRF-derived wrap can replace this
  with no schema change (swap what's stored in the wrap column).
