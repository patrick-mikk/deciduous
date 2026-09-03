# Auto-deploy from GitHub (no SSH)

Push to `main` → GitHub Actions tests + builds → the live cPanel app updates
itself. After the one-time setup below, you never SSH in to update files.

## How it works

The same Action gates pull requests and publishes from `main` — the checks
that decide whether a PR is mergeable are the ones that decide whether the
live site updates, so nothing reaches production having passed a weaker bar:

```
pull request → backend tests + frontend typecheck/build   (gate only, no publish)

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

## One-time setup (the first cutover)

> **Bootstrap note.** `/api/deploy/*` ships *in the code being deployed*
> (`backend/api/deploy.py`, added in #11). A server still running anything
> older doesn't have those routes at all, so the first cutover cannot use the
> deploy runner to deploy itself — it is manual, once. Every deploy after this
> is a `git push`.
>
> The runner handles `pip install` and `init_db` on later deploys
> (`backend/scripts/deploy.py`), which is why they appear here as manual steps
> and never again.

### 1. Server: move the clone onto the `deploy` branch

The app root must be a git clone whose `origin` points at GitHub and can fetch
without a prompt. For this **private** repo, create a fine-grained
**read-only** personal access token (Contents: Read) and embed it in the remote
URL once. It sits in plaintext in `.git/config`, so read-only genuinely
matters.

```
cd ~/deciduous
rm -rf frontend/dist
git remote set-url origin https://<TOKEN>@github.com/curejoker/Deciduous.git
git fetch origin deploy
git checkout deploy
```

**Why `rm -rf frontend/dist` first:** `frontend/dist/` is gitignored on `main`
but **tracked** on `deploy` (CI commits the build there because cPanel has no
Node — see the diagram above). A server that was deployed manually has an
untracked `dist` sitting exactly where those tracked files land, and
`git checkout deploy` aborts with *"untracked working tree files would be
overwritten"*. Deleting it first is safe: the tracked copy replaces it.

Untracked state — `.env`, `backend/instance/`, the cache DB — is not touched by
the checkout, or by any later deploy (there is no `git clean`).

Confirm you landed on the build you expect:

```
git log --oneline -1        # -> "Deploy build of <main sha>"
```

### 2. Server: install dependencies and migrate

A cutover can cross many merges at once, so do both explicitly this first time:

```
source /home/cpaneluser/virtualenv/deciduous/3.12/bin/activate
cd ~/deciduous
pip install -r backend/requirements.txt
python -m backend.scripts.init_db
```

`pip install` matters whenever new packages landed since the server last
updated (`webauthn`, `pyOpenSSL`, `itsdangerous` arrived with the auth
surface); the app won't boot without them. A `ResolutionImpossible` here means
the checkout is older than you think — verify step 1.

`init_db` is additive and idempotent (`create_all` plus nullable-column
`ALTER TABLE`s — `backend/extensions.py::_add_missing_columns`), but it is the
step most likely to surface a real problem on a first cutover. Read its output
rather than assuming.

### 3. Server: set the secret

Generate a secret and add it to the cPanel Python-app environment variables
(same screen as the `DB_*` vars — see [deploy-cpanel.md](deploy-cpanel.md)):

```
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

- `DEPLOY_WEBHOOK_SECRET` = that value (unset ⇒ the whole feature is off; all
  `/api/deploy/*` routes 503)
- `DEPLOY_BRANCH` = only if not `deploy`

**Treat this as a code-execution key**, not just an API token: anyone holding
it can `POST /api/deploy/run` and make the server fetch and execute a branch.
cPanel env vars and a password manager, nowhere else — never a commit, an
issue, or a chat log.

Restart the app once from the cPanel UI so the config loads.

### 4. GitHub: add the webhook

Repo → Settings → Webhooks → Add webhook:

| Field | Value |
|---|---|
| Payload URL | `https://deciduous.mikkelsen.ca/api/deploy/webhook` |
| Content type | `application/json` |
| Secret | the same `DEPLOY_WEBHOOK_SECRET` value |
| Events | Just the push event |

GitHub sends a `ping` on save — a green check there means the signature and
URL are right.

No GitHub Actions secret is needed: the workflow pushes `deploy` with the
built-in `GITHUB_TOKEN`. It does need **Settings → Actions → General →
Workflow permissions → Read and write**, or the publish step 403s.

### 5. Rebuild the data cache

```
python -m backend.scripts.refresh_cache
```

Deploys ship **code, not data** (see [What a deploy does NOT do](#what-a-deploy-does-not-do)).
Any change to how upstream data is parsed or classified keeps serving the old
cached values until this runs — which looks exactly like the fix having
failed. Do it once at cutover; the nightly cron
([deploy-cpanel.md](deploy-cpanel.md) step 9) covers it from then on.

### 6. Verify

```
curl -H "Authorization: Bearer $DEPLOY_WEBHOOK_SECRET" \
     https://deciduous.mikkelsen.ca/api/deploy/status
```

`null` is correct before the first webhook-driven deploy — it means the routes
are live and authenticating, with no run recorded yet. A 503 means the secret
isn't set (or the app wasn't restarted); a 403 means the token doesn't match.

That's it. The Action ships with the repo, so the next merge to `main` deploys
itself.

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
