"""`backend/api/*.py` — one module per resource, auto-registered as blueprints.

Blueprint contract
------------------
Any `backend/api/<name>.py` module that defines a module-level `bp`
(a `flask.Blueprint` instance) is auto-registered by
`backend.app.create_app` — just drop a new file here, e.g.:

    # backend/api/plan.py
    from flask import Blueprint, jsonify
    from backend.api import current_user, db_session, json_error, require_auth

    bp = Blueprint("plan", __name__, url_prefix="/api/plan")

    @bp.route("", methods=["GET"])
    @require_auth
    def get_plan():
        ...

No registration step needed elsewhere. Give your blueprint its own
`url_prefix` (matching the `/api/...` paths in
`design/06-data-model-and-api.md`) — `create_app` does not add prefixes for
you. Module names starting with `_` and sub-packages are skipped.

CSRF and CORS are handled globally in `backend.app` (a `before_request`/
`after_request` pair) — individual endpoint modules don't need to think about
either.

Helpers for endpoint modules
-----------------------------
- `db_session()` — the request-scoped SQLAlchemy `Session` (via
  `backend.extensions.get_session`). Don't create your own engine/session.
- `current_user()` — the signed-in `User` row for this request, or `None`.
  Resolves the cookie session against the `Session` DB row (checks revocation
  + expiry), and caches the result on `flask.g` for the request.
- `require_auth` — route decorator; 401s with a clean JSON body if
  `current_user()` is `None`.
- `current_data_key()` — the caller's unwrapped Fernet data key (`bytes`),
  read from the session cookie. Pair with
  `backend.security.crypto.encrypt_field`/`decrypt_field` for encrypted
  columns (`TranscriptEntry.grade_encrypted`, `PlanItem.notes_encrypted`, ...).
  `None` outside an authenticated request.
- `json_error(message, status)` — a clean `{"error": message}` JSON response.
  Prefer this (or letting an exception propagate to `backend.app`'s handlers)
  over ad hoc error shapes, so the client always gets a predictable body.
"""

from __future__ import annotations

from functools import wraps
from typing import Callable, TypeVar

from flask import g, jsonify, session

from backend.extensions import get_session as db_session  # re-exported for endpoint modules
from backend.models_db import Session as SessionModel
from backend.models_db import User

__all__ = [
    "db_session",
    "current_user",
    "current_data_key",
    "require_auth",
    "json_error",
]

F = TypeVar("F", bound=Callable)


def json_error(message: str, status: int = 400):
    """A clean `{"error": message}` JSON response — never a stack trace."""
    response = jsonify({"error": message})
    response.status_code = status
    return response


def current_user() -> User | None:
    """The signed-in `User` for this request, or `None`. Cached on `flask.g`."""
    if "user" in g:
        return g.user

    g.user = None
    user_id = session.get("user_id")
    session_id = session.get("session_id")
    if not user_id or not session_id:
        return None

    db = db_session()
    row = db.get(SessionModel, session_id)
    if row is None or row.user_id != user_id or not row.is_active:
        return None

    g.user = db.get(User, user_id)
    return g.user


def current_data_key() -> bytes | None:
    """The caller's unwrapped Fernet data key, or `None` outside an authenticated request."""
    raw = session.get("data_key")
    return raw.encode("ascii") if raw else None


def require_auth(view: F) -> F:
    """Route decorator: 401s with `{"error": ...}` unless `current_user()` is set."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        if current_user() is None:
            return json_error("Authentication required.", 401)
        return view(*args, **kwargs)

    return wrapper  # type: ignore[return-value]
