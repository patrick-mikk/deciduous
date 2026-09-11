"""Self-update the deployed app from GitHub — no SSH needed.

The actual update logic behind `POST /api/deploy/webhook` / `/api/deploy/run`
(`backend/api/deploy.py`) and the cron fallback. One deploy:

1. Take the lock (a stale lock older than 15 min is broken — a crashed deploy
   must not wedge updates forever).
2. `git fetch origin <branch>`; if `origin/<branch>` == current HEAD, report
   `up-to-date` and stop.
3. `git reset --hard origin/<branch>` — the server checkout is a pure mirror
   of the deploy branch (built by `.github/workflows/deploy-branch.yml`,
   which includes `frontend/dist`); it must never carry local edits.
   Untracked files (`.env`, `backend/instance/`, caches) are untouched — no
   `git clean` on purpose.
4. If `backend/requirements.txt` changed between the two SHAs:
   `pip install -r backend/requirements.txt`.
5. If MySQL is configured (`DB_HOST`/`DB_NAME`/`DB_USER` set): run
   `python -m backend.scripts.init_db` in a subprocess, so the schema step
   executes against the NEW code just written to disk.
6. `touch <repo>/tmp/restart.txt` — Passenger's restart signal, so the next
   request boots the new code.

Result (status + per-step output) is persisted to
`backend/instance/last-deploy.json` for `GET /api/deploy/status`.

CLI (for the cron fallback when a webhook can't be configured)::

    */5 * * * * cd ~/deciduous && python -m backend.scripts.deploy --if-changed

`--if-changed` exits quietly when already up to date, so the cron log stays
readable. Exit code 0 = deployed or up-to-date, 1 = failed/locked.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
_INSTANCE_DIR = REPO_ROOT / "backend" / "instance"
STATE_PATH = _INSTANCE_DIR / "last-deploy.json"
LOCK_PATH = _INSTANCE_DIR / "deploy.lock"
LOG_PATH = _INSTANCE_DIR / "deploy.log"
RESTART_PATH = REPO_ROOT / "tmp" / "restart.txt"

_LOCK_STALE_AFTER = 15 * 60  # seconds
_STEP_TIMEOUT = 600  # seconds per subprocess


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _run(argv: list[str], timeout: int = _STEP_TIMEOUT) -> tuple[bool, str]:
    """Run one subprocess in the repo root; (ok, combined output)."""
    try:
        proc = subprocess.run(
            argv,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"{type(exc).__name__}: {exc}"
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0, output.strip()


def _acquire_lock() -> bool:
    _INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        try:
            age = dt.datetime.now().timestamp() - LOCK_PATH.stat().st_mtime
        except OSError:
            return False
        if age < _LOCK_STALE_AFTER:
            return False
        # Stale lock from a crashed deploy — break it and take over.
        try:
            LOCK_PATH.unlink()
            fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except OSError:
            return False
    os.write(fd, str(os.getpid()).encode("ascii"))
    os.close(fd)
    return True


def _release_lock() -> None:
    try:
        LOCK_PATH.unlink()
    except OSError:
        pass


def _write_state(state: dict) -> None:
    _INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def read_state() -> dict | None:
    """Last persisted deploy result, or None if no deploy has run yet."""
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def spawn_detached(branch: str) -> None:
    """Start a deploy in a *detached child process* and return immediately.

    The web path cannot use a background thread. Under LiteSpeed's `lswsgi` the
    worker is reaped as soon as the response is written, and a
    `threading.Thread(daemon=True)` is killed with the interpreter — observed
    dying inside `_acquire_lock` between `os.open` and `os.write`, leaving a
    0-byte lock file and no state behind, so the deploy never ran at all while
    the webhook happily returned 202.

    `start_new_session=True` puts the deploy in its own session, so it survives
    both that reap and the Passenger restart the deploy itself triggers as its
    final step. Output goes to `backend/instance/deploy.log`; the machine-
    readable result still lands in `last-deploy.json` for `/api/deploy/status`.
    """
    _INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "ab") as log:
        subprocess.Popen(  # noqa: S603 — fixed argv, no shell
            [sys.executable, "-m", "backend.scripts.deploy", "--branch", branch],
            cwd=REPO_ROOT,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            start_new_session=True,
            close_fds=True,
        )


def run_deploy(branch: str) -> dict:
    """Execute one deploy of `origin/<branch>`. Returns (and persists) the
    result dict: `{status, fromSha, toSha, startedAt, finishedAt, steps}`,
    with `status` one of `deployed | up-to-date | failed | locked`.

    Never raises — every failure lands in the result. Safe to call from a
    webhook thread or the CLI; the lock serializes concurrent callers.
    """
    if not _acquire_lock():
        return {"status": "locked", "startedAt": _now_iso(), "steps": [], "detail": "Another deploy is in progress."}

    steps: list[dict] = []
    state: dict = {"status": "failed", "branch": branch, "startedAt": _now_iso(), "steps": steps}

    def step(name: str, argv: list[str]) -> tuple[bool, str]:
        ok, output = _run(argv)
        steps.append({"name": name, "ok": ok, "output": output[-4000:]})
        return ok, output

    # Populate os.environ from .env for the CLI/cron path (the webhook path's
    # Flask process already did this in create_app). Without it, the DB_* gate
    # below reads empty and the schema step is silently skipped under cron.
    try:
        from backend.config import load_env

        load_env()
    except Exception:  # noqa: BLE001 — .env is optional; missing it is fine
        pass

    prior = read_state()

    try:
        ok, old_sha = step("current-sha", ["git", "rev-parse", "HEAD"])
        if not ok:
            return state
        state["fromSha"] = old_sha

        if not step("fetch", ["git", "fetch", "origin", branch])[0]:
            return state

        ok, new_sha = step("remote-sha", ["git", "rev-parse", f"origin/{branch}"])
        if not ok:
            return state
        state["toSha"] = new_sha

        # Short-circuit ONLY when the checkout is already at the target AND the
        # last deploy of exactly this SHA already SUCCEEDED. A deploy that died
        # after `git reset` (HEAD already == origin) but before restart must
        # still be retryable — otherwise every retry would report up-to-date
        # and never run pip/schema/restart. All post-reset steps are idempotent.
        #
        # "up-to-date" counts as success: it is only ever written *after* a
        # "deployed" run of this same SHA, so the chain stays anchored on a real
        # deploy. Accepting only "deployed" made the poller oscillate — the
        # short-circuit persists status="up-to-date", which then failed this
        # check on the next tick and forced a full redeploy (schema step and a
        # Passenger restart) every other run, forever. A genuinely interrupted
        # deploy leaves "failed" and is still retried.
        already_deployed = bool(
            prior
            and prior.get("status") in ("deployed", "up-to-date")
            and prior.get("toSha") == new_sha
        )
        if new_sha == old_sha and already_deployed:
            state["status"] = "up-to-date"
            return state

        if not step("reset", ["git", "reset", "--hard", f"origin/{branch}"])[0]:
            return state

        # Compare against the pre-reset SHA so a resumed/retried deploy (where
        # old_sha already == new_sha) still re-checks requirements. `prior`'s
        # fromSha is the true previous baseline in that case.
        base_sha = old_sha if old_sha != new_sha else (prior or {}).get("fromSha", old_sha)
        ok, changed = step("changed-files", ["git", "diff", "--name-only", base_sha, new_sha])
        if not ok or "backend/requirements.txt" in changed.splitlines():
            if not step(
                "pip-install",
                [sys.executable, "-m", "pip", "install", "-r", "backend/requirements.txt"],
            )[0]:
                return state

        # Schema step runs as a subprocess so it imports the NEW code. Only
        # meaningful against MySQL — the SQLite dev fallback migrates itself
        # on boot (backend/app.py), and init_db refuses it by design.
        if all(os.environ.get(k) for k in ("DB_HOST", "DB_NAME", "DB_USER")):
            if not step("init-db", [sys.executable, "-m", "backend.scripts.init_db"])[0]:
                return state
        else:
            steps.append(
                {"name": "init-db", "ok": True, "output": "skipped: DB_HOST/DB_NAME/DB_USER not set (SQLite fallback self-migrates on boot)"}
            )

        try:
            RESTART_PATH.parent.mkdir(parents=True, exist_ok=True)
            RESTART_PATH.touch()
            steps.append({"name": "passenger-restart", "ok": True, "output": str(RESTART_PATH)})
        except OSError as exc:
            steps.append({"name": "passenger-restart", "ok": False, "output": str(exc)})
            return state

        state["status"] = "deployed"
        return state
    finally:
        state["finishedAt"] = _now_iso()
        try:
            _write_state(state)
        except OSError:
            pass
        _release_lock()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pull and deploy the latest origin/<branch>.")
    parser.add_argument("--branch", default=os.environ.get("DEPLOY_BRANCH", "deploy"))
    parser.add_argument(
        "--if-changed",
        action="store_true",
        help="Print nothing when already up to date (cron mode).",
    )
    args = parser.parse_args(argv)

    result = run_deploy(args.branch)
    if result["status"] == "up-to-date" and args.if_changed:
        return 0
    print(json.dumps(result, indent=2))
    return 0 if result["status"] in ("deployed", "up-to-date") else 1


if __name__ == "__main__":
    raise SystemExit(main())
