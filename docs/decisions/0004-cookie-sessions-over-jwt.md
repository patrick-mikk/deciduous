# 0004. httpOnly cookie sessions (not JWT in localStorage)

- **Status:** Accepted
- **Date:** 2026-07-07

## Context

A React SPA needs to authenticate against the Flask API. Storing a JWT in
`localStorage` is a common but XSS-exposed pattern (any injected script can exfiltrate
the token). The SPA is served **same-origin** with the API, so cross-site token
passing isn't required.

## Decision

Use **server-side sessions** via a signed, **httpOnly, Secure, SameSite=Lax** cookie.
Passwords hashed with **bcrypt**; login is rate-limited.

## Consequences

- Token is not readable by JS → materially reduces XSS token theft.
- Requires same-origin serving (or configured CORS + credentials) — already the plan.
- Need CSRF protection for state-changing requests (SameSite=Lax + CSRF token).
- Reversing to JWT would be driven only by a cross-origin/multi-client need.
