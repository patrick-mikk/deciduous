"""Importing an Academic History record without an account.

The onboarding "Do you have existing credits?" step is reachable with no
account, so a 401 there was a dead end rather than a nudge: parsing needs the
server (pdfplumber has no browser equivalent) but persisting does not, and
gating both on a session left a guest unable to complete the one action the
step exists for.

These cover the split in `backend/api/import_.py`:

- a guest parses and gets `saved: false` plus the parsed `courses` back --
  the response is their only copy, so it has to carry the data;
- nothing is written for a guest (no `TranscriptEntry` rows appear);
- a signed-in caller is unchanged: `saved: true`, persisted, and the
  response does NOT depend on the guest branch;
- `POST /api/import/courses` replays a stored guest import into a new
  account (the SignUp.tsx hand-off), and still requires auth, since it
  writes.
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
from backend.models_db import TranscriptEntry  # noqa: E402


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
def app():
    return create_app(config=_TestConfig())


@pytest.fixture()
def client(app):
    return app.test_client()


def _csrf_headers(client) -> dict:
    return {"X-CSRF-Token": client.get("/api/auth/csrf").get_json()["csrfToken"]}


def _signup(client, email="guest@mail.utoronto.ca", password="correcthorsebattery") -> None:
    resp = client.post(
        "/api/auth/signup",
        json={"email": email, "password": password},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 201, resp.get_data(as_text=True)


_CAPTURE = {
    "transcript": [
        {"code": "POL208H1", "title": "Intro to International Relations", "credits": 0.5,
         "grade": "A-", "mark": 82, "session": "20239", "status": "completed"},
        {"code": "MAT137Y1", "title": "Calculus", "credits": 1.0,
         "grade": "B+", "mark": 78, "session": "20239", "status": "completed"},
    ]
}


def _transcript_row_count(app) -> int:
    from backend.extensions import get_session

    with app.app_context():
        db = get_session()
        try:
            return db.query(TranscriptEntry).count()
        finally:
            db.close()


# ------------------------------------------------------------------ guest path


def test_guest_import_parses_and_returns_courses(client):
    """The whole point: a guest completes the import instead of being blocked."""
    resp = client.post("/api/import/capture", json=_CAPTURE, headers=_csrf_headers(client))

    assert resp.status_code == 200, resp.get_data(as_text=True)
    body = resp.get_json()
    assert body["saved"] is False
    assert body["courseCount"] == 2
    # The response IS the guest's only copy -- if it came back without the
    # courses there would be nothing to put in localStorage.
    assert [c["code"] for c in body["courses"]] == ["POL208H1", "MAT137Y1"]
    assert body["courses"][0]["grade"] == "A-"
    assert body["courses"][0]["credits"] == 0.5


def test_guest_import_persists_nothing(client, app):
    """`saved: false` has to be literally true -- no rows, no orphaned user."""
    client.post("/api/import/capture", json=_CAPTURE, headers=_csrf_headers(client))
    assert _transcript_row_count(app) == 0


def test_guest_import_of_an_empty_capture_warns_rather_than_crashing(client):
    """Dropping @require_auth must not turn a junk body into a 500.

    `parse_capture` is deliberately tolerant (unchanged here): an unrecognised
    payload yields an empty draft carrying a warning, not an exception. What
    matters for the guest path is that the warning still reaches them -- the
    response is their only copy, so a silent empty success would look like a
    successful import of nothing.
    """
    resp = client.post("/api/import/capture", json={"nonsense": True}, headers=_csrf_headers(client))

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["saved"] is False
    assert body["courseCount"] == 0
    assert body["warnings"], "an empty capture must explain itself"


# -------------------------------------------------------------- signed-in path


def test_signed_in_import_still_persists(client, app):
    """The signed-in contract is unchanged by the guest branch."""
    _signup(client)
    resp = client.post("/api/import/capture", json=_CAPTURE, headers=_csrf_headers(client))

    assert resp.status_code == 200, resp.get_data(as_text=True)
    body = resp.get_json()
    assert body["saved"] is True
    assert body["courseCount"] == 2
    assert _transcript_row_count(app) == 2


# ------------------------------------------------- guest -> account hand-off


def test_stored_guest_import_replays_into_a_new_account(client, app):
    """SignUp.tsx's hand-off: the PDF is long gone, only the parse was kept."""
    guest = client.post("/api/import/capture", json=_CAPTURE, headers=_csrf_headers(client)).get_json()
    assert guest["saved"] is False
    assert _transcript_row_count(app) == 0

    _signup(client)
    resp = client.post(
        "/api/import/courses",
        json={"courses": guest["courses"], "programs": guest["programs"]},
        headers=_csrf_headers(client),
    )

    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert resp.get_json()["courseCount"] == 2
    assert _transcript_row_count(app) == 2


def test_replay_endpoint_requires_an_account(client):
    """It writes, so unlike the parse routes it must stay gated."""
    resp = client.post(
        "/api/import/courses",
        json={"courses": [{"code": "POL208H1"}], "programs": []},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 401


def test_replay_endpoint_rejects_a_malformed_payload(client):
    """A corrupted localStorage blob is a 422, never a 500."""
    _signup(client)
    resp = client.post(
        "/api/import/courses",
        json={"courses": "not-a-list"},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 422
