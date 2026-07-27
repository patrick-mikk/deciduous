# Auto-deploy from GitHub (no SSH)

Push to `main` → GitHub Actions tests + builds → the live cPanel app updates
itself. After the one-time setup below, you never SSH in to update files.

## How it works

```
push to main
  └─ GitHub Action (.github/workflows/deploy-branch.yml)
       ├─ backend tests (stable subset)          ── failure = live site untouched
       ├─ frontend typecheck + vite build
       └─ force-push `deploy` branch  = main + built frontend/dist
            └─ GitHub webhook → POST https://deciduous.mikkelsen.ca/api/deploy/webhook
                 └─ server (backend/api/deploy.py + backend/scripts/deploy.py):
                      verify HMAC signature (DEPLOY_WEBHOOK_SECRET)
                      git fetch + reset --hard origin/deploy
                      pip install -r  (only if requirements.txt changed)
                      python -m backend.scripts.init_db  (schema step, MySQL only)
                      touch tmp/restart.txt  (Passenger restarts on next request)
```

The server checkout is a pure mirror of `deploy` — never edit files on the
server (a deploy hard-resets them). Untracked files (`.env`,
`backend/instance/`, the course cache) are never touched.

## One-time setup

### 1. Server: clone tracks the `deploy` branch

On the cPanel host, the app root must be a git clone whose `origin` points at
GitHub and can fetch without a prompt. For a **private** repo, create a
fine-grained **read-only** personal access token (Contents: Read) and embed it
in the remote URL once (cPanel → Terminal, or the one SSH session you'll ever
need):

```
cd ~/deciduous
git remote set-url origin https://<TOKEN>@github.com/curejoker/Deciduous.git
git fetch origin deploy && git checkout deploy
```

### 2. Server: set the secret

Generate a secret and add it to the cPanel Python-app environment variables
(same screen as the `DB_*` vars — see [deploy-cpanel.md](deploy-cpanel.md)):

```
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

- `DEPLOY_WEBHOOK_SECRET` = that value (unset ⇒ the whole feature is off; all
  `/api/deploy/*` routes 503)
- `DEPLOY_BRANCH` = only if not `deploy`

Restart the app once from the cPanel UI so the config loads.

### 3. GitHub: add the webhook

Repo → Settings → Webhooks → Add webhook:

| Field | Value |
|---|---|
| Payload URL | `https://deciduous.mikkelsen.ca/api/deploy/webhook` |
| Content type | `application/json` |
| Secret | the same `DEPLOY_WEBHOOK_SECRET` value |
| Events | Just the push event |

GitHub sends a `ping` on save — a green check there means the signature and
URL are right.

That's it. The Action ships with the repo, so the next merge to `main`
deploys itself.

## Day-to-day

- **Deploy** = merge/push to `main`. Nothing else.
- **Check the last deploy** (from anywhere):

  ```
  curl -H "Authorization: Bearer $DEPLOY_WEBHOOK_SECRET" \
       https://deciduous.mikkelsen.ca/api/deploy/status
  ```

- **Force a deploy now** (e.g. after fixing the webhook config):

  ```
  curl -X POST -H "Authorization: Bearer $DEPLOY_WEBHOOK_SECRET" \
       https://deciduous.mikkelsen.ca/api/deploy/run
  ```

- **Roll back**: `git revert` the bad commit on `main` and push — the same
  pipeline deploys the revert. (Force-pushing `main` backwards works too;
  the server hard-resets to whatever `deploy` says.)

## Cron fallback (if the webhook can't reach the server)

The same runner works as a poller — add a cPanel cron job:

Use the app's **virtualenv** interpreter (not the system `python3`) so the
deploy's `pip install` and schema step target the same environment the app
imports from — the exact path is shown at the top of cPanel → Setup Python App
(`docs/deploy-cpanel.md` step 9 makes the same point for the cache cron):

```
*/5 * * * * cd ~/deciduous && /home/cpaneluser/virtualenv/deciduous/3.12/bin/python -m backend.scripts.deploy --if-changed >> ~/deploy-cron.log 2>&1
```

`--if-changed` is silent when already up to date. The runner calls
`load_env()` itself, so DB credentials in `~/deciduous/.env` are picked up
even though cron doesn't inherit the Passenger app's environment. The lock file
(`backend/instance/deploy.lock`) keeps cron and webhook deploys from
overlapping; a lock older than 15 minutes is treated as stale and broken.

## Failure behaviour

- Tests or the frontend build fail in CI → `deploy` branch never moves → the
  live site keeps running the previous good build.
- A server-side step fails (fetch, pip, schema) → the deploy stops at that
  step, the result (with per-step output) is persisted for `/api/deploy/status`,
  and Passenger is NOT restarted — the old code keeps serving. Note the one
  sharp edge: a failure *after* `git reset` but *before* restart leaves new
  files on disk with old code in memory; the status endpoint makes that
  visible, and `POST /api/deploy/run` retries the whole sequence.
- Two triggers race → the second returns `locked` and does nothing.

## What a deploy does NOT do

A deploy ships **code**, not data. It never touches the course/program cache
(`PLANNER_CACHE_PATH`), because a full catalog pull on every push would hammer
the UofT endpoints we're deliberately gentle with (see AGENTS.md, "Boundaries").

So a change to how upstream data is *parsed or classified* — anything under
`backend/data_sources/` — ships as code but keeps serving the previously cached
values until the cache is rebuilt. The nightly cache-refresh cron
(`docs/deploy-cpanel.md` step 9) picks it up within a day; to see it
immediately, run the refresh by hand:

```
$ /home/cpaneluser/virtualenv/deciduous/3.12/bin/python -m backend.scripts.refresh_cache
```

`upsert_programs` is `INSERT OR REPLACE` keyed on program code, so a refresh
rewrites every cached row rather than only adding new ones.
