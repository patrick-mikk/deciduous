"""Regression tests for two `backend/tui/app.py` bugs found in review:

1. Stale-search race: `_run_search` used to unconditionally overwrite
   `state.results`/`state.status` when it returned, so a slow, earlier
   search that finished *after* a faster, later search could clobber the
   UI with stale data. `_run_search` now takes a `token` (a snapshot of
   `PlannerTUI._search_seq` at dispatch time) and only mutates state when
   `token == self._search_seq` (i.e. it is still the most recently started
   search).

2. Results pane auto-scroll: `_render_results` used to never emit a
   `("[SetCursorPosition]", "")` fragment, so prompt_toolkit's `Window`
   auto-scroll (which is driven entirely by the control's cursor position)
   could never follow `state.selected_index` once it scrolled out of view.
   `_render_results` now emits that marker immediately before the selected
   row's fragment - the same mechanism prompt_toolkit's own
   `RadioList`/`CheckboxList` widgets use.

No network access: `SearchService.search` is monkeypatched throughout, per
docs/conventions.md ("Unit tests must not hit the network").

Runnable both ways:
    python -m pytest backend/tests/test_tui_app_units.py -q
    python backend/tests/test_tui_app_units.py
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from typing import Any

# Make `backend` importable as a namespace package regardless of how this
# file is invoked - see backend/tests/test_timetable.py for the same shim.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest

from backend.tui.service import SearchResult, SearchService


def _make_tui() -> Any:
    """Build a headless `PlannerTUI` (no real TTY, no `app.run()`).

    Returns `(tui, pipe_input)`; `pipe_input` is the already-`__enter__`-ed
    context manager from `create_pipe_input()` - callers must
    `pipe_input.__exit__(None, None, None)` when done (see the `try/finally`
    blocks below), matching the pattern in test_tui_app_smoke.py.
    """
    from prompt_toolkit.input.defaults import create_pipe_input
    from prompt_toolkit.output import DummyOutput

    from backend.tui.app import PlannerTUI

    pipe_input_cm = create_pipe_input()
    pipe_input = pipe_input_cm.__enter__()
    tui = PlannerTUI(input=pipe_input, output=DummyOutput())
    return tui, pipe_input_cm


def test_stale_search_does_not_clobber_newer_results(monkeypatch: Any) -> None:
    """A slow search that started first must not overwrite a fast search
    that started later and already returned - see backend/tui/app.py's
    `_run_search` token guard."""
    delays = {"SLOW": 0.3, "FAST": 0.05}

    def _fake_search(self: object, source: str, keyword: str) -> list[SearchResult]:
        time.sleep(delays[keyword])
        return [SearchResult(key=keyword, title=keyword, detail="ok")]

    monkeypatch.setattr(SearchService, "search", _fake_search)

    tui, pipe_input = _make_tui()
    try:

        async def scenario() -> None:
            # Mirrors _on_search_accept's token bookkeeping without needing
            # a running Application event loop.
            tui._search_seq = 1
            slow_task = asyncio.create_task(tui._run_search("calendar", "SLOW", 1))
            await asyncio.sleep(0.01)  # let SLOW start before FAST is dispatched
            tui._search_seq = 2
            fast_task = asyncio.create_task(tui._run_search("timetable", "FAST", 2))
            await asyncio.gather(slow_task, fast_task)

        asyncio.run(scenario())

        assert [r.key for r in tui.state.results] == ["FAST"]
        assert "FAST" in tui.state.status
        assert tui.state.searching is False
    finally:
        pipe_input.__exit__(None, None, None)


def test_render_results_marks_selected_row_cursor_position() -> None:
    """`_render_results` must emit a `[SetCursorPosition]` fragment right
    before the selected row so `Window`'s auto-scroll can follow selection
    (see backend/tui/app.py `_render_results`)."""
    tui, pipe_input = _make_tui()
    try:
        tui.state.results = [
            SearchResult(key="AAA100H1", title="Course A", detail=""),
            SearchResult(key="BBB200H1", title="Course B", detail=""),
            SearchResult(key="CCC300H1", title="Course C", detail=""),
        ]
        tui.state.selected_index = 2

        fragments = tui._render_results()

        marker_indices = [i for i, f in enumerate(fragments) if f == ("[SetCursorPosition]", "")]
        assert len(marker_indices) == 1, "exactly one row should carry the cursor marker"
        marker_index = marker_indices[0]

        # The fragment immediately after the marker must be the selected row.
        next_style, next_text = fragments[marker_index + 1]
        assert "CCC300H1" in next_text
        assert next_style == "reverse"
    finally:
        pipe_input.__exit__(None, None, None)


def test_render_results_no_marker_when_empty() -> None:
    """No results -> no crash and no stray cursor marker."""
    tui, pipe_input = _make_tui()
    try:
        tui.state.results = []
        fragments = tui._render_results()
        assert ("[SetCursorPosition]", "") not in fragments
    finally:
        pipe_input.__exit__(None, None, None)


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
        test_stale_search_does_not_clobber_newer_results(mp)  # type: ignore[arg-type]
        print("PASS test_stale_search_does_not_clobber_newer_results")
        test_render_results_marks_selected_row_cursor_position()
        print("PASS test_render_results_marks_selected_row_cursor_position")
        test_render_results_no_marker_when_empty()
        print("PASS test_render_results_no_marker_when_empty")
    finally:
        mp.undo()

    print("\nAll test_tui_app_units checks passed.")
