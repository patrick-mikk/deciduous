# Setting up the MySQL database on cPanel

A focused, start-to-finish walkthrough for provisioning Deciduous's MySQL
database on a cPanel host. This expands step 2 of the full deploy runbook
([deploy-cpanel.md](deploy-cpanel.md)) — do this before the "Setup Python App"
steps there. Nothing here touches the frontend.

**What you'll end up with:** a MySQL database with the app's 7 tables, a
dedicated DB user, and the `DB_*` environment variables the backend reads to
connect (`backend/config_app.py:29-45`).

## 1. Create the database and user (cPanel UI)

cPanel → **Databases → MySQL® Databases**:

1. **Create New Database** — enter a short name, e.g. `deciduous`. cPanel
   prefixes it with your account username, producing `cpaneluser_deciduous`.
   The **full prefixed name** is what you'll use everywhere below.
2. Under **MySQL Users → Add New User** — e.g. `deciduous` (also prefixed →
   `cpaneluser_deciduous`). Use the password generator; save the password in
   your password manager now — cPanel won't show it again.
3. Under **Add User To Database** — select the user + database, click **Add**,
   and on the privileges screen check **ALL PRIVILEGES** → **Make Changes**.

> Why ALL PRIVILEGES: the app itself only needs data privileges
> (SELECT/INSERT/UPDATE/DELETE), but the one-time provisioning step in §3
> issues `CREATE TABLE` DDL. You can narrow the grant to data-only privileges
> after §3 if you want, but it must include CREATE the first time.

## 2. Set the environment variables

The backend builds its connection string from five variables
(`backend/config_app.py:29-45`):

| Env var | Value | Notes |
|---|---|---|
| `DB_HOST` | `localhost` | Unless cPanel's MySQL panel says the DB is on a remote host. |
| `DB_PORT` | `3306` | Optional — defaults to 3306. |
| `DB_NAME` | `cpaneluser_deciduous` | Full **prefixed** database name. |
| `DB_USER` | `cpaneluser_deciduous` | Full **prefixed** user name. |
| `DB_PASSWORD` | *(the generated password)* | Special characters are fine — the URI builder escapes them. |

⚠️ **All three of `DB_HOST`, `DB_NAME`, `DB_USER` must be set.** If any one is
missing, the backend silently falls back to a local SQLite file
(`backend/instance/dev.sqlite3`) — fine in dev, wrong in production. The §3
script refuses to run in that state specifically to catch this.

Two places to put them (either works; using both is fine — real env vars win
over `.env`, `backend/config.py:22-40`):

- **cPanel UI** — Software → Setup Python App → your app → **Environment
  Variables** → add each var. (If you haven't created the Python app yet,
  you'll do this during [deploy-cpanel.md](deploy-cpanel.md) step 5 —
  the `.env` file below is enough for now.)
- **`.env` file** — `KEY=VALUE` lines (no quotes, no `export`) in a git-ignored
  `.env` at the **repo root** on the server (e.g. `~/deciduous/.env`, outside
  `public_html`):

  ```
  DB_HOST=localhost
  DB_NAME=cpaneluser_deciduous
  DB_USER=cpaneluser_deciduous
  DB_PASSWORD=paste-generated-password-here
  ```

## 3. Create the tables

A fresh MySQL database has **zero tables** — the app never auto-provisions
MySQL on boot (SQLite dev fallback only, `backend/extensions.py:74`). Run the
explicit provisioning script once, over SSH, from the repo root, inside the
app's virtualenv (or after `pip install -r backend/requirements.txt`):

```
$ cd ~/deciduous
$ python -m backend.scripts.init_db
```

Expected output (host/db only — it never prints the password):

```
Target database: mysql+pymysql://localhost:3306/cpaneluser_deciduous
Tables present after create_all (7): plan_items, plans, program_enrolments, sessions, shares, transcript_entries, users
```

The script is **idempotent** — it only creates tables that don't exist, so
re-running it is always safe. (It does **not** migrate schema changes to
existing tables.)

## 4. Verify

Either re-run the script (the table list doubles as verification), or check in
cPanel → **phpMyAdmin** → select the database → you should see the 7 tables
above. From a shell:

```
$ mysql -u cpaneluser_deciduous -p cpaneluser_deciduous -e "SHOW TABLES;"
```

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `Refusing to run: DB_HOST/DB_NAME/DB_USER are not all set…` | One of the three vars is missing/typo'd where the script runs. If you used `.env`, confirm it's at the repo root you're running from and has no quotes around values. |
| `Access denied for user '…'@'localhost'` | Wrong password, or the user wasn't added to the database with ALL PRIVILEGES (§1.3). Unprefixed names are the usual culprit — use the full `cpaneluser_…` forms. |
| `Unknown database '…'` | `DB_NAME` missing the account prefix, or the DB was created under a different cPanel account. |
| `cryptography package is required` on connect | MySQL 8's default auth needs the `cryptography` package — it's pinned in `backend/requirements.txt`; make sure you installed requirements **inside the same virtualenv** you run the script from. |
| Script ran but the app still writes to SQLite | The Python app's environment doesn't have the `DB_*` vars — set them in Setup Python App (cPanel env vars are per-app, not account-wide) and **restart the app**. |
| `Can't connect to MySQL server on '…'` | `DB_HOST` should almost always be `localhost` on cPanel — only use a hostname if cPanel's MySQL panel explicitly lists a remote DB host. |

## Next

Continue with the full runbook from step 3 (code layout) onward:
[deploy-cpanel.md](deploy-cpanel.md). In particular you'll still need the
non-DB env vars there (`SECRET_KEY`, `DATA_KEY_PEPPER` — **one-way, back it
up** — and `GEMINI_API_KEY`).
