"""DEV-ONLY auto-login bypass -- NEVER active in production.

Lets a developer (especially in a fresh Codespaces/local checkout) skip the
signup/signin forms entirely: a `before_request` hook auto-establishes a real,
valid session for a fixed dev user on the first unauthenticated `/api/*`
request, using the exact same session/crypto machinery a normal signin uses
(`backend.api.auth._start_session`, `backend.security.crypto`) -- so encrypted
transcript/plan fields work exactly as they would for a real login.

Activation gate (hard, fail-closed; see `is_bypass_active`)
------------------------------------------------------------
Active only when the app is NOT in production (`FLASK_ENV == "production"`,
same check as `backend/config_app.py`) **and** either `FLASK_ENV=development`
or `FLASK_SKIP_AUTH` is truthy. If `FLASK_ENV=production`, this module is
completely inert regardless of `FLASK_SKIP_AUTH` -- production is checked
first and short-circuits everything else.

This module never touches `backend/api/auth.py`'s real signup/signin/reset
handlers; it only imports `_start_session` (the same session-establishment
helper they use) and calls it with a get-or-created dev `User` row.
"""

from __future__ import annotations

import os

import bcrypt
from flask import Flask, current_app, g, request

from backend.api import current_user, db_session
from backend.api.auth import _start_session
from backend.models_db import User
from backend.security.crypto import generate_data_key, generate_salt, unwrap_data_key, wrap_data_key

# Fixed dev identity -- same account every time, so a developer's local data
# (transcript/plan rows) persists across restarts of the dev server.
DEV_USER_EMAIL = "dev@deciduous.local"
_DEV_PASSWORD = "dev-only-insecure-password-never-used-in-production"


def _truthy(value: str | None) -> bool:
    """Same spirit as `backend/config_app.py::_truthy`: unset/empty => false;
    `0`/`false`/`no`/`off` (case-insensitive) => false; anything else => true."""
    if value is None or value == "":
        return False
    return value.strip().lower() not in ("0", "false", "no", "off")


def is_bypass_active() -> bool:
    """Whether the dev auto-login bypass should run in this process.

    Fail-closed: production is checked *first* and unconditionally disables
    the bypass, even if `FLASK_SKIP_AUTH` is set -- there is no combination of
    other env vars that re-enables it in production.
    """
    is_production = os.environ.get("FLASK_ENV", "development") == "production"
    if is_production:
        return False
    is_development = os.environ.get("FLASK_ENV", "development") == "development"
    return is_development or _truthy(os.environ.get("FLASK_SKIP_AUTH"))


def _get_or_create_dev_user() -> tuple[User, bytes]:
    """Get-or-create the fixed dev user; return `(user, unwrapped_data_key)`.

    Mirrors what `backend/api/auth.py`'s `signup` does (salt + random data key
    + password-wrapped storage), but wraps/unwraps with the fixed dev password
    instead of a real user-supplied one.
    """
    db = db_session()
    pepper = current_app.config["DATA_KEY_PEPPER"]
    user = db.query(User).filter_by(email=DEV_USER_EMAIL).first()

    if user is not None:
        data_key = unwrap_data_key(user.wrapped_data_key, _DEV_PASSWORD, user.salt, pepper)
        if data_key is not None:
            return user, data_key
        # The wrapped key doesn't unwrap with today's DATA_KEY_PEPPER/salt (e.g.
        # the pepper env var changed between dev runs) -- rewrap it so the dev
        # bypass never gets stuck. Any previously-encrypted rows for this dev
        # user become unreadable, same caveat as a real password reset
        # (ADR-0005) -- acceptable for a throwaway local dev account.
        salt = generate_salt()
        data_key = generate_data_key()
        user.salt = salt
        user.wrapped_data_key = wrap_data_key(data_key, _DEV_PASSWORD, salt, pepper)
        db.commit()
        return user, data_key

    pw_hash = bcrypt.hashpw(_DEV_PASSWORD.encode("utf-8"), bcrypt.gensalt())
    salt = generate_salt()
    data_key = generate_data_key()
    wrapped = wrap_data_key(data_key, _DEV_PASSWORD, salt, pepper)
    user = User(email=DEV_USER_EMAIL, pw_hash=pw_hash, salt=salt, wrapped_data_key=wrapped)
    db.add(user)
    db.commit()
    return user, data_key


def register_dev_auth_bypass(app: Flask) -> None:
    """Register the auto-login `before_request` hook on `app`, if active.

    No-op (does not register anything, does not log) when `is_bypass_active()`
    is false -- in particular, always a no-op in production. Also a no-op
    under `app.config["TESTING"]` (the pytest suite's `_TestConfig` sets this
    regardless of `FLASK_ENV`) -- the bypass must never make an isolated test
    client silently authenticated, or every `*_requires_auth` test would
    break. Call this once from `backend.app.create_app`, after blueprints
    (so `/api/*` routes and `backend.api.auth._start_session` are available)
    and after the CSRF guard.
    """
    if app.config.get("TESTING"):
        return
    if not is_bypass_active():
        return

    app.logger.warning(
        "AUTH BYPASS ACTIVE (FLASK_SKIP_AUTH/dev) -- auto-signed-in dev user; NEVER use in production"
    )

    @app.before_request
    def _auto_login_dev_user():
        if not request.path.startswith("/api/"):
            return None
        if current_user() is not None:
            return None

        user, data_key = _get_or_create_dev_user()
        _start_session(user, data_key)
        # `current_user()` above cached a `None` result on `flask.g` for this
        # request; drop that cache so the view's own `current_user()` call
        # re-resolves against the session we just established.
        if "user" in g:
            del g.user
        return None
