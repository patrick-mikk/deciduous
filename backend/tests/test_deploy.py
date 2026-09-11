"""Deploy webhook/API tests. The process spawn
(`backend/scripts/deploy.py::spawn_detached`) is monkeypatched — these tests
cover everything in front of it: HMAC signature verification, event/branch
filtering, Bearer auth on the manual/status routes, the off-by-default 503
when no secret is configured, and CSRF exemption of the webhook path.

`run_deploy`'s own short-circuit logic is covered separately at the bottom.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest  # noqa: E402

import backend.api.deploy as deploy_api  # noqa: E402
from backend.app import create_app  # noqa: E402
from backend.config_app import Config  # noqa: E402

_SECRET = "test-deploy-secret"


class _TestConfig(Config):
    def __init__(self) -> None:
        super().__init__()
        self.SQLALCHEMY_DATABASE_URI = "sqlite://"
        self.IS_SQLITE_FALLBACK = True
        self.TESTING = True
        self.SECRET_KEY = "test-secret-key"
        self.DATA_KEY_PEPPER = "test-pepper"
        self.SESSION_COOKIE_SECURE = False
        self.DEPLOY_WEBHOOK_SECRET = _SECRET
        self.DEPLOY_BRANCH = "deploy"


@pytest.fixture()
def client():
    return create_app(config=_TestConfig()).test_client()


@pytest.fixture()
def deploys(monkeypatch):
    """Capture spawn_detached calls instead of forking a real deploy.

    The spawn is synchronous (it only starts a child), so the recorded calls are
    visible as soon as the request returns; `wait_for`'s signature is kept so
    the assertions below read unchanged.
    """
    calls: list[str] = []
    monkeypatch.setattr(deploy_api, "spawn_detached", calls.append)

    def wait_for(n: int, timeout: float = 2.0) -> list[str]:
        deadline = time.monotonic() + timeout
        while len(calls) < n and time.monotonic() < deadline:
            time.sleep(0.01)
        return calls

    return wait_for


def _signed_headers(body: bytes, event: str = "push", secret: str = _SECRET) -> dict:
    signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return {
        "X-Hub-Signature-256": signature,
        "X-GitHub-Event": event,
        "Content-Type": "application/json",
    }


def _push_body(ref: str = "refs/heads/deploy") -> bytes:
    return json.dumps({"ref": ref}).encode()


def test_webhook_deploys_on_push_to_deploy_branch(client, deploys):
    body = _push_body()
    resp = client.post("/api/deploy/webhook", data=body, headers=_signed_headers(body))
    assert resp.status_code == 202
    assert resp.get_json()["deploying"] == "deploy"
    assert deploys(1) == ["deploy"]


def test_webhook_rejects_bad_signature(client, deploys):
    body = _push_body()
    resp = client.post(
        "/api/deploy/webhook", data=body, headers=_signed_headers(body, secret="wrong-secret")
    )
    assert resp.status_code == 403
    assert deploys(0, timeout=0.2) == []


def test_webhook_rejects_missing_signature(client):
    resp = client.post("/api/deploy/webhook", data=_push_body(), headers={"X-GitHub-Event": "push"})
    assert resp.status_code == 403


def test_webhook_ignores_other_branches(client, deploys):
    body = _push_body("refs/heads/main")
    resp = client.post("/api/deploy/webhook", data=body, headers=_signed_headers(body))
    assert resp.status_code == 200
    assert "ignored" in resp.get_json()
    assert deploys(0, timeout=0.2) == []


def test_webhook_answers_ping(client):
    body = b"{}"
    resp = client.post("/api/deploy/webhook", data=body, headers=_signed_headers(body, event="ping"))
    assert resp.status_code == 200
    assert resp.get_json()["pong"] is True


def test_webhook_ignores_non_push_events(client, deploys):
    body = _push_body()
    resp = client.post("/api/deploy/webhook", data=body, headers=_signed_headers(body, event="issues"))
    assert resp.status_code == 200
    assert deploys(0, timeout=0.2) == []


def test_manual_run_requires_bearer_secret(client, deploys):
    resp = client.post("/api/deploy/run")
    assert resp.status_code == 403
    resp = client.post("/api/deploy/run", headers={"Authorization": "Bearer nope"})
    assert resp.status_code == 403

    resp = client.post("/api/deploy/run", headers={"Authorization": f"Bearer {_SECRET}"})
    assert resp.status_code == 202
    assert deploys(1) == ["deploy"]


def test_non_ascii_signature_is_403_not_500(client, deploys):
    # A header byte > 0x7F would make compare_digest raise TypeError; the fix
    # compares bytes, so it cleanly rejects instead of 500ing this
    # unauthenticated route.
    body = _push_body()
    resp = client.post(
        "/api/deploy/webhook",
        data=body,
        headers={"X-Hub-Signature-256": "sha256=café", "X-GitHub-Event": "push", "Content-Type": "application/json"},
    )
    assert resp.status_code == 403
    resp = client.post("/api/deploy/run", headers={"Authorization": "Bearer café"})
    assert resp.status_code == 403


def test_status_requires_bearer_secret(client, monkeypatch):
    monkeypatch.setattr(deploy_api, "read_state", lambda: {"status": "deployed"})
    assert client.get("/api/deploy/status").status_code == 403
    resp = client.get("/api/deploy/status", headers={"Authorization": f"Bearer {_SECRET}"})
    assert resp.status_code == 200
    assert resp.get_json()["lastDeploy"]["status"] == "deployed"


def test_everything_503s_without_a_configured_secret():
    class _NoSecretConfig(_TestConfig):
        def __init__(self) -> None:
            super().__init__()
            self.DEPLOY_WEBHOOK_SECRET = None

    client = create_app(config=_NoSecretConfig()).test_client()
    body = _push_body()
    assert client.post("/api/deploy/webhook", data=body, headers=_signed_headers(body)).status_code == 503
    assert client.post("/api/deploy/run", headers={"Authorization": f"Bearer {_SECRET}"}).status_code == 503
    assert client.get("/api/deploy/status", headers={"Authorization": f"Bearer {_SECRET}"}).status_code == 503


# --- run_deploy short-circuit -------------------------------------------------
# Regression cover for the cron poller oscillating: the short-circuit persists
# status="up-to-date", so if only "deployed" counted as a prior success, every
# other tick did a full redeploy (schema step + Passenger restart) forever.


@pytest.fixture()
def no_side_effects(monkeypatch, tmp_path):
    """Run run_deploy against temp state with git/pip/restart stubbed out.

    Returns the list of step names each call actually executed, so a
    short-circuit ("no steps past remote-sha") is distinguishable from a full
    redeploy ("reset", "init-db", "passenger-restart").
    """
    from backend.scripts import deploy as runner

    monkeypatch.setattr(runner, "STATE_PATH", tmp_path / "last-deploy.json")
    monkeypatch.setattr(runner, "LOCK_PATH", tmp_path / "deploy.lock")
    monkeypatch.setattr(runner, "RESTART_PATH", tmp_path / "tmp" / "restart.txt")
    monkeypatch.setattr(runner, "_INSTANCE_DIR", tmp_path)
    # No DB env -> the schema step is recorded as skipped rather than run.
    for var in ("DB_HOST", "DB_NAME", "DB_USER"):
        monkeypatch.delenv(var, raising=False)

    sha = "a" * 40

    def _fake_run(argv, timeout=None):
        if argv[:2] == ["git", "rev-parse"]:
            return True, sha
        if argv[:2] == ["git", "diff"]:
            return True, ""
        return True, ""

    monkeypatch.setattr(runner, "_run", _fake_run)
    return runner, sha


def test_up_to_date_prior_does_not_trigger_a_redeploy(no_side_effects):
    """Two consecutive polls of an unchanged SHA: deploy once, then stay quiet.

    The third poll is the one that regressed — it saw status="up-to-date" and
    redeployed.
    """
    runner, _sha = no_side_effects

    first = runner.run_deploy("deploy")
    assert first["status"] == "deployed"

    for _ in range(3):
        again = runner.run_deploy("deploy")
        assert again["status"] == "up-to-date"
        step_names = [s["name"] for s in again["steps"]]
        assert "reset" not in step_names
        assert "passenger-restart" not in step_names


def test_failed_prior_is_still_retried(no_side_effects):
    """A deploy interrupted after `git reset` must not be mistaken for done."""
    runner, sha = no_side_effects
    runner._write_state({"status": "failed", "toSha": sha, "fromSha": sha})

    result = runner.run_deploy("deploy")
    assert result["status"] == "deployed"
    assert "passenger-restart" in [s["name"] for s in result["steps"]]
