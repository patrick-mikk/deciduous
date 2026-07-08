"""Flask app configuration, built from environment variables.

`backend.config.load_env()` populates `os.environ` from a git-ignored `.env`
(without clobbering real env vars) before this module reads anything, so both
cPanel (real env vars) and local dev (`.env`) work the same way.

Database: if `DB_HOST`/`DB_NAME`/`DB_USER` are set, build a MySQL
(`mysql+pymysql://`) URI (ADR-0002). Otherwise fall back to a local SQLite
file under `backend/instance/` for zero-setup local dev — `create_app` will
auto-create tables for that fallback; MySQL is expected to be provisioned via
a migration/init step instead.
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote_plus

_INSTANCE_DIR = Path(__file__).resolve().parent / "instance"


def _truthy(value: str | None, default: bool) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() not in ("0", "false", "no", "off")


def _build_database_uri() -> tuple[str, bool]:
    """Return `(SQLALCHEMY_DATABASE_URI, is_sqlite_fallback)`."""
    host = os.environ.get("DB_HOST")
    name = os.environ.get("DB_NAME")
    user = os.environ.get("DB_USER")
    if host and name and user:
        password = os.environ.get("DB_PASSWORD", "")
        port = os.environ.get("DB_PORT", "3306")
        uri = (
            f"mysql+pymysql://{quote_plus(user)}:{quote_plus(password)}"
            f"@{host}:{port}/{quote_plus(name)}?charset=utf8mb4"
        )
        return uri, False

    _INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    sqlite_path = _INSTANCE_DIR / "dev.sqlite3"
    return f"sqlite:///{sqlite_path}", True


class Config:
    """Process-wide Flask config, resolved once from the environment.

    Instantiate after `backend.config.load_env()` has run (`create_app` does
    this). Pass an explicit instance to `create_app(config=...)` for tests
    that need an isolated (e.g. in-memory) database.
    """

    def __init__(self) -> None:
        is_production = os.environ.get("FLASK_ENV", "development") == "production"

        db_uri, is_sqlite = _build_database_uri()
        self.SQLALCHEMY_DATABASE_URI = db_uri
        self.IS_SQLITE_FALLBACK = is_sqlite

        secret_key = os.environ.get("FLASK_SECRET_KEY")
        if not secret_key:
            if is_production:
                raise RuntimeError("FLASK_SECRET_KEY must be set in production.")
            secret_key = "dev-insecure-secret-key-do-not-use-in-production"
        self.SECRET_KEY = secret_key

        pepper = os.environ.get("DATA_KEY_PEPPER")
        if not pepper:
            if is_production:
                raise RuntimeError("DATA_KEY_PEPPER must be set in production.")
            pepper = "dev-insecure-pepper-do-not-use-in-production"
        self.DATA_KEY_PEPPER = pepper

        # The SPA's origin, for CORS + cookie scoping. Vite's default dev port.
        self.CORS_ORIGIN = os.environ.get("CORS_ORIGIN", "http://localhost:5173")

        self.DEBUG = not is_production
        self.TESTING = False

        self.SESSION_COOKIE_NAME = "deciduous_session"
        self.SESSION_COOKIE_HTTPONLY = True
        self.SESSION_COOKIE_SAMESITE = "Lax"
        # Secure cookies need HTTPS; default on in prod, off for plain-http local dev,
        # overridable either way via SESSION_COOKIE_SECURE.
        self.SESSION_COOKIE_SECURE = _truthy(
            os.environ.get("SESSION_COOKIE_SECURE"), default=is_production
        )
        self.PERMANENT_SESSION_LIFETIME = int(
            os.environ.get("SESSION_LIFETIME_SECONDS", 60 * 60 * 24 * 14)
        )
        self.JSON_SORT_KEYS = False
