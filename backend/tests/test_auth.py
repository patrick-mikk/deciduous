"""Exercises the auth blueprint end-to-end against an isolated in-memory DB:
signup -> whoami -> signout, wrong-password rejection, duplicate-email
rejection, CSRF enforcement, and that the data key round-trips (proving
crypto.wrap_data_key/unwrap_data_key are wired correctly through signup/signin).
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest  # noqa: E402

from backend.app import create_app  # noqa: E402
from backend.config_app import Config  # noqa: E402


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
    app = create_app(config=_TestConfig())
    return app.test_client()


def _csrf_headers(client) -> dict:
    resp = client.get("/api/auth/csrf")
    token = resp.get_json()["csrfToken"]
    return {"X-CSRF-Token": token}


def test_signup_requires_csrf_token(client):
    resp = client.post("/api/auth/signup", json={"email": "a@b.com", "password": "correcthorsebattery"})
    assert resp.status_code == 403


def test_signup_then_whoami_then_signout(client):
    headers = _csrf_headers(client)
    resp = client.post(
        "/api/auth/signup",
        json={"email": "student@mail.utoronto.ca", "password": "correcthorsebattery"},
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["user"]["email"] == "student@mail.utoronto.ca"

    who = client.get("/api/auth/session")
    assert who.status_code == 200
    assert who.get_json()["user"]["email"] == "student@mail.utoronto.ca"

    headers = _csrf_headers(client)
    out = client.post("/api/auth/signout", headers=headers)
    assert out.status_code == 200

    who_after = client.get("/api/auth/session")
    assert who_after.status_code == 401


def test_signup_rejects_duplicate_email(client):
    headers = _csrf_headers(client)
    client.post(
        "/api/auth/signup",
        json={"email": "dup@mail.utoronto.ca", "password": "correcthorsebattery"},
        headers=headers,
    )
    headers = _csrf_headers(client)
    resp = client.post(
        "/api/auth/signup",
        json={"email": "dup@mail.utoronto.ca", "password": "anotherlongpassword"},
        headers=headers,
    )
    assert resp.status_code == 409


def test_signin_wrong_password_is_rejected_without_leaking_which_field(client):
    headers = _csrf_headers(client)
    client.post(
        "/api/auth/signup",
        json={"email": "wrongpw@mail.utoronto.ca", "password": "correcthorsebattery"},
        headers=headers,
    )
    headers = _csrf_headers(client)
    client.post("/api/auth/signout", headers=headers)

    headers = _csrf_headers(client)
    resp = client.post(
        "/api/auth/signin",
        json={"email": "wrongpw@mail.utoronto.ca", "password": "totallywrongpassword"},
        headers=headers,
    )
    assert resp.status_code == 401
    assert resp.get_json()["error"] == "Incorrect email or password."


def test_signin_round_trips_the_data_key(client):
    email, password = "roundtrip@mail.utoronto.ca", "correcthorsebattery"
    headers = _csrf_headers(client)
    client.post("/api/auth/signup", json={"email": email, "password": password}, headers=headers)
    with client.session_transaction() as sess:
        original_key = sess["data_key"]

    headers = _csrf_headers(client)
    client.post("/api/auth/signout", headers=headers)

    headers = _csrf_headers(client)
    resp = client.post("/api/auth/signin", json={"email": email, "password": password}, headers=headers)
    assert resp.status_code == 200
    with client.session_transaction() as sess:
        assert sess["data_key"] == original_key


def test_signin_locks_out_after_too_many_failures(client):
    email, password = "lockout@mail.utoronto.ca", "correcthorsebattery"
    headers = _csrf_headers(client)
    client.post("/api/auth/signup", json={"email": email, "password": password}, headers=headers)
    headers = _csrf_headers(client)
    client.post("/api/auth/signout", headers=headers)

    for _ in range(8):
        headers = _csrf_headers(client)
        client.post("/api/auth/signin", json={"email": email, "password": "wrong"}, headers=headers)

    headers = _csrf_headers(client)
    resp = client.post("/api/auth/signin", json={"email": email, "password": password}, headers=headers)
    assert resp.status_code == 429


# --------------------------------------------------------------- remember me
def _signup(client, email, password="correcthorsebattery", **extra) -> None:
    headers = _csrf_headers(client)
    resp = client.post(
        "/api/auth/signup", json={"email": email, "password": password, **extra}, headers=headers
    )
    assert resp.status_code == 201, resp.get_json()


def _session_expiry_days(client, email) -> float:
    """Days until the newest active DB session row for `email` expires."""
    import datetime as dt

    from backend.extensions import get_session
    from backend.models_db import Session as SessionModel
    from backend.models_db import User

    with client.application.app_context():
        db = get_session()
        user = db.query(User).filter_by(email=email).one()
        row = (
            db.query(SessionModel)
            .filter_by(user_id=user.id, revoked_at=None)
            .order_by(SessionModel.created_at.desc())
            .first()
        )
        now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
        return (row.expires_at - now).total_seconds() / 86400


def test_default_session_expires_in_a_day(client):
    _signup(client, "shortsession@mail.utoronto.ca")
    assert _session_expiry_days(client, "shortsession@mail.utoronto.ca") < 1.1


def test_remember_me_session_expires_in_thirty_days(client):
    email, password = "remember@mail.utoronto.ca", "correcthorsebattery"
    _signup(client, email, password)
    headers = _csrf_headers(client)
    client.post("/api/auth/signout", headers=headers)

    headers = _csrf_headers(client)
    resp = client.post(
        "/api/auth/signin",
        json={"email": email, "password": password, "rememberMe": True},
        headers=headers,
    )
    assert resp.status_code == 200
    days = _session_expiry_days(client, email)
    assert 29.5 < days <= 30.0


# ----------------------------------------------------------------- sessions
def test_list_and_revoke_sessions(client):
    email, password = "sessions@mail.utoronto.ca", "correcthorsebattery"
    _signup(client, email, password)

    # A second sign-in (without signing out) leaves two active sessions.
    headers = _csrf_headers(client)
    client.post("/api/auth/signin", json={"email": email, "password": password}, headers=headers)

    resp = client.get("/api/auth/sessions")
    sessions = resp.get_json()["sessions"]
    assert len(sessions) == 2
    assert sum(1 for s in sessions if s["current"]) == 1

    headers = _csrf_headers(client)
    resp = client.post("/api/auth/sessions/revoke-others", headers=headers)
    assert resp.status_code == 200
    sessions = client.get("/api/auth/sessions").get_json()["sessions"]
    assert len(sessions) == 1 and sessions[0]["current"]

    # Revoking the current session signs the caller out.
    headers = _csrf_headers(client)
    resp = client.delete(f"/api/auth/sessions/{sessions[0]['id']}", headers=headers)
    assert resp.status_code == 200
    assert client.get("/api/auth/session").status_code == 401


def test_cannot_revoke_someone_elses_session(client):
    _signup(client, "victim@mail.utoronto.ca")
    victim_sessions = client.get("/api/auth/sessions").get_json()["sessions"]
    headers = _csrf_headers(client)
    client.post("/api/auth/signout", headers=headers)

    _signup(client, "attacker@mail.utoronto.ca")
    headers = _csrf_headers(client)
    resp = client.delete(f"/api/auth/sessions/{victim_sessions[0]['id']}", headers=headers)
    assert resp.status_code == 404


# ---------------------------------------------------------- change password
def test_change_password_rewraps_data_key(client):
    email, old_pw, new_pw = "changepw@mail.utoronto.ca", "correcthorsebattery", "an-even-better-pass"
    _signup(client, email, old_pw)
    with client.session_transaction() as sess:
        original_key = sess["data_key"]

    headers = _csrf_headers(client)
    resp = client.post(
        "/api/auth/change-password",
        json={"currentPassword": "wrong-password", "newPassword": new_pw},
        headers=headers,
    )
    assert resp.status_code == 401

    headers = _csrf_headers(client)
    resp = client.post(
        "/api/auth/change-password",
        json={"currentPassword": old_pw, "newPassword": new_pw},
        headers=headers,
    )
    assert resp.status_code == 200

    headers = _csrf_headers(client)
    client.post("/api/auth/signout", headers=headers)

    headers = _csrf_headers(client)
    assert (
        client.post(
            "/api/auth/signin", json={"email": email, "password": old_pw}, headers=headers
        ).status_code
        == 401
    )
    headers = _csrf_headers(client)
    resp = client.post("/api/auth/signin", json={"email": email, "password": new_pw}, headers=headers)
    assert resp.status_code == 200
    with client.session_transaction() as sess:
        assert sess["data_key"] == original_key  # same key, new wrap


# ------------------------------------------------------- recovery code flow
def test_recovery_code_reset_preserves_data_key(client):
    email, old_pw, new_pw = "recovery@mail.utoronto.ca", "correcthorsebattery", "brand-new-password1"
    _signup(client, email, old_pw)
    with client.session_transaction() as sess:
        original_key = sess["data_key"]

    headers = _csrf_headers(client)
    resp = client.post("/api/auth/recovery-code", headers=headers)
    assert resp.status_code == 200
    code = resp.get_json()["recoveryCode"]
    assert len(code.replace("-", "")) == 16

    headers = _csrf_headers(client)
    client.post("/api/auth/signout", headers=headers)

    # Wrong code is rejected generically.
    headers = _csrf_headers(client)
    resp = client.post(
        "/api/auth/reset",
        json={"email": email, "recoveryCode": "AAAA-BBBB-CCCC-DDDD", "newPassword": new_pw},
        headers=headers,
    )
    assert resp.status_code == 401

    headers = _csrf_headers(client)
    resp = client.post(
        "/api/auth/reset",
        json={"email": email, "recoveryCode": code.lower(), "newPassword": new_pw},
        headers=headers,
    )
    assert resp.status_code == 200
    with client.session_transaction() as sess:
        assert sess["data_key"] == original_key  # data survived the reset

    headers = _csrf_headers(client)
    client.post("/api/auth/signout", headers=headers)
    headers = _csrf_headers(client)
    resp = client.post("/api/auth/signin", json={"email": email, "password": new_pw}, headers=headers)
    assert resp.status_code == 200


def test_reset_without_code_stays_a_stub(client):
    headers = _csrf_headers(client)
    resp = client.post("/api/auth/reset", json={"email": "whoever@x.com"}, headers=headers)
    assert resp.status_code == 202


# ----------------------------------------------------------- delete account
def test_delete_account_requires_password_and_cascades(client):
    email, password = "deleteme@mail.utoronto.ca", "correcthorsebattery"
    _signup(client, email, password)

    headers = _csrf_headers(client)
    resp = client.delete("/api/auth/account", json={"password": "wrong"}, headers=headers)
    assert resp.status_code == 401

    headers = _csrf_headers(client)
    resp = client.delete("/api/auth/account", json={"password": password}, headers=headers)
    assert resp.status_code == 200
    assert client.get("/api/auth/session").status_code == 401

    headers = _csrf_headers(client)
    resp = client.post("/api/auth/signin", json={"email": email, "password": password}, headers=headers)
    assert resp.status_code == 401  # account is gone


# ------------------------------------------------------------------ profile
def test_profile_roundtrip_and_validation(client):
    _signup(client, "profile@mail.utoronto.ca")

    resp = client.get("/api/me/profile")
    assert resp.status_code == 200
    profile = resp.get_json()["profile"]
    assert profile["email"] == "profile@mail.utoronto.ca"
    assert profile["displayName"] == ""

    headers = _csrf_headers(client)
    resp = client.put(
        "/api/me/profile",
        json={"displayName": "Priya Sharma", "currentSession": "20269", "expectedGrad": "2027-06"},
        headers=headers,
    )
    assert resp.status_code == 200
    profile = resp.get_json()["profile"]
    assert profile["displayName"] == "Priya Sharma"
    assert profile["currentSession"] == "20269"
    assert profile["expectedGrad"] == "2027-06"

    # Partial update leaves other fields alone.
    headers = _csrf_headers(client)
    resp = client.put("/api/me/profile", json={"displayName": "Priya"}, headers=headers)
    assert resp.get_json()["profile"]["currentSession"] == "20269"

    headers = _csrf_headers(client)
    assert (
        client.put("/api/me/profile", json={"currentSession": "Fall 2026"}, headers=headers).status_code
        == 422
    )
    headers = _csrf_headers(client)
    assert client.put("/api/me/profile", json={"expectedGrad": "June 2027"}, headers=headers).status_code == 422
