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
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from backend.api import current_data_key, current_user, db_session, json_error, require_auth
from backend.mailer import send_email
from backend.models_db import Session as SessionModel
from backend.models_db import User
from backend.security.crypto import (
    generate_data_key,
    generate_salt,
    server_unwrap_data_key,
    unwrap_data_key,
    wrap_data_key,
)

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MIN_PASSWORD_LEN = 10
# Two session lifetimes (design: "Remember me for 30 days"). Without
# remember-me the cookie is a browser-session cookie (gone on browser close)
# and the DB row caps it at 24h; with it, a persistent 30-day session.
_SESSION_LIFETIME_DEFAULT = dt.timedelta(hours=24)
_SESSION_LIFETIME_REMEMBER = dt.timedelta(days=30)
_MAX_FAILED_ATTEMPTS = 8
_LOCKOUT = dt.timedelta(minutes=15)


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


def _start_session(user: User, data_key: bytes, remember: bool = False) -> None:
    """Create a `Session` row and populate the signed cookie session.

    `remember=False` (default): non-permanent cookie (dropped when the
    browser closes) + a 24h server-side expiry. `remember=True`: permanent
    cookie + 30-day server-side expiry. The DB row's `expires_at` is the
    source of truth either way (`backend.api.current_user` checks it), so a
    lingering cookie past expiry is inert.
    """
    lifetime = _SESSION_LIFETIME_REMEMBER if remember else _SESSION_LIFETIME_DEFAULT
    db = db_session()
    row = SessionModel(
        id=secrets.token_urlsafe(32),
        user_id=user.id,
        expires_at=_now() + lifetime,
        user_agent=(request.headers.get("User-Agent") or "")[:255],
        ip_address=request.remote_addr or "",
    )
    db.add(row)
    db.commit()

    session.clear()
    session.permanent = remember
    session["user_id"] = user.id
    session["session_id"] = row.id
    session["data_key"] = data_key.decode("ascii")


def _user_public(user: User) -> dict:
    return {"id": user.id, "email": user.email, "verified": user.verified_at is not None}


# ------------------------------------------------------------ email tokens
_VERIFY_SALT = "verify-email-v1"
_RESET_SALT = "password-reset-v1"
_VERIFY_MAX_AGE = 60 * 60 * 24 * 3  # 3 days
_RESET_MAX_AGE = 60 * 60  # 1 hour


def _serializer(salt: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=salt)


def _email_token(user: User, salt: str) -> str:
    # The email is in the payload so a token minted for one address can never
    # verify/reset an account whose email has since changed.
    return _serializer(salt).dumps({"uid": user.id, "email": user.email})


def _load_email_token(token: str, salt: str, max_age: int) -> User | None:
    try:
        payload = _serializer(salt).loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    if not isinstance(payload, dict):
        return None
    user = db_session().get(User, payload.get("uid"))
    if user is None or user.email != payload.get("email"):
        return None
    return user


def _send_verification_email(user: User) -> bool:
    link = f"{current_app.config['APP_BASE_URL']}/verify?token={_email_token(user, _VERIFY_SALT)}"
    return send_email(
        user.email,
        "Verify your Deciduous email",
        "Hi,\n\n"
        "Confirm this is your email address to finish setting up your Deciduous "
        f"degree-planner account:\n\n  {link}\n\n"
        "The link works for 3 days. If you didn't create this account, you can "
        "ignore this message.\n\n— Deciduous",
    )


