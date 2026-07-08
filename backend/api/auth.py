"""Auth blueprint: signup / signin / signout / password reset (stub) + CSRF token.

Session model: on a successful signup/signin we create a `Session` DB row
(source of truth for revocation + expiry) and put `user_id`, `session_id`,
and the *unwrapped* Fernet data key into Flask's signed, httpOnly, Secure,
SameSite=Lax session cookie (ADR-0004). The data key is never written to the
database (ADR-0005) — only `wrapped_data_key` (password-encrypted) lives on
`User`.

CSRF: the global `before_request` guard in `backend.app` requires a matching
`X-CSRF-Token` header + `csrf_token` cookie on every non-GET `/api/*` request;
`GET /api/auth/csrf` is how the client obtains that pair (double-submit
cookie pattern, defense in depth alongside `SameSite=Lax`).

Sign-in is rate-limited per account (`User.failed_login_attempts` /
`locked_until`) rather than per-process-in-memory, so it holds up under
Passenger's multi-process model.
"""

from __future__ import annotations

import datetime as dt
import re
import secrets

import bcrypt
from flask import Blueprint, current_app, jsonify, request, session

from backend.api import current_user, db_session, json_error, require_auth
from backend.models_db import Session as SessionModel
from backend.models_db import User
from backend.security.crypto import generate_data_key, generate_salt, unwrap_data_key, wrap_data_key

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MIN_PASSWORD_LEN = 10
_SESSION_LIFETIME = dt.timedelta(days=14)
_MAX_FAILED_ATTEMPTS = 8
_LOCKOUT = dt.timedelta(minutes=15)


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


def _start_session(user: User, data_key: bytes) -> None:
    """Create a `Session` row and populate the signed cookie session."""
    db = db_session()
    row = SessionModel(
        id=secrets.token_urlsafe(32),
        user_id=user.id,
        expires_at=_now() + _SESSION_LIFETIME,
        user_agent=(request.headers.get("User-Agent") or "")[:255],
        ip_address=request.remote_addr or "",
    )
    db.add(row)
    db.commit()

    session.clear()
    session.permanent = True
    session["user_id"] = user.id
    session["session_id"] = row.id
    session["data_key"] = data_key.decode("ascii")


def _user_public(user: User) -> dict:
    return {"id": user.id, "email": user.email}


@bp.route("/csrf", methods=["GET"])
def csrf_token():
    """Issue a fresh CSRF token as both a JSON body and a readable cookie
    (double-submit pattern). Call before any signup/signin/signout POST."""
    token = secrets.token_urlsafe(32)
    response = jsonify({"csrfToken": token})
    response.set_cookie(
        "csrf_token",
        token,
        httponly=False,
        samesite="Lax",
        secure=current_app.config["SESSION_COOKIE_SECURE"],
        max_age=3600,
    )
    return response


@bp.route("/signup", methods=["POST"])
def signup():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not _EMAIL_RE.match(email):
        return json_error("Enter a valid email address.", 422)
    if len(password) < _MIN_PASSWORD_LEN:
        return json_error(f"Password must be at least {_MIN_PASSWORD_LEN} characters.", 422)

    db = db_session()
    if db.query(User).filter_by(email=email).first() is not None:
        return json_error("An account with that email already exists.", 409)

    pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    salt = generate_salt()
    data_key = generate_data_key()
    wrapped = wrap_data_key(data_key, password, salt, current_app.config["DATA_KEY_PEPPER"])

    user = User(email=email, pw_hash=pw_hash, salt=salt, wrapped_data_key=wrapped)
    db.add(user)
    db.commit()

    _start_session(user, data_key)
    return jsonify({"user": _user_public(user)}), 201


@bp.route("/signin", methods=["POST"])
def signin():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    db = db_session()
    user = db.query(User).filter_by(email=email).first()
    # Same generic error whether the account doesn't exist or the password is
    # wrong -- don't let signin reveal which emails have accounts.
    generic_error = "Incorrect email or password."

    if user is None:
        return json_error(generic_error, 401)

    if user.locked_until is not None and user.locked_until > _now():
        return json_error("Too many failed attempts. Try again later.", 429)

    if not bcrypt.checkpw(password.encode("utf-8"), bytes(user.pw_hash)):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= _MAX_FAILED_ATTEMPTS:
            user.locked_until = _now() + _LOCKOUT
        db.commit()
        return json_error(generic_error, 401)

    data_key = unwrap_data_key(user.wrapped_data_key, password, user.salt, current_app.config["DATA_KEY_PEPPER"])
    if data_key is None:
        # Wrong password but bcrypt matched an older/corrupt hash pairing --
        # shouldn't happen in practice, but never proceed without a data key.
        return json_error(generic_error, 401)

    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    _start_session(user, data_key)
    return jsonify({"user": _user_public(user)})


@bp.route("/signout", methods=["POST"])
def signout():
    session_id = session.get("session_id")
    if session_id:
        db = db_session()
        row = db.get(SessionModel, session_id)
        if row is not None and row.revoked_at is None:
            row.revoked_at = _now()
            db.commit()
    session.clear()
    return jsonify({"ok": True})


@bp.route("/reset", methods=["POST"])
def reset_request():
    """Request a password reset.

    Always returns 202 regardless of whether the email exists (no account
    enumeration). NOTE (ADR-0005): resetting a password without a recovery
    code cannot re-derive the old data key, so previously encrypted
    transcript/plan rows become unreadable after a reset — the design (see
    `design/screens/01-auth-and-onboarding.md`) surfaces that warning in the
    UI. A recovery-code flow that re-wraps the data key is future work; this
    endpoint is intentionally a stub (no email delivery yet).
    """
    return jsonify({"ok": True}), 202


@bp.route("/session", methods=["GET"])
@require_auth
def whoami():
    return jsonify({"user": _user_public(current_user())})
