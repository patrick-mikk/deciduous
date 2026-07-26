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

        if new_sha == old_sha:
            state["status"] = "up-to-date"
            return state

        if not step("reset", ["git", "reset", "--hard", f"origin/{branch}"])[0]:
            return state

        ok, changed = step(
            "changed-files", ["git", "diff", "--name-only", old_sha, new_sha]
        )
        if ok and "backend/requirements.txt" in changed.splitlines():
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
