"""Nightly cron entry point: warm the persistent course/program cache.

Usage (cron, from the repo root)::

    python -m backend.scripts.refresh_cache
    python -m backend.scripts.refresh_cache --dry-run   # no network bulk pull

Resolves the shared cache via `backend.extensions.get_course_cache()`, so
`PLANNER_CACHE_PATH` (see `backend/extensions.py::get_course_cache`) is
honored automatically — point cPanel's cron environment at a persistent file,
not the OS temp dir `SqliteCache` defaults to.

Session codes are never hard-coded (AGENTS.md) — they're discovered at
runtime from the Timetable Builder's `/reference-data` endpoint via
`TTBClient.current_sessions()` (`backend/data_sources/timetable/client.py`),
the same call the rest of the app (and `backend/tui/service.py`) uses.

This is a thin orchestrator: all HTTP/parsing is delegated to `TTBClient` and
`ProgramClient` (`backend/data_sources/`). Per-page pacing during a session's
or the catalog's pagination lives inside those clients' own page loops
(`TTBClient.search`, `ProgramClient.search`, both call
`backend.data_sources.http.throttle()` between pages) so it protects every
caller, not just this script. The `_throttle`/`THROTTLE_MIN`/`THROTTLE_MAX`
pattern imported here from `backend/scripts/harvest_programs.py` is reused
only for the coarser between-session and between-catalog-pull pacing below,
on top of that per-page throttle.

`--dry-run` prints what WOULD be fetched — discovered sessions, and the
cache's current course/program counts — without doing the bulk pull, so this
can be smoke-tested from a sandbox where UofT endpoints are unreachable.
"""

from __future__ import annotations

import argparse
import datetime
import sys

from backend.config import load_env
from backend.data_sources.cache import PROGRAMS_CATALOG_FULL_AT, SqliteCache
from backend.data_sources.models import Program
from backend.data_sources.programs.client import ProgramClient
from backend.data_sources.timetable.client import TTBClient
from backend.extensions import get_course_cache
from backend.scripts.harvest_programs import _throttle

_DIVISION = "ARTSC"
# Generous safety cap: the primary combine="" type=All program query needed
# ~14 pages as of 2026-07-08 (see harvest_programs.py); ProgramClient.search's
# own default (5) is tuned for smaller/keyword-scoped calls, not a full pull.
_PROGRAM_MAX_PAGES = 60


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _discover_sessions(ttb: TTBClient) -> list[str]:
    """Usable session codes from `/reference-data` — never hard-coded."""
    return ttb.current_sessions()


def _dry_run(cache: SqliteCache, sessions: list[str]) -> None:
    print(f"[dry-run] discovered {len(sessions)} session(s): {sessions}")
    print(f"[dry-run] cache currently holds {cache.program_count()} program(s)")
    for session in sessions:
        print(f"[dry-run]   session {session}: {cache.course_count(session)} course(s) cached now")
    print(
        f"[dry-run] would pull ARTSC courses for {len(sessions)} session(s) and "
        "refresh the full program catalog; no network calls made."
    )


def _refresh_courses(ttb: TTBClient, cache: SqliteCache, sessions: list[str], fetched_at: str) -> int:
    total = 0
    for session in sessions:
        courses = ttb.search(session=session, division=_DIVISION)
        cache.upsert_courses(session, courses, fetched_at)
        total += len(courses)
        print(f"  session {session}: {len(courses)} course(s) cached")
        _throttle()
    return total


def _refresh_programs(cache: SqliteCache, fetched_at: str) -> int:
    programs: list[Program] = ProgramClient().search(max_pages=_PROGRAM_MAX_PAGES)
    cache.upsert_programs(programs, fetched_at)
    if programs:
        # Mark the catalog complete so `/api/programs` catalog browses trust
        # the cache instead of re-pulling (backend/api/programs.py).
        cache.set_meta(PROGRAMS_CATALOG_FULL_AT, fetched_at)
    _throttle()
    print(f"  programs: {len(programs)} cached")
    return len(programs)


def refresh(*, dry_run: bool) -> int:
    """Warm the shared cache (or, with `dry_run`, just report what would happen).

    Returns a process exit code: 0 on success, 1 on hard failure.
    """
    cache = get_course_cache()
    ttb = TTBClient()

    try:
        sessions = _discover_sessions(ttb)
    except Exception as exc:  # network/parse failure discovering sessions
        print(f"refresh_cache: FAILED discovering sessions ({exc})", file=sys.stderr)
        return 1

    if not sessions:
        print(
            "refresh_cache: FAILED -- /reference-data returned no usable session codes",
            file=sys.stderr,
        )
        return 1

    if dry_run:
        _dry_run(cache, sessions)
        return 0

    fetched_at = _now_iso()
    try:
        course_count = _refresh_courses(ttb, cache, sessions, fetched_at)
        program_count = _refresh_programs(cache, fetched_at)
    except Exception as exc:  # any network/parse failure during the bulk pull
        print(f"refresh_cache: FAILED during bulk pull ({exc})", file=sys.stderr)
        return 1

    print(
        f"refresh_cache: OK -- {len(sessions)} session(s), {course_count} course(s), "
        f"{program_count} program(s) refreshed at {fetched_at}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Warm the persistent TTB/Calendar cache.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print discovered sessions/cache counts; make no bulk-pull network calls.",
    )
    args = parser.parse_args(argv)

    load_env()
    return refresh(dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
