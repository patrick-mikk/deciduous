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

import os
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
    """Create all missing tables AND add missing nullable columns.

    Called on boot for the local SQLite dev fallback, and by
    `backend/scripts/init_db.py` for production MySQL. `MetaData.create_all`
    only creates absent tables; `_add_missing_columns` then covers the one
    schema-evolution case this project actually has (new *nullable* columns on
    an existing table, e.g. `users.display_name`), idempotently, on both
    SQLite and MySQL. Anything beyond that (renames, type changes, NOT NULL
    additions) still needs a hand-written migration.
    """
    import backend.models_db  # noqa: F401  (imported for side effect: registers model metadata on Base)

    Base.metadata.create_all(bind=_engine)
    _add_missing_columns(app)


def _add_missing_columns(app: Flask) -> None:
    """Issue `ALTER TABLE ... ADD COLUMN` for model columns absent from an
    existing table. Only nullable columns are added (safe on populated tables
    with no default-backfill question); a missing non-nullable column is
    logged loudly instead of guessed at."""
    from sqlalchemy import inspect, text

    inspector = inspect(_engine)
    with _engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if not inspector.has_table(table.name):
                continue
            existing = {col["name"] for col in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing:
                    continue
                if not column.nullable:
                    app.logger.error(
                        "Table %r is missing NON-NULLABLE column %r — refusing to auto-add; "
                        "write an explicit migration.",
                        table.name,
                        column.name,
                    )
                    continue
                col_type = column.type.compile(_engine.dialect)
                conn.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {column.name} {col_type}"))
                app.logger.info("Added missing column %s.%s (%s)", table.name, column.name, col_type)


def get_course_cache() -> SqliteCache:
    """The shared `SqliteCache` for course/program data (separate store from SQLAlchemy;
    see `backend/data_sources/cache.py` — reused here, never duplicated).

    By default `SqliteCache` lives under the OS temp dir
    (`backend/data_sources/cache.py::DEFAULT_CACHE_PATH`), which shared cPanel
    hosting wipes — fine for dev/tests, not for production. Set
    `PLANNER_CACHE_PATH` (an absolute file path) in the environment to persist
    the cache elsewhere in production; read once at construction time via
    `os.environ`, so it must be set before the first call in a process.
    Leaving it unset keeps today's behaviour exactly (the `DEFAULT_CACHE_PATH`
    temp-dir file).
    """
    global _course_cache
    if _course_cache is None:
        cache_path = os.environ.get("PLANNER_CACHE_PATH")
        _course_cache = SqliteCache(cache_path) if cache_path else SqliteCache()
    return _course_cache
