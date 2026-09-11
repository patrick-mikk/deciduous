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
without a prompt. The repo is **public**, so a plain HTTPS remote fetches
unauthenticated and no token is needed:

```
cd ~/deciduous
rm -rf frontend/dist
git remote set-url origin https://github.com/patrick-mikk/deciduous.git
git fetch origin deploy
git checkout deploy
```

(If the repo is ever made private, swap in a fine-grained **read-only** PAT —
Contents: Read — as `https://<TOKEN>@github.com/...`. It sits in plaintext in
`.git/config`, so read-only genuinely matters.)

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

**Do this before the first push to `main`.** New repos default to `read`, and
the failure is easy to misread: backend tests and the frontend build all go
green and only the final `Force-push deploy branch` step fails, with a bare
`Process completed with exit code 128` and no mention of permissions. Verify
with:

```
$ gh api repos/<owner>/<repo>/actions/permissions/workflow
```

`default_workflow_permissions` must be `write`. After fixing it, the failed run
can simply be re-run (`gh run rerun <id> --failed`) — no new commit is needed to
publish `deploy`.

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

- **Deploy** = merge/push to `main`. Nothing else. It lands within ~5
  minutes (webhook immediately, poller as the backstop).
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

## Cron poller (installed, and load-bearing on LiteSpeed)

The same runner works as a poller. **On this host it is the primary trigger,
not a fallback**, because the webhook's 202 does not guarantee a deploy — see
[Why the webhook alone isn't enough](#why-the-webhook-alone-isnt-enough).
It is installed:

Use the app's **virtualenv** interpreter (not the system `python3`) so the
deploy's `pip install` and schema step target the same environment the app
imports from — the exact path is shown at the top of cPanel → Setup Python App
(`docs/deploy-cpanel.md` step 9 makes the same point for the cache cron):

```
*/5 * * * * cd /home/cpaneluser/deciduous && /home/cpaneluser/virtualenv/deciduous/3.12/bin/python -m backend.scripts.deploy --if-changed >> /home/cpaneluser/deciduous-data/deploy-cron.log 2>&1
```

`--if-changed` is silent when already up to date, so the log only ever grows
on a real deploy. Absolute paths throughout, and the `cd` matters for the same
reason as the cache cron — `python -m backend.scripts...` resolves `backend`
from the working directory. The runner calls `load_env()` itself, so DB
credentials in `~/deciduous/.env` are picked up even though cron doesn't inherit
the Passenger app's environment.

An unchanged poll must stay a true no-op. The short-circuit persists
`status: "up-to-date"`, so that status has to count as a prior success — when
only `"deployed"` did, every *other* tick failed the check and ran a full
redeploy, restarting Passenger every 10 minutes forever
(`backend/tests/test_deploy.py::test_up_to_date_prior_does_not_trigger_a_redeploy`).

The lock file (`backend/instance/deploy.lock`) keeps cron and webhook deploys
from overlapping; a lock older than 15 minutes is treated as stale and broken.

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
- A trigger dies *after* taking the lock → every later trigger reports `locked`
  until the lock goes stale, which is longer than you'd guess: see
  [When `locked` is a lie](#when-locked-is-a-lie).

## Why the webhook alone isn't enough

On this cPanel host the web app runs under LiteSpeed's `lswsgi`, which reaps the
worker process as soon as the response is written. The webhook therefore cannot
do the deploy "after replying" inside its own process: the original
implementation started a `threading.Thread(daemon=True)`, returned 202, and the
thread was killed with the interpreter *microseconds later* — it died inside
`_acquire_lock` between `os.open` and `os.write`, leaving a **0-byte lock file**,
no state, and `origin/deploy` never even fetched. GitHub showed a green 202
delivery for a deploy that never happened, which is the worst possible failure
mode: silent and confidently reported as success.

`spawn_detached` (`backend/scripts/deploy.py`) fixes the mechanism — the deploy
runs in a child process with `start_new_session=True`, so it outlives both the
worker reap and the Passenger restart it triggers as its own last step.

Keep the cron poller anyway. It is the only trigger that doesn't depend on the
web app being up: if the app is down, a bad deploy is exactly when you most need
the next deploy to land, and a webhook into a dead app delivers nothing. Belt
and braces — the poller is a no-op when the webhook already did the work.

## When `locked` is a lie

`_LOCK_STALE_AFTER` is 15 minutes and the poller runs every 5, so a trigger that
dies while holding the lock silently swallows **three consecutive polls**. The
log says `"status": "locked", "detail": "Another deploy is in progress."` about a
deploy that is not in progress and never will be.

That asymmetry nearly stopped the `spawn_detached` fix from shipping at all. The
old thread-based code on the server took a lock, died, and the lock blocked the
poller — so the deploy carrying the fix *for that exact bug* couldn't land. It is
a genuine bootstrap deadlock, and breaking it took one manual intervention:

```
cd ~/deciduous
cat backend/instance/deploy.lock                      # the holder's PID
ps -p "$(cat backend/instance/deploy.lock)"           # alive? then leave it alone
unlink backend/instance/deploy.lock                   # only if it is dead
/home/cpaneluser/virtualenv/deciduous/3.12/bin/python -m backend.scripts.deploy
```

**A 0-byte lock file is always a dead one.** The PID is written immediately after
the file is created (`_acquire_lock`), so an empty lock means the holder was
killed in the microseconds between the two — which is the signature of the
`lswsgi` worker reap described above, not of a slow deploy.

Check the holder before removing a lock. A real deploy can legitimately hold it
for minutes (a `pip install` of the full requirements file is the slow step), and
deleting it mid-flight lets a second deploy `git reset` the tree under the first.

This should now be self-correcting — the detached child no longer dies and
releases the lock in its `finally` — so a `locked` poll with nothing running is
worth treating as a signal that something new is wrong, not as routine.

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
