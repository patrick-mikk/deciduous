# Deploying to cPanel (deciduous.mikkelsen.ca)

Production runbook for Phase 6 (see [roadmap.md](roadmap.md)). Follow the steps in
order — later steps assume earlier ones are done. Commands prefixed `$` run over
SSH on the cPanel box; steps marked **cPanel UI** are done in the browser control
panel.

Code pointers used throughout: [`backend/passenger_wsgi.py`](../backend/passenger_wsgi.py),
[`backend/app.py`](../backend/app.py), [`backend/config_app.py`](../backend/config_app.py),
[`backend/extensions.py`](../backend/extensions.py).

## 1. Prerequisites

- `deciduous.mikkelsen.ca` DNS already pointed at the cPanel host.
- SSH access to the account (Setup Python App also works from the UI alone, but
  `pip install` and the cron/init steps below need a shell).
- Python **3.12** available as a cPanel "Setup Python App" version (check
  cPanel → Software → Setup Python App → the version dropdown before creating
  the app; this project targets 3.12.13 per [AGENTS.md](../AGENTS.md)).

## 2. MySQL database (cPanel UI)

> Detailed walkthrough with verification + troubleshooting:
> [setup-mysql-cpanel.md](setup-mysql-cpanel.md). The short version:

cPanel UI → **MySQL Databases**:

1. Create a database (e.g. `cpaneluser_deciduous`).
2. Create a database user + a strong password.
3. Add the user to the database with **all privileges**.

cPanel prefixes both names with your account username — use the full prefixed
names below. These map directly to the `DB_*` vars `backend/config_app.py`
reads to build the SQLAlchemy URI (`_build_database_uri`, `backend/config_app.py:29-45`):

| cPanel value | Env var |
|---|---|
| Database name (`cpaneluser_deciduous`) | `DB_NAME` |
| Database user | `DB_USER` |
| Database password | `DB_PASSWORD` |
| Host (`localhost` unless cPanel says otherwise) | `DB_HOST` |
| Port (`3306` unless customized) | `DB_PORT` |

If `DB_HOST`/`DB_NAME`/`DB_USER` are not **all** set, `Config` silently falls
back to a local SQLite file (`backend/config_app.py:29-45`) — fine for local
dev, wrong for prod. Step 6's `init_db` script refuses to run against that
fallback specifically to catch this.

## 3. Get the code onto the server

Clone (or upload + extract) the repo **outside** `public_html`, e.g.
`/home/cpaneluser/deciduous`. `public_html` is web-served directly by Apache;
anything under it is a potential leak. Passenger serves the app via the
"Setup Python App" proxy regardless of where the app root lives, so there's no
reason to put it under the docroot.

```
$ git clone <repo-url> ~/deciduous
```

Create `~/deciduous/.env` (git-ignored — see `.gitignore` — and never
committed) for the values in step 5. Keeping it outside `public_html` means
it's never directly fetchable even if Passenger's routing is ever
misconfigured. `backend/config.py::load_env()` reads this file, but a real
env var set through cPanel's "Setup Python App" UI always wins over it
(`setdefault` semantics — `backend/config.py:22-42`).

## 4. cPanel "Setup Python App"

cPanel UI → **Setup Python App** → Create Application:

| Field | Value |
|---|---|
| Python version | 3.12.13 (or closest 3.12.x offered) |
| Application root | `deciduous` (relative to home — i.e. `~/deciduous`) |
| Application URL | `deciduous.mikkelsen.ca` |
| Application startup file | `backend/passenger_wsgi.py` |
| Application Entry point | `application` |

`backend/passenger_wsgi.py` is intentionally minimal — it just puts the repo
root on `sys.path` and calls `backend.app.create_app()` (`backend/passenger_wsgi.py:1-17`);
all real setup happens inside `create_app`.

After creating the app, cPanel shows an "Enter to the virtual environment"
command — run it, then install dependencies inside that venv:

```
$ source /home/cpaneluser/virtualenv/deciduous/3.12/bin/activate
$ cd ~/deciduous
$ pip install -r backend/requirements.txt
```

`backend/requirements.txt` includes `pytest` (tests) and `prompt_toolkit`
(the dev TUI, `backend/tui/`) — neither is imported by `backend.app` or
`backend.passenger_wsgi`, so they can be skipped on the production venv if you
want a leaner install; nothing breaks if they're left in.

