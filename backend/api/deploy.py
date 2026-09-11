"""Deploy blueprint: GitHub-webhook-driven self-update (no SSH).

Routes (all gated by `DEPLOY_WEBHOOK_SECRET`; unset ⇒ every route 503s, so
the feature is off-by-default):

- `POST /api/deploy/webhook` — the GitHub webhook receiver. Authenticated by
  the `X-Hub-Signature-256` HMAC over the raw body (constant-time compare) —
  the exact scheme GitHub signs with when the webhook is configured with the
  same secret. Only a `push` to the configured `DEPLOY_BRANCH` triggers a
  deploy; everything else is acknowledged and ignored. The deploy itself
  (`backend/scripts/deploy.py`) runs in a *detached child process* and this
  responds 202 immediately — GitHub times webhooks out at 10s, a git+pip
  deploy can take longer. It must be a separate process, not a thread: see
  `spawn_detached`'s docstring for why a thread silently never runs here.
- `POST /api/deploy/run` — manual trigger for the same deploy, authenticated
  with `Authorization: Bearer <DEPLOY_WEBHOOK_SECRET>` (e.g. from `curl` or a
  phone, when you don't want to wait for a push).
- `GET /api/deploy/status` — last deploy's persisted result, same Bearer auth.

CSRF: the two POSTs are exempted from the app-wide double-submit guard
(`backend/app.py::_CSRF_EXEMPT_PATHS`) — GitHub can't play the cookie game;
the HMAC/Bearer secret is the (stronger) authentication here.

Setup: docs/auto-deploy.md.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets as _secrets

from flask import Blueprint, current_app, jsonify, request

from backend.api import json_error
from backend.scripts.deploy import read_state, spawn_detached

bp = Blueprint("deploy", __name__, url_prefix="/api/deploy")


def _secret() -> str | None:
    return current_app.config.get("DEPLOY_WEBHOOK_SECRET") or None


def _branch() -> str:
    return current_app.config.get("DEPLOY_BRANCH") or "deploy"


def _bearer_authorized() -> bool:
    secret = _secret()
    if not secret:
        return False
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return False
    # Compare as bytes: compare_digest raises TypeError on non-ASCII str
    # (Werkzeug decodes headers as latin-1), which would 500 an unauthenticated
    # route instead of cleanly rejecting.
    return _secrets.compare_digest(
        header[len("Bearer "):].strip().encode("utf-8", "ignore"), secret.encode("utf-8")
    )


def _start_background_deploy(branch: str) -> None:
    """Hand the deploy to a detached process; never blocks the request.

    Indirection kept so the routes read the same either way (and so tests have
    a single seam to patch). The result is not logged here — the child outlives
    this process, and records its own outcome in `last-deploy.json`.
    """
    current_app.logger.info("Deploy requested for branch %s", branch)
    spawn_detached(branch)


@bp.route("/webhook", methods=["POST"])
def webhook():
    secret = _secret()
    if not secret:
        return json_error("Auto-deploy is not configured (DEPLOY_WEBHOOK_SECRET unset).", 503)

    signature = request.headers.get("X-Hub-Signature-256", "")
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), request.get_data(), hashlib.sha256).hexdigest()
    # Byte compare: a non-ASCII signature header would make compare_digest raise
    # TypeError and 500 this unauthenticated route instead of returning 403.
    if not signature or not hmac.compare_digest(signature.encode("utf-8", "ignore"), expected.encode("utf-8")):
        return json_error("Invalid webhook signature.", 403)

    event = request.headers.get("X-GitHub-Event", "")
    if event == "ping":
        return jsonify({"ok": True, "pong": True})
    if event != "push":
        return jsonify({"ok": True, "ignored": f"event {event or '(none)'}"})

    payload = request.get_json(silent=True) or {}
    ref = payload.get("ref") or ""
    branch = _branch()
    if ref != f"refs/heads/{branch}":
        return jsonify({"ok": True, "ignored": f"push to {ref or '(unknown ref)'}, deploying only {branch}"})

    _start_background_deploy(branch)
    return jsonify({"ok": True, "deploying": branch}), 202


@bp.route("/run", methods=["POST"])
def run_now():
    if not _secret():
        return json_error("Auto-deploy is not configured (DEPLOY_WEBHOOK_SECRET unset).", 503)
    if not _bearer_authorized():
        return json_error("Invalid or missing deploy token.", 403)
    _start_background_deploy(_branch())
    return jsonify({"ok": True, "deploying": _branch()}), 202


@bp.route("/status", methods=["GET"])
def status():
    if not _secret():
        return json_error("Auto-deploy is not configured (DEPLOY_WEBHOOK_SECRET unset).", 503)
    if not _bearer_authorized():
        return json_error("Invalid or missing deploy token.", 403)
    return jsonify({"lastDeploy": read_state()})