def _send_reset_email(user: User) -> bool:
    link = f"{current_app.config['APP_BASE_URL']}/reset?token={_email_token(user, _RESET_SALT)}"
    return send_email(
        user.email,
        "Reset your Deciduous password",
        "Hi,\n\n"
        f"Someone asked to reset the password for this account:\n\n  {link}\n\n"
        "The link works for 1 hour. If it wasn't you, ignore this message — "
        "your password is unchanged.\n\n— Deciduous",
    )


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

    _send_verification_email(user)  # best-effort; signup succeeds regardless
    _start_session(user, data_key, remember=bool(data.get("rememberMe")))
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

    _start_session(user, data_key, remember=bool(data.get("rememberMe")))
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
    """Reset a forgotten password using a recovery code.

    Body: `{email, recoveryCode, newPassword}`. The recovery code (generated
    while signed in via `POST /api/auth/recovery-code`) verifies against
    `User.recovery_code_hash` and unwraps `recovery_wrapped_data_key`, so the
    data key survives the reset and gets re-wrapped under the new password
    (closing the ADR-0005 "reset loses your data" gap for users who saved a
    code). Without a valid code this returns the same generic 401 whether the
    email exists, the code is wrong, or no code was ever generated — no
    account enumeration. Uses the same persistent lockout counters as signin.

    Called WITHOUT `recoveryCode`, this is the "email me a reset link" flow:
    if the email has an account, a signed, 1-hour reset link is sent via
    `backend.mailer` (see `reset_confirm` for the redemption endpoint).
    Always 202 either way — no account enumeration through timing-visible
    branches beyond the unavoidable SMTP queueing.
    """
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    # Normalize to the hashed form: uppercase, no spaces/dashes (the code is
    # displayed as XXXX-XXXX-XXXX-XXXX but hashed without separators).
    code = (data.get("recoveryCode") or "").strip().upper().replace(" ", "").replace("-", "")
    new_password = data.get("newPassword") or ""

    if not code:
        user = db_session().query(User).filter_by(email=email).first()
        if user is not None:
            _send_reset_email(user)
        return jsonify({"ok": True}), 202

    if len(new_password) < _MIN_PASSWORD_LEN:
        return json_error(f"Password must be at least {_MIN_PASSWORD_LEN} characters.", 422)

    generic_error = "That email and recovery code combination is not valid."
    db = db_session()
    user = db.query(User).filter_by(email=email).first()
    if user is None or not user.recovery_code_hash or not user.recovery_wrapped_data_key:
        return json_error(generic_error, 401)

    if user.locked_until is not None and user.locked_until > _now():
        return json_error("Too many failed attempts. Try again later.", 429)

    if not bcrypt.checkpw(code.encode("utf-8"), bytes(user.recovery_code_hash)):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= _MAX_FAILED_ATTEMPTS:
            user.locked_until = _now() + _LOCKOUT
        db.commit()
        return json_error(generic_error, 401)

    pepper = current_app.config["DATA_KEY_PEPPER"]
    data_key = unwrap_data_key(user.recovery_wrapped_data_key, code, user.recovery_salt or "", pepper)
    if data_key is None:
        return json_error(generic_error, 401)

    salt = generate_salt()
    user.pw_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())
    user.salt = salt
    user.wrapped_data_key = wrap_data_key(data_key, new_password, salt, pepper)
    user.failed_login_attempts = 0
    user.locked_until = None
    _revoke_all_sessions(db, user.id)  # a reset invalidates every signed-in device
    db.commit()

    _start_session(user, data_key)
    return jsonify({"user": _user_public(user)})


