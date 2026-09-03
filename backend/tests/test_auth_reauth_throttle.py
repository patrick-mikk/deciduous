"""Regression tests for the re-auth lockout and the reset-email throttle.

Both close gaps where holding a session cookie (or knowing an address) gave
an attacker something unlimited:

- `change_password`, `recovery-code`, `delete_account` and passkey
  registration all re-ask for the password precisely because they are what a
  stolen session shouldn't be able to do — but they verified with a bare
  `bcrypt.checkpw`, never consulting `locked_until` or incrementing
  `failed_login_attempts`. `signin` has enforced that lockout all along, so
  the re-auth prompt was a strictly easier oracle than the front door.
- `POST /api/auth/reset` without a recovery code is unauthenticated and each
  call spawns a daemon SMTP thread with a 20s timeout, so an unthrottled loop
  both mail-bombs the address and exhausts threads in the Passenger worker.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest  # noqa: E402

from backend.api.auth import _MAX_FAILED_ATTEMPTS  # noqa: E402
from backend.app import create_app  # noqa: E402
from backend.config_app import Config  # noqa: E402
from backend.mailer import outbox  # noqa: E402


class _TestConfig(Config):
    def __init__(self) -> None:
        super().__init__()
        self.SQLALCHEMY_DATABASE_URI = "sqlite://"
        self.IS_SQLITE_FALLBACK = True
        self.TESTING = True
        self.SECRET_KEY = "test-secret-key"
        self.DATA_KEY_PEPPER = "test-pepper"
        self.SESSION_COOKIE_SECURE = False


@pytest.fixture()
def client():
    return create_app(config=_TestConfig()).test_client()


_EMAIL = "student@mail.utoronto.ca"
_PASSWORD = "correcthorsebattery"


def _csrf(client) -> dict:
    return {"X-CSRF-Token": client.get("/api/auth/csrf").get_json()["csrfToken"]}


def _signup(client) -> None:
    resp = client.post(
        "/api/auth/signup", json={"email": _EMAIL, "password": _PASSWORD}, headers=_csrf(client)
    )
    assert resp.status_code == 201, resp.get_data(as_text=True)


def _guess(client, path: str, body: dict, method: str = "POST") -> int:
    fn = client.delete if method == "DELETE" else client.post
    return fn(path, json=body, headers=_csrf(client)).status_code


# ------------------------------------------------------------ re-auth lockout


@pytest.mark.parametrize(
    "path,body_key,extra,method",
    [
        ("/api/auth/change-password", "currentPassword", {"newPassword": "anotherlongpassword"}, "POST"),
        ("/api/auth/recovery-code", "password", {}, "POST"),
        ("/api/auth/account", "password", {}, "DELETE"),
    ],
)
def test_password_reauth_locks_out_after_repeated_wrong_guesses(client, path, body_key, extra, method):
    _signup(client)

    for _ in range(_MAX_FAILED_ATTEMPTS):
        assert _guess(client, path, {body_key: "wrong-password", **extra}, method) == 401

    # The next attempt is refused by the lockout, not by bcrypt -- 429, and
    # crucially the CORRECT password is refused too, which is what proves the
    # attempt was never evaluated.
    assert _guess(client, path, {body_key: "wrong-password", **extra}, method) == 429
    assert _guess(client, path, {body_key: _PASSWORD, **extra}, method) == 429


def test_successful_reauth_clears_the_failure_count(client):
    """A near-miss streak must not leave the account primed to lock on one
    later typo — `signin` resets on success and re-auth has to match."""
    _signup(client)

    for _ in range(_MAX_FAILED_ATTEMPTS - 1):
        assert _guess(client, "/api/auth/recovery-code", {"password": "wrong-password"}) == 401

    assert _guess(client, "/api/auth/recovery-code", {"password": _PASSWORD}) == 200

    # Counter reset: a fresh wrong guess is an ordinary 401, not the lockout.
    assert _guess(client, "/api/auth/recovery-code", {"password": "wrong-password"}) == 401


def test_lockout_from_reauth_also_blocks_the_front_door(client):
    """One shared counter — guessing via the re-auth prompt must not leave
    `signin` wide open (and vice versa)."""
    _signup(client)
    for _ in range(_MAX_FAILED_ATTEMPTS):
        assert _guess(client, "/api/auth/account", {"password": "wrong-password"}, "DELETE") == 401

    resp = client.post(
        "/api/auth/signin", json={"email": _EMAIL, "password": _PASSWORD}, headers=_csrf(client)
    )
    assert resp.status_code == 429


# ------------------------------------------------------- reset email throttle


def test_reset_email_is_throttled_per_account(client):
    _signup(client)
    outbox.clear()

    for _ in range(5):
        resp = client.post("/api/auth/reset", json={"email": _EMAIL}, headers=_csrf(client))
        # Always 202: the response must not reveal whether mail actually went
        # out, or the throttle becomes an account-existence oracle.
        assert resp.status_code == 202

    assert len(outbox) == 1, f"expected one throttled send, got {len(outbox)}"


def test_reset_email_for_an_unknown_address_still_looks_identical(client):
    outbox.clear()
    resp = client.post(
        "/api/auth/reset", json={"email": "nobody@mail.utoronto.ca"}, headers=_csrf(client)
    )
    assert resp.status_code == 202
    assert outbox == []
