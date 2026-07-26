# Production hardening plan — public multi-user deployment

The plan for taking the backend from "works for one developer" to "safe and
fast for a public multi-user deployment" at `deciduous.mikkelsen.ca` (cPanel
Passenger, Python 3.12, cPanel MySQL). Ordered by risk: each phase is
shippable on its own. Items marked ✅ shipped with the account/passkey-auth
change; unchecked items are the actual remaining plan.

## Phase A — Account & session security (mostly shipped)

- [x] **Remember-me sessions** — 24h non-persistent session by default,
  opt-in 30-day persistent session (`rememberMe` on signin/signup;
  `backend/api/auth.py`). DB `Session.expires_at` is authoritative, so a
  stale cookie is inert.
- [x] **Passkey (WebAuthn) sign-in** — discoverable credentials, register /
  list / delete + usernameless sign-in (`backend/api/passkeys.py`,
  ADR-0006 for the data-key model).
- [x] **Session management** — list active sessions, revoke one, revoke all
  others; password change revokes other sessions.
- [x] **Password change with key re-wrap** — data key survives, encrypted
  rows untouched.
- [x] **Recovery codes** — bcrypt-hashed, shown once, wrap the data key so a
  forgotten-password reset no longer destroys encrypted data (closes the
  ADR-0005 gap).
- [x] **Account deletion** — password-confirmed, cascades to all user data.
- [x] **Email verification on signup** — signed 3-day token links over SMTP
  (`backend/mailer.py`, stdlib smtplib; configure `SMTP_*` env vars for the
  `deciduous@mikkelsen.ca` mailbox). `users.verified_at` + `/api/auth/verify`
  + resend; a redeemed reset link also counts as verification. Remaining
  follow-up: decide what (if anything) to gate on unverified accounts —
  share links are the natural candidate.
- [x] **Email-based password reset** — `/auth/reset` (no code) emails a
  1-hour signed link; `/auth/reset/confirm` redeems it. Preserves the
  encrypted data key when the account has a passkey (via the ADR-0006
  server wrap); otherwise issues a fresh key with the UI warning shown
  up front, and reports `dataPreserved` either way.
- [ ] **IP-level rate limiting** — per-account lockout exists and is
  multi-process-safe, but signup/reset/csrf endpoints have no per-IP
  throttle. On shared hosting, do it in `.htaccess`/mod_security or a tiny
  DB-backed counter table (in-memory counters don't survive Passenger's
  process model).

## Phase B — Transport & headers

- [ ] **Security headers** — add an `after_request` block: `Strict-Transport-
  Security` (after AutoSSL is verified), `X-Content-Type-Options: nosniff`,
  `Referrer-Policy: strict-origin-when-cross-origin`, `X-Frame-Options:
  DENY`, and a CSP for the SPA (self + inline styles the DS needs; no
  third-party origins exist by design).
- [ ] **Cookie scope audit** — `SameSite=Lax` + `Secure` + `httpOnly` are
  set; confirm the CSRF cookie stays non-httpOnly (it must be readable) and
  that nothing else is.
- [ ] **CORS in production** — same-origin serving makes CORS nearly moot;
  set `CORS_ORIGIN` to the exact HTTPS origin and remove any localhost
  values from the cPanel env.

## Phase C — Database & schema lifecycle

- [x] **Idempotent schema evolution** — `create_all` + automatic
  `ADD COLUMN` for new nullable columns (`backend/extensions.py`), run by
  `python -m backend.scripts.init_db` on deploy.
- [ ] **Move to Alembic when churn grows** — the column-adder deliberately
  refuses renames/type changes/NOT NULL; adopt Alembic the first time one of
  those is needed rather than hand-writing SQL.
- [ ] **Connection pool sizing** — Passenger runs N worker processes, each
  with its own SQLAlchemy pool. cPanel MySQL caps `max_user_connections`
  (often 30). Set `pool_size=2, max_overflow=3, pool_recycle=280` (under
  MySQL's `wait_timeout`) in `init_db` so N workers × pool stays below the
  cap. `pool_pre_ping` is already on.
- [ ] **Indexes review** — hot paths are keyed by `user_id` (indexed) and
  `sessions.expires_at` scans for cleanup; add a composite index on
  `sessions (user_id, revoked_at)` if the sessions list ever slows.
- [ ] **Expired-row cleanup cron** — sessions and revoked shares accumulate
  forever. Nightly cron: delete sessions expired > 30 days and revoked
  shares > 90 days.
- [ ] **Backups** — nightly `mysqldump` to a non-webroot path + rotation;
  verify a restore once. Encrypted columns stay encrypted in dumps by
  design, so a leaked backup is still safe.

## Phase D — Catalog data layer under concurrency

- [ ] **Persist the course cache** — set `PLANNER_CACHE_PATH` outside `/tmp`
  (shared hosts wipe it); already documented in the deploy runbook, verify
  it on the live box.
- [ ] **Nightly warm cron** — one session-scoped TTB pull per night keeps
  every user's searches hitting SQLite instead of the live API (also the
  polite-client behaviour AGENTS.md requires). Throttle: the cron is the
  ONLY bulk puller; request-path fetches stay single-course.
- [ ] **SQLite cache under multi-process reads** — readers are fine
  (WAL/shared cache), but confirm the cache opens read-only-tolerant when
  the cron is mid-write; add a busy_timeout.
- [ ] **Gemini grouper concurrency guard** — `reparse` takes 10–20s; two
  users clicking it for the same program should coalesce (a `parsing` flag
  row or lock file), not double-spend API quota.

## Phase E — Observability & operations

- [ ] **Structured request logging** — one line per request (method, path,
  status, ms, user id-or-anon) to Passenger's log; no PII beyond the user id.
- [ ] **Error alerting** — the JSON 500 handler already logs tracebacks;
  add a daily logwatch email (cPanel cron + `mail`) or a free Sentry
  project (allowed: outbound HTTPS from the server is fine — it's the
  *browser* that must stay first-party-only).
- [ ] **Health endpoint monitoring** — `/api/health` exists; point an
  external uptime monitor at it.
- [ ] **Capacity sanity check** — sign-in costs one bcrypt verify + one
  390k-iteration PBKDF2 (~150–300ms CPU). At cPanel scale that's fine for
  hundreds of users but is the first thing to profile if login latency
  climbs; passkey sign-in (no PBKDF2) is the cheap path to nudge users to.

## Phase F — Product-level account features

- [ ] **Data export** — `GET /api/me/export` returning the user's decrypted
  transcript/plan as JSON/CSV (the Settings button currently demos it).
  Requires a live session (data key in hand), so it's a thin serializer.
- [ ] **Terms of Service / Privacy pages** — the signup checkbox links to
  nothing; write both (what's stored, encryption model, deletion rights)
  before public launch.
- [ ] **Frontend bundle splitting** — the SPA is one ~1.1 MB chunk; lazy-load
  the heavy screens (Timetable, Plan) via `React.lazy` to cut first-paint on
  residence Wi-Fi.

## Explicit non-goals (constraints that still hold)

- No Selenium/headless Chrome (ADR-0003) — shared host can't run it.
- No JWT (ADR-0004) — cookie sessions with a DB revocation row.
- No second datastore/queue — cPanel offers MySQL + cron; design within that.