@bp.route("/reset/confirm", methods=["POST"])
def reset_confirm():
    """Redeem an emailed reset link: `{token, newPassword}`.

    Data-key outcome (ADR-0005/0006), reported as `dataPreserved`:
    - The account has a passkey (so `server_wrapped_data_key` exists): the
      data key is recovered from that wrap and re-wrapped under the new
      password — encrypted transcript/plan data SURVIVES.
    - Otherwise the old data key is unrecoverable without the password or a
      recovery code: a FRESH data key is issued, old encrypted values become
      unreadable (they decrypt to empty, never garbage), and now-useless
      recovery-code fields are cleared. The UI warns before this path.
    Every session is revoked, then the caller is signed in.
    """
    data = request.get_json(silent=True) or {}
    token = data.get("token") or ""
    new_password = data.get("newPassword") or ""

    if len(new_password) < _MIN_PASSWORD_LEN:
        return json_error(f"Password must be at least {_MIN_PASSWORD_LEN} characters.", 422)

    user = _load_email_token(token, _RESET_SALT, _RESET_MAX_AGE)
    if user is None:
        return json_error("That reset link is invalid or has expired — request a new one.", 401)

    pepper = current_app.config["DATA_KEY_PEPPER"]
    data_key = (
        server_unwrap_data_key(user.server_wrapped_data_key, pepper)
        if user.server_wrapped_data_key
        else None
    )
    preserved = data_key is not None
    if not preserved:
        data_key = generate_data_key()
        # Recovery wraps protect the OLD key — clear them so Settings offers a
        # fresh code instead of silently keeping one that can't restore anything.
        user.recovery_code_hash = None
        user.recovery_salt = None
        user.recovery_wrapped_data_key = None

    db = db_session()
    salt = generate_salt()
    user.pw_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())
    user.salt = salt
    user.wrapped_data_key = wrap_data_key(data_key, new_password, salt, pepper)
    user.failed_login_attempts = 0
    user.locked_until = None
    # The link proves control of the mailbox — that's exactly what
    # verification asserts, so count it.
    if user.verified_at is None:
        user.verified_at = _now()
    _revoke_all_sessions(db, user.id)
    db.commit()

    _start_session(user, data_key)
    return jsonify({"user": _user_public(user), "dataPreserved": preserved})


# ------------------------------------------------------- email verification
@bp.route("/verify", methods=["POST"])
def verify_email():
    """Redeem an emailed verification link: `{token}`. Public — the link may
    be opened in a browser with no session; verifying never signs anyone in."""
    data = request.get_json(silent=True) or {}
    user = _load_email_token(data.get("token") or "", _VERIFY_SALT, _VERIFY_MAX_AGE)
    if user is None:
        return json_error("That verification link is invalid or has expired.", 401)
    if user.verified_at is None:
        user.verified_at = _now()
        db_session().commit()
    return jsonify({"ok": True, "email": user.email})


@bp.route("/verify/request", methods=["POST"])
@require_auth
def resend_verification():
    """Re-send the verification email for the signed-in account."""
    user = current_user()
    if user.verified_at is not None:
        return jsonify({"ok": True, "alreadyVerified": True})
    sent = _send_verification_email(user)
    if not sent:
        return json_error("Email sending isn't configured on this server yet.", 503)
    return jsonify({"ok": True})


@bp.route("/session", methods=["GET"])
@require_auth
def whoami():
    return jsonify({"user": _user_public(current_user())})


# ---------------------------------------------------------------- sessions
def _revoke_all_sessions(db, user_id: int, keep: str | None = None) -> None:
    rows = db.query(SessionModel).filter_by(user_id=user_id, revoked_at=None).all()
    for row in rows:
        if keep is not None and row.id == keep:
            continue
        row.revoked_at = _now()


def _session_public(row: SessionModel, current_id: str | None) -> dict:
    return {
        "id": row.id,
        "current": row.id == current_id,
        "createdAt": row.created_at.isoformat() + "Z",
        "expiresAt": row.expires_at.isoformat() + "Z",
        "userAgent": row.user_agent or "",
        "ipAddress": row.ip_address or "",
    }


@bp.route("/sessions", methods=["GET"])
@require_auth
def list_sessions():
    """Every ACTIVE session for the signed-in user (Settings → Security →
    "Active sessions"), newest first, with the caller's own marked `current`."""
    db = db_session()
    user = current_user()
    current_id = session.get("session_id")
    rows = (
        db.query(SessionModel)
        .filter_by(user_id=user.id, revoked_at=None)
        .order_by(SessionModel.created_at.desc())
        .all()
    )
    active = [_session_public(r, current_id) for r in rows if r.is_active]
    return jsonify({"sessions": active})


@bp.route("/sessions/<session_id>", methods=["DELETE"])
@require_auth
def revoke_session(session_id: str):
    """Revoke one of the caller's own sessions. Revoking the current one is
    allowed and doubles as a sign-out (the cookie session is cleared too)."""
    db = db_session()
    user = current_user()
    row = db.get(SessionModel, session_id)
    if row is None or row.user_id != user.id:
        return json_error("No such session.", 404)
    if row.revoked_at is None:
        row.revoked_at = _now()
        db.commit()
    if session.get("session_id") == session_id:
        session.clear()
    return jsonify({"ok": True})


