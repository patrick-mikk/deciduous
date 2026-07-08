"""Offline unit tests for backend/tui/troubleshooter.py.

Monkeypatches TTBClient/CalendarCourseClient at the backend.tui.troubleshooter
module level so the reachability checks never touch the network - per
docs/conventions.md ("Unit tests must not hit the network"). The
prompt_toolkit/import checks and the log-reading checks are exercised as-is
since they are already network-free.

Runnable both ways:
    python -m pytest backend/tests/test_troubleshooter.py -q
    python backend/tests/test_troubleshooter.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

# Make `backend` importable as a namespace package regardless of how this
# file is invoked - see backend/tests/test_timetable.py for the same shim.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.tui.logging_setup import LOG_PATH, setup_logging
from backend.tui import troubleshooter as troubleshooter_module
from backend.tui.troubleshooter import Check, Troubleshooter


class _FakeTTBClientOk:
    def current_sessions(self) -> list[str]:
        return ["20239", "20241"]


class _FakeTTBClientNoSessions:
    def current_sessions(self) -> list[str]:
        return []


class _FakeTTBClientFails:
    def current_sessions(self) -> list[str]:
        raise RuntimeError("ttb down")


class _FakeCalendarClientOk:
    def search(self, keyword: str) -> list[object]:
        return [object()]


class _FakeCalendarClientEmpty:
    def search(self, keyword: str) -> list[object]:
        return []


class _FakeCalendarClientFails:
    def search(self, keyword: str) -> list[object]:
        raise RuntimeError("calendar down")


# ---------------------------------------------------------------------------
# run_diagnostics() shape
# ---------------------------------------------------------------------------


def test_run_diagnostics_returns_six_checks(monkeypatch: Any) -> None:
    monkeypatch.setattr(troubleshooter_module, "TTBClient", _FakeTTBClientOk)
    monkeypatch.setattr(troubleshooter_module, "CalendarCourseClient", _FakeCalendarClientOk)

    checks = Troubleshooter().run_diagnostics()

    assert len(checks) == 6
    assert all(isinstance(c, Check) for c in checks)
    assert any("cache" in c.name for c in checks)


# ---------------------------------------------------------------------------
# Individual checks: prompt_toolkit / data-client imports (already offline)
# ---------------------------------------------------------------------------


def test_check_prompt_toolkit_ok() -> None:
    check = Troubleshooter._check_prompt_toolkit()
    assert check.ok is True
    assert check.suggestion == ""


def test_check_data_client_imports_ok() -> None:
    check = Troubleshooter._check_data_client_imports()
    assert check.ok is True


# ---------------------------------------------------------------------------
# TTB reachability
# ---------------------------------------------------------------------------


def test_check_ttb_reachable_ok(monkeypatch: Any) -> None:
    monkeypatch.setattr(troubleshooter_module, "TTBClient", _FakeTTBClientOk)

    check = Troubleshooter()._check_ttb_reachable()

    assert check.ok is True
    assert "20239" in check.detail


def test_check_ttb_reachable_fails_on_client_error(monkeypatch: Any) -> None:
    monkeypatch.setattr(troubleshooter_module, "TTBClient", _FakeTTBClientFails)

    check = Troubleshooter()._check_ttb_reachable()

    assert check.ok is False
    assert "ttb down" in check.detail
    assert check.suggestion  # actionable suggestion present


def test_check_ttb_reachable_fails_on_no_sessions(monkeypatch: Any) -> None:
    monkeypatch.setattr(troubleshooter_module, "TTBClient", _FakeTTBClientNoSessions)

    check = Troubleshooter()._check_ttb_reachable()

    assert check.ok is False
    assert check.suggestion


# ---------------------------------------------------------------------------
# Calendar reachability
# ---------------------------------------------------------------------------


def test_check_calendar_reachable_ok(monkeypatch: Any) -> None:
    monkeypatch.setattr(troubleshooter_module, "CalendarCourseClient", _FakeCalendarClientOk)

    check = Troubleshooter()._check_calendar_reachable()

    assert check.ok is True


def test_check_calendar_reachable_fails_on_client_error(monkeypatch: Any) -> None:
    monkeypatch.setattr(troubleshooter_module, "CalendarCourseClient", _FakeCalendarClientFails)

    check = Troubleshooter()._check_calendar_reachable()

    assert check.ok is False
    assert "calendar down" in check.detail
    assert check.suggestion


def test_check_calendar_reachable_fails_on_empty_result(monkeypatch: Any) -> None:
    monkeypatch.setattr(troubleshooter_module, "CalendarCourseClient", _FakeCalendarClientEmpty)

    check = Troubleshooter()._check_calendar_reachable()

    assert check.ok is False
    assert check.suggestion


# ---------------------------------------------------------------------------
# Log reading / clearing / last-error detection
# ---------------------------------------------------------------------------


def test_read_recent_logs_sees_lines_written_after_setup_logging() -> None:
    setup_logging()
    logger = logging.getLogger("planner.tui")
    logger.info("read_recent_logs marker line")

    lines = Troubleshooter().read_recent_logs(limit=200)

    assert any("read_recent_logs marker line" in line for line in lines)


def test_clear_logs_truncates_the_log_file() -> None:
    setup_logging()
    logging.getLogger("planner.tui").info("line before clearing")

    troubleshooter = Troubleshooter()
    troubleshooter.clear_logs()

    assert troubleshooter.read_recent_logs() == []
    assert LOG_PATH.exists()
    assert LOG_PATH.read_text(encoding="utf-8") == ""


def test_check_recent_error_reports_last_error() -> None:
    setup_logging()
    troubleshooter = Troubleshooter()
    troubleshooter.clear_logs()
    logging.getLogger("planner.tui").error("boom test marker")

    check = troubleshooter._check_recent_error()

    assert check.ok is False
    assert "boom test marker" in check.detail
    assert str(LOG_PATH) in check.suggestion


def test_check_recent_error_ok_when_no_errors_logged() -> None:
    setup_logging()
    troubleshooter = Troubleshooter()
    troubleshooter.clear_logs()
    logging.getLogger("planner.tui").info("all good, no errors here")

    check = troubleshooter._check_recent_error()

    assert check.ok is True
    assert check.suggestion == ""


# ---------------------------------------------------------------------------
# Plain `python backend/tests/test_troubleshooter.py` runner (no pytest)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Configure the "planner.tui" logger first so logger.error() calls below
    # go to the file handler instead of Python's stderr "lastResort" handler.
    setup_logging()

    class _ManualMonkeypatch:
        def __init__(self) -> None:
            self._restores: list[tuple[Any, str, Any]] = []

        def setattr(self, obj: Any, name: str, value: Any) -> None:
            self._restores.append((obj, name, getattr(obj, name)))
            setattr(obj, name, value)

        def undo(self) -> None:
            for obj, name, original in reversed(self._restores):
                setattr(obj, name, original)

    _tests_needing_monkeypatch = [
        test_run_diagnostics_returns_six_checks,
        test_check_ttb_reachable_ok,
        test_check_ttb_reachable_fails_on_client_error,
        test_check_ttb_reachable_fails_on_no_sessions,
        test_check_calendar_reachable_ok,
        test_check_calendar_reachable_fails_on_client_error,
        test_check_calendar_reachable_fails_on_empty_result,
    ]
    for test_fn in _tests_needing_monkeypatch:
        mp = _ManualMonkeypatch()
        try:
            test_fn(mp)  # type: ignore[arg-type]
            print(f"PASS {test_fn.__name__}")
        finally:
            mp.undo()

    _tests_no_monkeypatch = [
        test_check_prompt_toolkit_ok,
        test_check_data_client_imports_ok,
        test_read_recent_logs_sees_lines_written_after_setup_logging,
        test_clear_logs_truncates_the_log_file,
        test_check_recent_error_reports_last_error,
        test_check_recent_error_ok_when_no_errors_logged,
    ]
    for test_fn in _tests_no_monkeypatch:
        test_fn()
        print(f"PASS {test_fn.__name__}")

    print("\nAll test_troubleshooter checks passed.")
