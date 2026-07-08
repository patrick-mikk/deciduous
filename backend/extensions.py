"""Shared, process-wide resources: the SQLAlchemy engine/session and the
course/program `SqliteCache` (reused as-is from `backend/data_sources/cache.py`
— not duplicated here, per project conventions).

This project uses plain SQLAlchemy (not the Flask-SQLAlchemy extension) so the
dependency list matches `backend/requirements.txt` exactly: `SQLAlchemy` +
`PyMySQL`. `init_db(app)` builds one engine + a `scoped_session` factory keyed
per-request via Flask's app context teardown, which is the same one-session-
per-request lifecycle Flask-SQLAlchemy would give you.
"""

from __future__ import annotations

from typing import Optional

from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.data_sources.cache import SqliteCache

_SQLITE_MEMORY_URIS = {"sqlite://", "sqlite:///:memory:"}


class Base(DeclarativeBase):
    """Declarative base shared by every model in `backend/models_db.py`."""


_engine = None
_session_factory: Optional[scoped_session] = None
_course_cache: Optional[SqliteCache] = None


def init_db(app: Flask) -> None:
    """Build the engine + request-scoped session factory for `app`.

    Call once from `backend.app.create_app`. Registers a `teardown_appcontext`
    hook that returns the scoped session's connection at the end of each
    request, so handlers never need to manage sessions themselves.
    """
    global _engine, _session_factory
    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if uri in _SQLITE_MEMORY_URIS:
        # An in-memory SQLite DB is connection-scoped: a normal pool would
        # hand out a fresh (empty) database per checkout. StaticPool pins
        # everyone to the one connection that has the tables on it -- used by
        # tests only (see backend/tests/test_app_smoke.py); the SQLite *dev*
        # fallback (backend/config_app.py) always uses a real file.
        engine = create_engine(
            uri, future=True, poolclass=StaticPool, connect_args={"check_same_thread": False}
        )
    else:
        engine = create_engine(uri, pool_pre_ping=True, future=True)
    _engine = engine
    _session_factory = scoped_session(
        sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False, future=True)
    )
    app.extensions["db_engine"] = _engine
    app.extensions["db_session_factory"] = _session_factory

    @app.teardown_appcontext
    def _remove_session(exception: BaseException | None = None) -> None:
        _session_factory.remove()


def get_session() -> Session:
    """The current request's SQLAlchemy `Session`. Requires `init_db(app)` to have run."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized -- call backend.extensions.init_db(app) first.")
    return _session_factory()


def create_all(app: Flask) -> None:
    """Create all tables — used for the local SQLite dev fallback only.

    Production (MySQL, ADR-0002) is expected to be provisioned via an explicit
    migration/init step, not an implicit `create_all` on every boot.
    """
    import backend.models_db  # noqa: F401  (imported for side effect: registers model metadata on Base)

    Base.metadata.create_all(bind=_engine)


def get_course_cache() -> SqliteCache:
    """The shared `SqliteCache` for course/program data (separate store from SQLAlchemy;
    see `backend/data_sources/cache.py` — reused here, never duplicated)."""
    global _course_cache
    if _course_cache is None:
        _course_cache = SqliteCache()
    return _course_cache