@bp.route("/sessions/revoke-others", methods=["POST"])
@require_auth
def revoke_other_sessions():
    """"Sign out everywhere else": revoke every active session except this one."""
    db = db_session()
    user = current_user()
    _revoke_all_sessions(db, user.id, keep=session.get("session_id"))
    db.commit()
    return jsonify({"ok": True})


# ------------------------------------------------------- password & account
@bp.route("/change-password", methods=["POST"])
@require_auth
def change_password():
    """Change the signed-in user's password, re-wrapping the data key under
    the new one (the key itself never changes, so encrypted rows are
    untouched). Requires the current password even with a live session —
    a stolen open laptop shouldn't be enough. Revokes every OTHER session."""
    data = request.get_json(silent=True) or {}
    current_password = data.get("currentPassword") or ""
    new_password = data.get("newPassword") or ""

    if len(new_password) < _MIN_PASSWORD_LEN:
        return json_error(f"Password must be at least {_MIN_PASSWORD_LEN} characters.", 422)

    db = db_session()
    user = current_user()
    if not bcrypt.checkpw(current_password.encode("utf-8"), bytes(user.pw_hash)):
        return json_error("Current password is incorrect.", 401)

    pepper = current_app.config["DATA_KEY_PEPPER"]
    data_key = unwrap_data_key(user.wrapped_data_key, current_password, user.salt, pepper)
    if data_key is None:
        return json_error("Current password is incorrect.", 401)

    salt = generate_salt()
    user.pw_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())
    user.salt = salt
    user.wrapped_data_key = wrap_data_key(data_key, new_password, salt, pepper)
    _revoke_all_sessions(db, user.id, keep=session.get("session_id"))
    db.commit()
    return jsonify({"ok": True})


_RECOVERY_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no 0/O/1/I/L lookalikes


def _generate_recovery_code() -> str:
    groups = ["".join(secrets.choice(_RECOVERY_ALPHABET) for _ in range(4)) for _ in range(4)]
    return "-".join(groups)


@bp.route("/recovery-code", methods=["POST"])
@require_auth
def generate_recovery_code():
    """Generate (or regenerate) the account's recovery code.

    Returns the plaintext code EXACTLY ONCE — only its bcrypt hash and a
    recovery-code-wrapped copy of the data key are stored, so a later
    password reset with the code can re-wrap the key (see `reset_request`).
    Regenerating replaces the previous code; the old one stops working.
    Requires the live session's data key (always present on this route,
    since every sign-in path carries it).
    """
    data_key = current_data_key()
    if data_key is None:
        return json_error("Session is missing its data key — sign in again.", 401)

    code = _generate_recovery_code()
    normalized = code.replace("-", "")
    salt = generate_salt()
    db = db_session()
    user = current_user()
    user.recovery_code_hash = bcrypt.hashpw(normalized.encode("utf-8"), bcrypt.gensalt())
    user.recovery_salt = salt
    user.recovery_wrapped_data_key = wrap_data_key(
        data_key, normalized, salt, current_app.config["DATA_KEY_PEPPER"]
    )
    db.commit()
    return jsonify({"recoveryCode": code})


@bp.route("/account", methods=["DELETE"])
@require_auth
def delete_account():
    """Permanently delete the account and everything under it (cascades to
    sessions, transcript, plans, enrolments, shares, passkeys). Requires the
    password as re-confirmation."""
    data = request.get_json(silent=True) or {}
    password = data.get("password") or ""

    db = db_session()
    user = current_user()
    if not bcrypt.checkpw(password.encode("utf-8"), bytes(user.pw_hash)):
        return json_error("Password is incorrect.", 401)

    db.delete(user)
    db.commit()
    session.clear()
    return jsonify({"ok": True})
