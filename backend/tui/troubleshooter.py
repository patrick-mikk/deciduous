"""Self-diagnostics for the TUI: import sanity, live-service reachability,
and log inspection - one place a user with a broken setup can run to get
actionable next steps instead of a bare traceback.
"""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass

from backend.data_sources.calendar_courses.client import CalendarCourseClient
from backend.data_sources.timetable.client import TTBClient
from backend.tui.logging_setup import LOG_PATH

logger = logging.getLogger("planner.tui")

# Import-sanity check (b) below re-imports these fresh via importlib so it
# exercises Python's import machinery, independent of the client references
# above (which tests monkeypatch for the reachability checks c/d).
_DATA_CLIENT_MODULES = [
    "backend.data_sources.timetable.client",
    "backend.data_sources.calendar_courses.client",
    "backend.data_sources.programs.client",
]

_CALENDAR_PROBE_KEYWORD = "POL208"


@dataclass
class Check:
    """One diagnostic result: is it ok, what did we see, what to do about it."""

    name: str
    ok: bool
    detail: str
    suggestion: str


class Troubleshooter:
    """Runs a handful of quick, self-contained diagnostic checks."""

    def run_diagnostics(self) -> list[Check]:
        """Run all diagnostics and return one `Check` per diagnostic, in order:

        prompt_toolkit importable; data-client imports OK; TTB reachable;
        Calendar reachable; last logged ERROR (if any).
        """
        return [
            self._check_prompt_toolkit(),
            self._check_data_client_imports(),
            self._check_ttb_reachable(),
            self._check_calendar_reachable(),
            self._check_cache_storage(),
            self._check_recent_error(),
        ]

    @staticmethod
    def _check_cache_storage() -> Check:
        """Report the local SQLite cache: where it lives and what it holds."""
        name = "local SQLite cache"
        try:
            from backend.data_sources.cache import SqliteCache

            cache = SqliteCache()
            programs = cache.program_count()
            sessions = [
                row["session"]
                for row in cache._conn.execute(
                    "SELECT session, COUNT(*) FROM courses GROUP BY session"
                )
            ]
            counts = ", ".join(f"{s}={cache.course_count(s)}" for s in sessions) or "none"
            cache.close()
        except Exception as exc:  # noqa: BLE001 - surface any storage failure
            logger.error("cache storage check failed: %s", exc)
            return Check(
                name=name,
                ok=False,
                detail=f"cache unavailable: {exc}",
                suggestion="Check filesystem permissions on the temp dir; delete the cache file to reset.",
            )
        return Check(
            name=name,
            ok=True,
            detail=f"{cache.path} | courses[{counts}] programs={programs}",
            suggestion=(
                "Empty? Run a timetable search to sync the session, or the "
                "cache file was cleared."
            ),
        )

    @staticmethod
    def _check_prompt_toolkit() -> Check:
        name = "prompt_toolkit importable"
        try:
            importlib.import_module("prompt_toolkit")
        except Exception as exc:  # noqa: BLE001 - report any import failure
            logger.error("prompt_toolkit import failed: %s", exc)
            return Check(
                name=name,
                ok=False,
                detail=f"import failed: {exc}",
                suggestion="Run: pip install prompt_toolkit==3.0.48",
            )
        return Check(name=name, ok=True, detail="OK", suggestion="")

    @staticmethod
    def _check_data_client_imports() -> Check:
        name = "data-source client imports"
        try:
            for module_name in _DATA_CLIENT_MODULES:
                importlib.import_module(module_name)
        except Exception as exc:  # noqa: BLE001 - report any import failure
            logger.error("data-source client import failed: %s", exc)
            return Check(
                name=name,
                ok=False,
                detail=f"import failed: {exc}",
                suggestion=(
                    "Run from the repo root so `backend` is importable; check "
                    "backend/data_sources/*.py for syntax errors and that "
                    "requests/beautifulsoup4/lxml are installed "
                    "(pip install -r backend/requirements.txt)."
                ),
            )
        return Check(name=name, ok=True, detail="OK", suggestion="")

    def _check_ttb_reachable(self) -> Check:
        name = "Timetable Builder reachable"
        try:
            sessions = TTBClient().current_sessions()
        except Exception as exc:  # noqa: BLE001 - surface any client failure
            logger.error("TTB reachability check failed: %s", exc)
            return Check(
                name=name,
                ok=False,
                detail=f"request failed: {exc}",
                suggestion=(
                    "Check your network connection/firewall; TTB may be "
                    "temporarily down. See backend/docs/TTB_API_REFERENCE.md."
                ),
            )
        if not sessions:
            return Check(
                name=name,
                ok=False,
                detail="current_sessions() returned no sessions",
                suggestion=(
                    "TTB's /reference-data has no current sessions right now; "
                    "try again later."
                ),
            )
        return Check(
            name=name,
            ok=True,
            detail=f"{len(sessions)} session(s): {', '.join(sessions)}",
            suggestion="",
        )

    def _check_calendar_reachable(self) -> Check:
        name = "Academic Calendar reachable"
        try:
            courses = CalendarCourseClient().search(_CALENDAR_PROBE_KEYWORD)
        except Exception as exc:  # noqa: BLE001 - surface any client failure
            logger.error("Calendar reachability check failed: %s", exc)
            return Check(
                name=name,
                ok=False,
                detail=f"request failed: {exc}",
                suggestion=(
                    "Check your network connection; the Academic Calendar site "
                    "may be temporarily down."
                ),
            )
        if not courses:
            return Check(
                name=name,
                ok=False,
                detail=f"search({_CALENDAR_PROBE_KEYWORD!r}) returned no results",
                suggestion=(
                    "The Calendar search endpoint responded but found no "
                    "matches for a known course code - the page shape may "
                    "have changed."
                ),
            )
        return Check(name=name, ok=True, detail=f"{len(courses)} result(s)", suggestion="")

    def _check_recent_error(self) -> Check:
        name = "last logged error"
        last_error = next(
            (line for line in reversed(self.read_recent_logs(limit=500)) if " ERROR " in line),
            None,
        )
        if last_error is None:
            return Check(name=name, ok=True, detail="no ERROR lines in the log", suggestion="")
        return Check(
            name=name,
            ok=False,
            detail=last_error,
            suggestion=f"See the full log at {LOG_PATH} for the traceback.",
        )

    def read_recent_logs(self, limit: int = 200) -> list[str]:
        """Return up to the last `limit` lines of the log file, oldest first.

        Returns `[]` if the log file doesn't exist yet.
        """
        if not LOG_PATH.exists():
            return []
        with LOG_PATH.open(encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
        return [line.rstrip("\n") for line in lines[-limit:]]

    def clear_logs(self) -> None:
        """Truncate the log file. No-op if it doesn't exist yet."""
        if LOG_PATH.exists():
            LOG_PATH.write_text("", encoding="utf-8")
