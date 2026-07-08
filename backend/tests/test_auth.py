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