## 5. Environment variables (cPanel UI)

Same "Setup Python App" page has an **Environment variables** section — set
these there (they take precedence over `.env`). `FLASK_SECRET_KEY` and
`DATA_KEY_PEPPER` are enforced: `Config.__init__` raises `RuntimeError` at
startup if either is unset while `FLASK_ENV=production` (`backend/config_app.py:63-75`).

| Variable | Required | Value / how to generate |
|---|---|---|
| `FLASK_ENV` | yes | `production` — flips the prod guards below on (`backend/config_app.py:57`) |
| `FLASK_SECRET_KEY` | yes | `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `DATA_KEY_PEPPER` | yes | same generator as above, **a different value** |
| `DB_HOST` | yes | from step 2 |
| `DB_NAME` | yes | from step 2 |
| `DB_USER` | yes | from step 2 |
| `DB_PASSWORD` | yes | from step 2 |
| `DB_PORT` | no | defaults to `3306` (`backend/config_app.py:36`) |
| `CORS_ORIGIN` | yes | `https://deciduous.mikkelsen.ca` |
| `PLANNER_CACHE_PATH` | strongly recommended | absolute path outside `public_html` and outside `/tmp`, e.g. `/home/cpaneluser/deciduous-data/cache.sqlite` — see step 9 |
| `SESSION_COOKIE_SECURE` | no | defaults to `True` when `FLASK_ENV=production` (`backend/config_app.py:86-90`); only set explicitly to override |
| `SESSION_LIFETIME_SECONDS` | no | remember-me cookie lifetime cap; defaults to 30 days. Per-session server-side expiry is 24h (default) / 30d (remember-me) in `backend/api/auth.py` |
| `PASSKEY_RP_ID` | no | WebAuthn relying-party ID; defaults to the hostname of `PASSKEY_ORIGIN`/`CORS_ORIGIN` (`deciduous.mikkelsen.ca`) — set explicitly only if serving from multiple subdomains |
| `PASSKEY_ORIGIN` | no | full origin the browser reports during passkey ceremonies; defaults to `CORS_ORIGIN` |
| `PASSKEY_RP_NAME` | no | display name shown in the browser's passkey sheet; defaults to `Deciduous` |
| `FRONTEND_DIST` | no | absolute path to the built SPA if it doesn't live at `<repo root>/frontend/dist` (`backend/app.py:139`) |
| `SMTP_HOST` | for email flows | the cPanel mail server, e.g. `mail.mikkelsen.ca` — unset, email sending is a logged no-op and the app still works (verification banner stays; emailed reset links can't be sent) |
| `SMTP_PORT` | no | defaults to `465` (implicit SSL); set `587` for STARTTLS |
| `SMTP_USER` | with SMTP_HOST | the mailbox, e.g. `deciduous@mikkelsen.ca` |
| `SMTP_PASSWORD` | with SMTP_HOST | that mailbox's password |
| `MAIL_FROM` | no | From address; defaults to `SMTP_USER` |
| `MAIL_FROM_NAME` | no | From display name; defaults to `Deciduous` |
| `APP_BASE_URL` | no | absolute base for emailed verify/reset links; defaults to `CORS_ORIGIN` |
| `DEPLOY_WEBHOOK_SECRET` | for auto-deploy | shared secret for the GitHub webhook / manual deploy trigger — see [auto-deploy.md](auto-deploy.md); unset, the `/api/deploy/*` routes are disabled |
| `DEPLOY_BRANCH` | no | branch the server self-updates from; defaults to `deploy` (published by the GitHub Action) |
| `GEMINI_API_KEY` | optional | see below |
| `GEMINI_MODEL` | no | overrides the grouper's default Gemini model (`backend/data_sources/llm_grouper.py:260`); only meaningful with `GEMINI_API_KEY` set |

> **Warning — `DATA_KEY_PEPPER` is one-way.** It's mixed into every user's
> wrapped per-user data key (ADR-0005). Changing it after real users exist
> makes their encrypted transcript/plan data **permanently unreadable** — there
> is no re-wrap/migration path today. Generate it once, store it somewhere
> durable (password manager), and never regenerate it against a live database.
> It also derives the server-side wrap that powers passkey sign-in (ADR-0006):
> rotating it breaks passkey sign-in until users re-register a passkey.

`GEMINI_API_KEY` (optional) powers the on-demand program-requirement grouper
(`backend/data_sources/llm_grouper.py`, called from `POST
/api/programs/:code/requirements/reparse`). Without it, that one endpoint
raises a `LLMGroupingError` telling the caller to set the key
(`backend/data_sources/llm_grouper.py:277-278`); everything else in the app —
search, plan, validators, transcript — is unaffected.

## 6. Initialize the schema

```
$ python -m backend.scripts.init_db
```

Loads env the same way `create_app` does, builds `Config`, and calls
`create_all` against whatever `SQLALCHEMY_DATABASE_URI` resolves to
(`backend/scripts/init_db.py:69-90`). Expected output on first run:

```
Target database: mysql+pymysql://<host>:<port>/<db-name>
Tables present after create_all (7): ...
```

(Only scheme/host/port/db name print — never the password;
`_safe_target`, `backend/scripts/init_db.py:40-46`.) It's idempotent — rerunning
after the tables exist reprints the same table count and is a no-op DDL-wise
(`CREATE TABLE IF NOT EXISTS` semantics, not a migration tool). If `DB_*` isn't
fully set, it refuses with exit 1 rather than silently provisioning the SQLite
fallback (`backend/scripts/init_db.py:72-79`); pass `--allow-sqlite` only if
that's genuinely what you want (e.g. a throwaway smoke test).

## 7. Frontend build

cPanel has no Node — build on your dev machine and upload the result:

```
$ cd frontend
$ npm ci
$ npm run build
```

Upload the contents of `frontend/dist/` to the path Flask serves from: either
`<repo root>/frontend/dist` (the default `_register_spa` looks for,
`backend/app.py:40`) or wherever `FRONTEND_DIST` (step 5) points. If no build
is present at startup, `_register_spa` logs one line and registers nothing —
`GET /` 404s and the app stays API-only (`backend/app.py:140-146`).

Upload files only — don't leave a previous build's hashed asset alongside the
new one. `index.html` references exactly one JS and one CSS file by content
hash, so stale siblings are dead weight (and confusing when debugging):

```
$ ssh user@host 'ls ~/<app dir>/frontend/dist/assets/'
$ grep -o 'assets/[^"]*' frontend/dist/index.html    # the only two that matter
```

Permissions after an SFTP upload default to owner-only, which Passenger can't
serve. This is all public static content, so: `chmod 755` the `dist` and
`assets` directories, `chmod 644` the files.

### API base — plain `npm run build` is what you want

`frontend/src/api/client.ts:346` resolves `VITE_API_BASE` when set, and
otherwise defaults **every** build to the relative path `/api` — same-origin
against this same Flask process, so no build-time env var is needed here.

The offline demo adapter is opt-in only (`VITE_API_BASE=mock`) and renders
seeded sample transcripts/programs/GPA. Because Vite inlines env vars at build
time, a stray `frontend/.env` left from local UI work would bake that into
`dist/` and serve fake data to every visitor. `vite.config.ts` now refuses such
a build outright; if you ever need to confirm a bundle by hand:

```
$ grep -c '"mock"' frontend/dist/assets/*.js    # 0 = clean production build
```

## 8. AutoSSL / HTTPS

cPanel UI → **SSL/TLS Status** → run AutoSSL for `deciduous.mikkelsen.ca` (or
confirm it already issued a cert — cPanel typically auto-runs this once DNS
resolves to the account). Do this before or right after step 4; Passenger apps
work over plain HTTP too, but `SESSION_COOKIE_SECURE` defaults to `True` in
production (`backend/config_app.py:86-90`), so the session cookie is marked
`Secure` and **browsers will not send it back over plain HTTP** — sign-in will
appear to silently fail until HTTPS is live.

## 9. Nightly cache-refresh cron (cPanel UI → Cron Jobs)

`PLANNER_CACHE_PATH` (step 5) must be a path outside `/tmp` — shared hosting
wipes `/tmp` between reboots/cleanups, silently dropping the course/program
cache (`backend/extensions.py:86-98`). Set it once and use the same value for
both the app's env vars and the cron job below.

First, test with `--dry-run` (no network calls, just reports what it would
do — safe to run any time):

```
$ /home/cpaneluser/virtualenv/deciduous/3.12/bin/python -m backend.scripts.refresh_cache --dry-run
```

Then add the real nightly cron (cPanel UI → **Cron Jobs**, or `crontab -e`):

```
0 3 * * * /home/cpaneluser/virtualenv/deciduous/3.12/bin/python -m backend.scripts.refresh_cache >> /home/cpaneluser/deciduous-data/refresh_cache.log 2>&1
```

Use the venv's `python` directly (not the system one) so `requests`/
`SQLAlchemy`/etc. resolve; cron doesn't source `~/.bashrc` or activate venvs.
`refresh_cache.py` discovers session codes at runtime via
`TTBClient.current_sessions()` — never hard-coded (AGENTS.md) — pulls ARTSC
courses per session and the full program catalog, and throttles between bulk
calls (`backend/scripts/refresh_cache.py:89-126`). It exits 1 with a one-line
`stderr` message on failure (session discovery failure, zero sessions, or any
exception during the pull) and 0 with a one-line summary on success — check
the log after the first scheduled run.

## 10. Smoke tests

```
$ curl -s https://deciduous.mikkelsen.ca/ | head -c 200          # HTML (index.html)
$ curl -s https://deciduous.mikkelsen.ca/api/health               # {"status": "ok", ...}
$ curl -s -c cookies.txt https://deciduous.mikkelsen.ca/api/auth/csrf   # {"csrfToken": "..."}
$ curl -s -b cookies.txt -X POST https://deciduous.mikkelsen.ca/api/auth/signup \
    -H "Content-Type: application/json" \
    -H "X-CSRF-Token: <csrfToken from above>" \
    -d '{"email":"smoketest@example.com","password":"a-long-enough-password"}'
    # 201 {"user": {...}} — delete this test user afterward
```

(`backend/api/auth.py:71-113`: `GET /api/auth/csrf` sets the double-submit
cookie; `POST /api/auth/signup` needs both the cookie and the matching
`X-CSRF-Token` header.)

Passenger logs stdout/stderr to `stderr.log` in the application root
(`~/deciduous/stderr.log`) — check it first for any 500. After changing code
or env vars, restart the app without going through the cPanel UI:

```
$ mkdir -p ~/deciduous/tmp && touch ~/deciduous/tmp/restart.txt
```

## 11. Troubleshooting

| Symptom | Likely cause |
|---|---|
| Blank page / `GET /` 404s | `frontend/dist` missing at the expected path, or `FRONTEND_DIST` points somewhere wrong — check `stderr.log` for the "No frontend build at ..." info line (`backend/app.py:141-146`) |
| 500 on every request | `FLASK_SECRET_KEY` or `DATA_KEY_PEPPER` unset with `FLASK_ENV=production` (raises `RuntimeError` at boot, `backend/config_app.py:63-75`); or MySQL schema not initialized yet — run step 6 |
| App loads but shows seeded/fake data plus a "Demo data" banner | `VITE_API_BASE=mock` was set (usually a leftover `frontend/.env`) when the bundle was built, so the offline adapter got inlined (`frontend/src/api/client.ts:346`). Delete the `.env`, `rm -rf dist`, rebuild, re-upload, and delete the old hashed asset on the server. `vite.config.ts` now fails this build up front, so a bundle built after that guard landed can't be in this state |
| New build uploaded but the browser shows the old UI | Either the stale hashed asset is still on the server and `index.html` wasn't replaced, or it's a browser cache — hard-refresh (Ctrl+Shift+R) and confirm `index.html` names the hash you just built |
| Course/program search looks stale | Nightly cron (step 9) isn't running, or `PLANNER_CACHE_PATH` was unset when the cron ran so the cache landed in the OS temp dir and got wiped (`backend/extensions.py:90-98`) — check the cron log and confirm the env var is set in **both** the app and cron environments |

See also: [ADR-0002](decisions/0002-mysql-over-sqlite.md) (MySQL),
[ADR-0003](decisions/0003-no-selenium-http-data-layer.md) (no Selenium),
[ADR-0004](decisions/0004-cookie-sessions-over-jwt.md) (cookie sessions/CORS),
[ADR-0005](decisions/0005-fernet-per-user-encryption.md) (encryption at rest).
