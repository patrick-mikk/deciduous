"""Email verification + emailed password-reset flows, end-to-end against an
in-memory DB. `backend.mailer` captures messages to its `outbox` in TESTING
mode, so tests redeem the exact tokens a real user would receive — the token
is extracted from the rendered email body, not minted by the test.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest  # noqa: E402

from backend import mailer  # noqa: E402
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
        self.APP_BASE_URL = "https://deciduous.test"


@pytest.fixture()
def client():
    mailer.outbox.clear()
    app = create_app(config=_TestConfig())
    return app.test_client()


def _csrf_headers(client) -> dict:
    return {"X-CSRF-Token": client.get("/api/auth/csrf").get_json()["csrfToken"]}


def _signup(client, email, password="correcthorsebattery"):
    resp = client.post(
        "/api/auth/signup", json={"email": email, "password": password}, headers=_csrf_headers(client)
    )
    assert resp.status_code == 201, resp.get_json()


def _token_from_last_email(path_prefix: str) -> str:
    assert mailer.outbox, "expected an email in the TESTING outbox"
    body = mailer.outbox[-1].get_content()
    match = re.search(rf"https://deciduous\.test{path_prefix}\?token=([\w.\-_]+)", body)
    assert match, f"no {path_prefix} link found in email body:\n{body}"
    return match.group(1)


# ------------------------------------------------------------- verification
def test_signup_sends_verification_email_and_token_verifies(client):
    _signup(client, "verifyme@mail.utoronto.ca")
    assert mailer.outbox[-1]["To"] == "verifyme@mail.utoronto.ca"
    token = _token_from_last_email("/verify")

    who = client.get("/api/auth/session").get_json()["user"]
    assert who["verified"] is False

    resp = client.post("/api/auth/verify", json={"token": token}, headers=_csrf_headers(client))
    assert resp.status_code == 200
    assert resp.get_json()["email"] == "verifyme@mail.utoronto.ca"
    assert client.get("/api/auth/session").get_json()["user"]["verified"] is True
    assert client.get("/api/me/profile").get_json()["profile"]["verified"] is True


def test_verify_rejects_garbage_token(client):
    resp = client.post("/api/auth/verify", json={"token": "not-a-token"}, headers=_csrf_headers(client))
    assert resp.status_code == 401


def test_resend_verification(client):
    _signup(client, "resend@mail.utoronto.ca")
    sent_before = len(mailer.outbox)
    resp = client.post("/api/auth/verify/request", headers=_csrf_headers(client))
    assert resp.status_code == 200
    assert len(mailer.outbox) == sent_before + 1

    token = _token_from_last_email("/verify")
    client.post("/api/auth/verify", json={"token": token}, headers=_csrf_headers(client))
    resp = client.post("/api/auth/verify/request", headers=_csrf_headers(client))
    assert resp.get_json().get("alreadyVerified") is True


# ------------------------------------------------------------- email reset
def test_reset_request_emails_link_and_confirm_resets_password(client):
    email, old_pw, new_pw = "emailreset@mail.utoronto.ca", "correcthorsebattery", "a-whole-new-passw0rd"
    _signup(client, email, old_pw)
    client.post("/api/auth/signout", headers=_csrf_headers(client))

    resp = client.post("/api/auth/reset", json={"email": email}, headers=_csrf_headers(client))
    assert resp.status_code == 202
    token = _token_from_last_email("/reset")

    resp = client.post(
        "/api/auth/reset/confirm",
        json={"token": token, "newPassword": new_pw},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 200
    body = resp.get_json()
    # No passkey on this account -> the data key could not be preserved.
    assert body["dataPreserved"] is False
    # Redeeming the emailed link proves mailbox control -> verified.
    assert body["user"]["verified"] is True
    assert client.get("/api/auth/session").status_code == 200

    client.post("/api/auth/signout", headers=_csrf_headers(client))
    resp = client.post(
        "/api/auth/signin", json={"email": email, "password": new_pw}, headers=_csrf_headers(client)
    )
    assert resp.status_code == 200
    resp = client.post(
        "/api/auth/signin", json={"email": email, "password": old_pw}, headers=_csrf_headers(client)
    )
    assert resp.status_code == 401


def test_reset_request_for_unknown_email_still_202_and_sends_nothing(client):
    resp = client.post(
        "/api/auth/reset", json={"email": "nobody@mail.utoronto.ca"}, headers=_csrf_headers(client)
    )
    assert resp.status_code == 202
    assert mailer.outbox == []


def test_reset_confirm_preserves_data_key_when_account_has_a_passkey(client, monkeypatch):
    """With a passkey registered, `server_wrapped_data_key` exists, so an
    email reset recovers the SAME data key (encrypted rows stay readable)."""
    import backend.api.passkeys as passkeys_module
    from webauthn.helpers import bytes_to_base64url

    email, new_pw = "resetpasskey@mail.utoronto.ca", "a-whole-new-passw0rd"
    _signup(client, email)
    with client.session_transaction() as sess:
        original_key = sess["data_key"]

    class _Verified:
        credential_id = b"cred-reset-test"
        credential_public_key = b"pk"
        sign_count = 0

    client.post("/api/auth/passkeys/register/options", headers=_csrf_headers(client))
    monkeypatch.setattr(passkeys_module, "verify_registration_response", lambda **kw: _Verified())
    cred_b64 = bytes_to_base64url(b"cred-reset-test")
    resp = client.post(
        "/api/auth/passkeys/register/verify",
        json={"credential": {"id": cred_b64, "rawId": cred_b64}},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 201
    client.post("/api/auth/signout", headers=_csrf_headers(client))

    client.post("/api/auth/reset", json={"email": email}, headers=_csrf_headers(client))
    token = _token_from_last_email("/reset")
    resp = client.post(
        "/api/auth/reset/confirm",
        json={"token": token, "newPassword": new_pw},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 200
    assert resp.get_json()["dataPreserved"] is True
    with client.session_transaction() as sess:
        assert sess["data_key"] == original_key


def test_reset_confirm_rejects_expired_token(client, monkeypatch):
    email = "expired@mail.utoronto.ca"
    _signup(client, email)
    client.post("/api/auth/signout", headers=_csrf_headers(client))
    client.post("/api/auth/reset", json={"email": email}, headers=_csrf_headers(client))
    token = _token_from_last_email("/reset")

    import backend.api.auth as auth_module

    monkeypatch.setattr(auth_module, "_RESET_MAX_AGE", -1)  # everything is now expired
    resp = client.post(
        "/api/auth/reset/confirm",
        json={"token": token, "newPassword": "a-whole-new-passw0rd"},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 401
