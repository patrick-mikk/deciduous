"""Headless smoke test for backend/tui/app.py.

Drives the real `PlannerTUI` `Application` with a `prompt_toolkit`
`create_pipe_input()` pipe and a `DummyOutput()` - no real TTY needed, so this
runs fine in CI/headless environments. `SearchService.search` and
`Troubleshooter.run_diagnostics` are monkeypatched so this test never touches
the network (per docs/conventions.md, "Unit tests must not hit the network").

The scripted key sequence exercises the main interaction surface: type a
keyword, press Enter to search, cycle the source with Tab and F2, open the
troubleshooter with F1, toggle the log viewer with F3, then quit with
Ctrl-Q. The whole thing runs in a background thread with a timeout so a
hang (rather than a crash) also fails the test instead of blocking forever.

Runnable both ways:
    python -m pytest backend/tests/test_tui_app_smoke.py -q
    python backend/tests/test_tui_app_smoke.py
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from typing import Any

# Make `backend` importable as a namespace package regardless of how this
# file is invoked - see backend/tests/test_timetable.py for the same shim.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest

from backend.tui import service as tui_service
from backend.tui import troubleshooter as troubleshooter_module
from backend.tui.service import SearchResult
from backend.tui.troubleshooter import Check

# ANSI escape sequences prompt_toolkit's vt100 parser maps to the named keys
# we exercise (see prompt_toolkit.input.ansi_escape_sequences.ANSI_SEQUENCES).
# Plain characters and "\r"/"\t" are sent as literal text.
_KEY_F1 = "\x1bOP"
_KEY_F2 = "\x1bOQ"
_KEY_F3 = "\x1bOR"
_KEY_CTRL_Q = "\x11"

_STEP_DELAY = 0.15  # let the app's event loop process each step
_JOIN_TIMEOUT = 10.0


def _fake_search(self: object, source: str, keyword: str) -> list[SearchResult]:
    """Stand-in for `SearchService.search` - no network, deterministic."""
    return [SearchResult(key="CSC110Y1", title=f"CSC110Y1 ({source}: {keyword})", detail="ok")]


def _fake_diagnostics(self: object) -> list[Check]:
    """Stand-in for `Troubleshooter.run_diagnostics` - no network."""
    return [Check(name="fake check", ok=True, detail="OK", suggestion="")]


def _run_scripted_session(monkeypatch: Any) -> tuple[bool, list[BaseException]]:
    """Run the app headless with a scripted key sequence.

    Returns `(thread_finished, errors)`; `thread_finished` is False if
    `app.run()` didn't return within `_JOIN_TIMEOUT` (a hang), and `errors`
    holds any exception `app.run()` raised.
    """
    monkeypatch.setattr(tui_service.SearchService, "search", _fake_search)
    monkeypatch.setattr(troubleshooter_module.Troubleshooter, "run_diagnostics", _fake_diagnostics)

    # Imported lazily so a prompt_toolkit API mismatch surfaces as a normal
    # test failure/skip rather than an import-time error for the whole file.
    from prompt_toolkit.input.defaults import create_pipe_input
    from prompt_toolkit.output import DummyOutput

    from backend.tui.app import PlannerTUI

    errors: list[BaseException] = []

    with create_pipe_input() as pipe_input:
        tui = PlannerTUI(input=pipe_input, output=DummyOutput())

        def _run() -> None:
            try:
                tui.run()
            except BaseException as exc:  # noqa: BLE001 - captured for the assertion
                errors.append(exc)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        time.sleep(_STEP_DELAY * 2)  # let the Application start reading input

        # 1) type a keyword and press Enter to search.
        pipe_input.send_text("CSC")
        time.sleep(_STEP_DELAY)
        pipe_input.send_text("\r")
        time.sleep(_STEP_DELAY)

        # 2) cycle the search source: Tab, then F2.
        pipe_input.send_text("\t")
        time.sleep(_STEP_DELAY)
        pipe_input.send_text(_KEY_F2)
        time.sleep(_STEP_DELAY)

        # 3) open the troubleshooter overlay.
        pipe_input.send_text(_KEY_F1)
        time.sleep(_STEP_DELAY)

        # 4) toggle to the log viewer overlay.
        pipe_input.send_text(_KEY_F3)
        time.sleep(_STEP_DELAY)

        # 5) quit.
        pipe_input.send_text(_KEY_CTRL_Q)
        thread.join(timeout=_JOIN_TIMEOUT)

    return (not thread.is_alive()), errors


def test_headless_app_smoke(monkeypatch: Any) -> None:
    finished, errors = _run_scripted_session(monkeypatch)

    assert finished, "app.run() did not return within the timeout (hang)"
    assert not errors, f"app.run() raised: {errors!r}"


# ---------------------------------------------------------------------------
# Plain `python backend/tests/test_tui_app_smoke.py` runner (no pytest)
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    class _ManualMonkeypatch:
        def __init__(self) -> None:
            self._restores: list[tuple[Any, str, Any]] = []

        def setattr(self, obj: Any, name: str, value: Any) -> None:
            self._restores.append((obj, name, getattr(obj, name)))
            setattr(obj, name, value)

        def undo(self) -> None:
            for obj, name, original in reversed(self._restores):
                setattr(obj, name, original)

    mp = _ManualMonkeypatch()
    try:
        finished, errors = _run_scripted_session(mp)  # type: ignore[arg-type]
        assert finished, "app.run() did not return within the timeout (hang)"
        assert not errors, f"app.run() raised: {errors!r}"
        print("PASS test_headless_app_smoke")
    finally:
        mp.undo()

    print("\nAll test_tui_app_smoke checks passed.")
