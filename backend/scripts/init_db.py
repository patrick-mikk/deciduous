"""Explicit, idempotent database provisioning step for production (cPanel MySQL).

`backend.app.create_app` only auto-runs `backend.extensions.create_all` for the
local SQLite dev fallback (see `backend/extensions.py:74` and
`backend/app.py::create_app`) — a fresh cPanel MySQL database is never
auto-provisioned on boot, so it has zero tables until this script is run once.

Usage (from the repo root)::

    python -m backend.scripts.init_db

Idempotent: this calls `backend.extensions.create_all`, which issues DDL only
for tables that don't exist yet (`CREATE TABLE IF NOT EXISTS` semantics) and
then adds any missing *nullable* columns to existing tables (see
`backend/extensions.py::_add_missing_columns`) — running this script again is
a no-op once the schema is current. Larger migrations (renames, type changes,
NOT NULL additions) still need a hand-written step.

Refuses to run against the local SQLite dev fallback (i.e. when `DB_HOST` /
`DB_NAME` / `DB_USER` are not all set — see `backend/config_app.py`) unless
`--allow-sqlite` is passed, so a missing/misconfigured `DB_*` env var on
cPanel fails loudly instead of silently "provisioning"
`backend/instance/dev.sqlite3` while someone believes MySQL got set up.
"""

from __future__ import annotations

import argparse
import sys
from urllib.parse import urlsplit

from flask import Flask
from sqlalchemy import inspect

from backend.config import load_env
from backend.config_app import Config
from backend.extensions import create_all, init_db


def _safe_target(uri: str) -> str:
    """`uri`'s scheme/host/port/database name only — NEVER the credentials."""
    parts = urlsplit(uri)
    host = parts.hostname or ""
    port = f":{parts.port}" if parts.port else ""
    db_name = parts.path.lstrip("/")
    return f"{parts.scheme}://{host}{port}/{db_name}"


def _table_names(app: Flask) -> list[str]:
    engine = app.extensions["db_engine"]
    return sorted(inspect(engine).get_table_names())


def main(argv: list[str] | None = None) -> int:
    """Parse args, build config the same way `create_app` does, and provision.

    Returns a process exit code (0 success, 1 refused/failed).
    """
    parser = argparse.ArgumentParser(
        description="Create any missing tables for the configured database (idempotent)."
    )
    parser.add_argument(
        "--allow-sqlite",
        action="store_true",
        help="Allow running against the local SQLite dev fallback (refused by default).",
    )
    args = parser.parse_args(argv)

    load_env()
    config = Config()

    if config.IS_SQLITE_FALLBACK and not args.allow_sqlite:
        print(
            "Refusing to run: DB_HOST/DB_NAME/DB_USER are not all set, so this resolved "
            "to the local SQLite dev fallback, not MySQL. Set the DB_* env vars on cPanel, "
            "or pass --allow-sqlite if you really mean to provision the SQLite fallback.",
            file=sys.stderr,
        )
        return 1

    print(f"Target database: {_safe_target(config.SQLALCHEMY_DATABASE_URI)}")

    app = Flask(__name__)
    app.config.from_object(config)
    init_db(app)
    create_all(app)

    tables = _table_names(app)
    print(f"Tables present after create_all ({len(tables)}): {', '.join(tables) or '(none)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
