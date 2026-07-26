"""Passkey (WebAuthn) blueprint tests against an isolated in-memory DB.

The actual cryptographic ceremony verification belongs to the `webauthn`
library (tested upstream); here its `verify_registration_response` /
`verify_authentication_response` are monkeypatched with stubs so the tests
exercise everything AROUND the ceremony: challenge bookkeeping, credential
storage, the server-wrapped data key lifecycle (ADR-0006), ownership checks,
and that a passkey sign-in yields a working session whose data key matches
the one from the password sign-up.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest  # noqa: E402
from webauthn.helpers import bytes_to_base64url  # noqa: E402
from webauthn.helpers.exceptions import (  # noqa: E402
    InvalidAuthenticationResponse,
    InvalidRegistrationResponse,
)

import backend.api.passkeys as passkeys_module  # noqa: E402
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


_CRED_ID = b"test-credential-id-0001"
_CRED_ID_B64 = bytes_to_base64url(_CRED_ID)
_PUBLIC_KEY = b"stub-cose-public-key"


class _VerifiedRegistration:
    credential_id = _CRED_ID
    credential_public_key = _PUBLIC_KEY
    sign_count = 0


class _VerifiedAuthentication:
    credential_id = _CRED_ID
    new_sign_count = 7


def _csrf_headers(client) -> dict:
    token = client.get("/api/auth/csrf").get_json()["csrfToken"]
    return {"X-CSRF-Token": token}


def _signup(client, email="passkey@mail.utoronto.ca", password="correcthorsebattery"):
    resp = client.post(
        "/api/auth/signup",
        json={"email": email, "password": password},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 201, resp.get_json()


def _register_passkey(client, monkeypatch, label="MacBook Touch ID", password="correcthorsebattery"):
    # register/options now re-authenticates with the current password.
    resp = client.post(
        "/api/auth/passkeys/register/options",
        json={"password": password},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 200
    options = resp.get_json()
    assert options["challenge"] and options["rp"]["id"]

    monkeypatch.setattr(
        passkeys_module, "verify_registration_response", lambda **kw: _VerifiedRegistration()
    )
    resp = client.post(
        "/api/auth/passkeys/register/verify",
        json={"credential": {"id": _CRED_ID_B64, "rawId": _CRED_ID_B64}, "label": label},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["passkey"]


def test_register_options_requires_current_password(client):
    _signup(client)
    # No password / wrong password is rejected before any ceremony.
    assert client.post("/api/auth/passkeys/register/options", headers=_csrf_headers(client)).status_code == 401
    resp = client.post(
        "/api/auth/passkeys/register/options",
        json={"password": "wrong-password"},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 401


def test_malformed_credential_is_400_not_500(client, monkeypatch):
    _signup(client)
    client.post(
        "/api/auth/passkeys/register/options",
        json={"password": "correcthorsebattery"},
        headers=_csrf_headers(client),
    )
    resp = client.post(
        "/api/auth/passkeys/register/verify",
        json={"credential": {"id": "x", "rawId": "x"}},  # no response block -> parser raises
        headers=_csrf_headers(client),
    )
    assert resp.status_code in (400, 422)


def _server_wrapped_key(client, email):
    from backend.extensions import get_session
    from backend.models_db import User

    with client.application.app_context():
        db = get_session()
        return db.query(User).filter_by(email=email).one().server_wrapped_data_key


def test_register_requires_auth(client):
    resp = client.post("/api/auth/passkeys/register/options", headers=_csrf_headers(client))
    assert resp.status_code == 401


def test_register_stores_credential_and_server_wrapped_key(client, monkeypatch):
    _signup(client)
    assert _server_wrapped_key(client, "passkey@mail.utoronto.ca") is None

    passkey = _register_passkey(client, monkeypatch)
    assert passkey["label"] == "MacBook Touch ID"
    assert _server_wrapped_key(client, "passkey@mail.utoronto.ca") is not None

    listed = client.get("/api/auth/passkeys").get_json()["passkeys"]
    assert len(listed) == 1 and listed[0]["label"] == "MacBook Touch ID"


def test_register_verify_without_options_first_fails(client, monkeypatch):
    _signup(client)
    monkeypatch.setattr(
        passkeys_module, "verify_registration_response", lambda **kw: _VerifiedRegistration()
    )
    resp = client.post(
        "/api/auth/passkeys/register/verify",
        json={"credential": {"id": _CRED_ID_B64, "rawId": _CRED_ID_B64}},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 400


def test_register_rejected_ceremony_stores_nothing(client, monkeypatch):
    _signup(client)
    client.post("/api/auth/passkeys/register/options", headers=_csrf_headers(client))

    def _boom(**kw):
        raise InvalidRegistrationResponse("bad attestation")

    monkeypatch.setattr(passkeys_module, "verify_registration_response", _boom)
    resp = client.post(
        "/api/auth/passkeys/register/verify",
        json={"credential": {"id": _CRED_ID_B64, "rawId": _CRED_ID_B64}},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 400
    assert client.get("/api/auth/passkeys").get_json()["passkeys"] == []
    assert _server_wrapped_key(client, "passkey@mail.utoronto.ca") is None


def test_passkey_signin_round_trips_the_data_key(client, monkeypatch):
    _signup(client)
    with client.session_transaction() as sess:
        original_key = sess["data_key"]
    _register_passkey(client, monkeypatch)
    client.post("/api/auth/signout", headers=_csrf_headers(client))
    assert client.get("/api/auth/session").status_code == 401

    resp = client.post("/api/auth/passkeys/authenticate/options", headers=_csrf_headers(client))
    assert resp.status_code == 200
    assert resp.get_json()["challenge"]

    monkeypatch.setattr(
        passkeys_module, "verify_authentication_response", lambda **kw: _VerifiedAuthentication()
    )
    resp = client.post(
        "/api/auth/passkeys/authenticate/verify",
        json={"credential": {"id": _CRED_ID_B64, "rawId": _CRED_ID_B64}, "rememberMe": True},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 200
    assert resp.get_json()["user"]["email"] == "passkey@mail.utoronto.ca"
    assert client.get("/api/auth/session").status_code == 200
    with client.session_transaction() as sess:
        assert sess["data_key"] == original_key  # encrypted rows stay readable

    # sign_count advanced and last_used_at stamped.
    listed = client.get("/api/auth/passkeys").get_json()["passkeys"]
    assert listed[0]["lastUsedAt"] is not None


def test_passkey_signin_unknown_credential_fails_generically(client, monkeypatch):
    client.post("/api/auth/passkeys/authenticate/options", headers=_csrf_headers(client))
    monkeypatch.setattr(
        passkeys_module, "verify_authentication_response", lambda **kw: _VerifiedAuthentication()
    )
    resp = client.post(
        "/api/auth/passkeys/authenticate/verify",
        json={"credential": {"id": "nope", "rawId": "bm9wZQ"}},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 401
    assert resp.get_json()["error"] == "Passkey sign-in failed."


def test_passkey_signin_rejected_assertion_fails(client, monkeypatch):
    _signup(client)
    _register_passkey(client, monkeypatch)
    client.post("/api/auth/signout", headers=_csrf_headers(client))
    client.post("/api/auth/passkeys/authenticate/options", headers=_csrf_headers(client))

    def _boom(**kw):
        raise InvalidAuthenticationResponse("bad signature")

    monkeypatch.setattr(passkeys_module, "verify_authentication_response", _boom)
    resp = client.post(
        "/api/auth/passkeys/authenticate/verify",
        json={"credential": {"id": _CRED_ID_B64, "rawId": _CRED_ID_B64}},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 401


def test_delete_last_passkey_clears_server_wrapped_key(client, monkeypatch):
    _signup(client)
    passkey = _register_passkey(client, monkeypatch)
    assert _server_wrapped_key(client, "passkey@mail.utoronto.ca") is not None

    resp = client.delete(f"/api/auth/passkeys/{passkey['id']}", headers=_csrf_headers(client))
    assert resp.status_code == 200
    assert client.get("/api/auth/passkeys").get_json()["passkeys"] == []
    assert _server_wrapped_key(client, "passkey@mail.utoronto.ca") is None


def test_cannot_delete_someone_elses_passkey(client, monkeypatch):
    _signup(client, email="owner@mail.utoronto.ca")
    passkey = _register_passkey(client, monkeypatch)
    client.post("/api/auth/signout", headers=_csrf_headers(client))

    _signup(client, email="other@mail.utoronto.ca")
    resp = client.delete(f"/api/auth/passkeys/{passkey['id']}", headers=_csrf_headers(client))
    assert resp.status_code == 404
