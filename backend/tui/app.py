"""Bare-bones full-screen TUI for the UofT Degree Planner prototype.

Wraps `backend.tui.service.SearchService` and
`backend.tui.troubleshooter.Troubleshooter` in a `prompt_toolkit`
full-screen `Application`. Deliberately minimal: default prompt_toolkit
styling only (no custom `Style`/theme), a handful of widgets
(`TextArea`/`Frame`/`Window`/`Float`), and every key-binding handler is
wrapped in try/except so a data/network error becomes a status message and
a log line instead of a crash.

Launch:
    python -m backend.tui.app
    (or, from the repo root)  python backend/tui/app.py

Key bindings (also shown in the bottom hints line):
    Enter               run a search (current source) for the typed keyword
    Up/Down, Ctrl-P/N   move the selection in the results list
    Tab, F2             cycle the search source (calendar/timetable/programs)
    F5, Ctrl-G          load requirements for the selected program via Gemini
    F1, Ctrl-T          toggle the troubleshooter overlay (runs diagnostics)
    F3, Ctrl-L          toggle the log viewer overlay (tails the log file)
    Ctrl-C, Ctrl-Q       quit
"""

from __future__ import annotations

import asyncio
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Allow `python backend/tui/app.py` (no -m) to find the `backend` package.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from prompt_toolkit import Application
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    Float,
    FloatContainer,
    HSplit,
    VSplit,
    Window,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import D
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.widgets import Frame, TextArea

from backend.tui.logging_setup import setup_logging
from backend.tui.service import SearchError, SearchResult, SearchService
from backend.tui.troubleshooter import Troubleshooter

APP_NAME = "UofT Degree Planner"

HINTS = (
    "Enter: search  |  Up/Down: select  |  Tab/F2: source  |  "
    "F5/Ctrl-G: load requirements  |  F1: troubleshooter  |  "
    "F3: logs  |  Ctrl-Q: quit"
)


@dataclass
class AppState:
    """All mutable UI state, kept in one place for easy reasoning."""

    source_index: int = 0
    results: list[SearchResult] = field(default_factory=list)
    selected_index: int = 0
    status: str = "Ready."
    searching: bool = False
    show_troubleshooter: bool = False
    show_logs: bool = False

    def current_source(self) -> str:
        return SearchService.SOURCES[self.source_index]

    def selected_result(self) -> SearchResult | None:
        if 0 <= self.selected_index < len(self.results):
            return self.results[self.selected_index]
        return None


class PlannerTUI:
    """Owns the widgets, layout, key bindings and the running Application."""

    def __init__(self, input: object | None = None, output: object | None = None) -> None:
        """Build the app. `input`/`output` are optional prompt_toolkit
        Input/Output overrides used by the headless smoke test (see
        backend/tests/test_tui_app_smoke.py); left `None` for real use, in
        which case `Application` picks up the real terminal as usual.
        """
        self._logger = logging.getLogger("planner.tui")
        self._service = SearchService(self._logger)
        self._troubleshooter = Troubleshooter()
        self.state = AppState()
        # Monotonic token identifying the most-recently-started search; lets
        # `_run_search` detect it has been superseded by a later search and
        # avoid clobbering fresher results with a stale, slower response.
        self._search_seq = 0

        self.search_field = TextArea(
            multiline=False,
            prompt="search> ",
            accept_handler=self._on_search_accept,
        )
        self.results_window = Window(
            content=FormattedTextControl(self._render_results),
            wrap_lines=False,
            always_hide_cursor=True,
        )
        self.details_window = Window(
            content=FormattedTextControl(self._render_details),
            wrap_lines=True,
            always_hide_cursor=True,
        )
        self.diag_field = TextArea(read_only=True, wrap_lines=True, scrollbar=True)
        self.log_field = TextArea(read_only=True, wrap_lines=False, scrollbar=True)

        self._app = Application(
            layout=Layout(self._build_root(), focused_element=self.search_field),
            key_bindings=self._build_key_bindings(),
            full_screen=True,
            mouse_support=True,
            input=input,  # type: ignore[arg-type]
            output=output,  # type: ignore[arg-type]
        )

    # -- layout ---------------------------------------------------------

    def _build_root(self) -> FloatContainer:
        body = HSplit(
            [
                Window(
                    content=FormattedTextControl(self._render_status),
                    height=1,
                    always_hide_cursor=True,
                ),
                self.search_field,
                VSplit(
                    [
                        Frame(self.results_window, title="Results", width=D(weight=1)),
                        Frame(self.details_window, title="Details", width=D(weight=2)),
                    ]
                ),
                Window(
                    content=FormattedTextControl(HINTS),
                    height=1,
                    always_hide_cursor=True,
                ),
            ]
        )
        troubleshooter_float = Float(
            content=ConditionalContainer(
                content=Frame(
                    self.diag_field,
                    title="Troubleshooter (F1/Ctrl-T to close)",
                ),
                filter=Condition(lambda: self.state.show_troubleshooter),
            ),
            top=2,
            bottom=2,
            left=4,
            right=4,
        )
        log_float = Float(
            content=ConditionalContainer(
                content=Frame(self.log_field, title="Log viewer (F3/Ctrl-L to close)"),
                filter=Condition(lambda: self.state.show_logs),
            ),
            top=2,
            bottom=2,
            left=4,
            right=4,
        )
        return FloatContainer(content=body, floats=[troubleshooter_float, log_float])

    # -- rendering --------------------------------------------------------

    def _render_status(self) -> list[tuple[str, str]]:
        return [
            (
                "",
                f" {APP_NAME}  |  source: {self.state.current_source()}  |  "
                f"{self.state.status} ",
            )
        ]

    def _render_results(self) -> list[tuple[str, str]]:
        if self.state.searching:
            return [("", "Searching...\n")]
        if not self.state.results:
            return [("", "(no results - type a keyword and press Enter)\n")]
        lines: list[tuple[str, str]] = []
        for i, result in enumerate(self.state.results):
            is_selected = i == self.state.selected_index
            prefix = "> " if is_selected else "  "
            style = "reverse" if is_selected else ""
            if is_selected:
                # Marks this fragment's position as the control's cursor so
                # Window's built-in scroll-to-cursor logic keeps the
                # highlighted row in view (same mechanism prompt_toolkit's
                # own RadioList/CheckboxList widgets use).
                lines.append(("[SetCursorPosition]", ""))
            lines.append((style, f"{prefix}{result.key}  {result.title}\n"))
        return lines

    def _render_details(self) -> list[tuple[str, str]]:
        if self.state.searching:
            return [("", "Searching...")]
        result = self.state.selected_result()
        if result is None:
            return [("", "(select a result to see details)")]
        return [("", f"{result.title}\n\n{result.detail}")]

    def _invalidate(self) -> None:
        try:
            self._app.invalidate()
        except Exception:  # noqa: BLE001 - app may not be running yet
            pass

    # -- key bindings -----------------------------------------------------

    def _build_key_bindings(self) -> KeyBindings:
        kb = KeyBindings()
        not_overlaid = Condition(
            lambda: not self.state.show_troubleshooter and not self.state.show_logs
        )

        @kb.add("c-c")
        @kb.add("c-q")
        def _quit(event: object) -> None:
            event.app.exit()  # type: ignore[attr-defined]

        @kb.add("tab", eager=True)
        @kb.add("f2", eager=True)
        def _cycle_source(event: object) -> None:
            self._cycle_source()

        @kb.add("f1", eager=True)
        @kb.add("c-t", eager=True)
        def _toggle_troubleshooter(event: object) -> None:
            self._toggle_troubleshooter()

        @kb.add("f3", eager=True)
        @kb.add("c-l", eager=True)
        def _toggle_logs(event: object) -> None:
            self._toggle_logs()

        @kb.add("up", eager=True, filter=not_overlaid)
        @kb.add("c-p", eager=True, filter=not_overlaid)
        def _select_prev(event: object) -> None:
            self._move_selection(-1)

        @kb.add("down", eager=True, filter=not_overlaid)
        @kb.add("c-n", eager=True, filter=not_overlaid)
        def _select_next(event: object) -> None:
            self._move_selection(1)

        @kb.add("f5", eager=True, filter=not_overlaid)
        @kb.add("c-g", eager=True, filter=not_overlaid)
        def _load_reqs(event: object) -> None:
            self._load_requirements()

        return kb

    # -- handlers -----------------------------------------------------------

    def _on_search_accept(self, buff: object) -> bool:
        try:
            keyword = buff.text.strip()  # type: ignore[attr-defined]
            if not keyword:
                self.state.status = "Type a keyword and press Enter."
                self._invalidate()
                return True
            source = self.state.current_source()
            self._search_seq += 1
            token = self._search_seq
            self.state.searching = True
            self.state.status = f"Searching {source} for {keyword!r}..."
            self._invalidate()
            self._app.create_background_task(self._run_search(source, keyword, token))
        except Exception:  # noqa: BLE001 - handlers must never crash the UI
            self._logger.exception("Failed to start search")
            self.state.searching = False
            self.state.status = "Could not start search - see logs (F3)."
            self._invalidate()
        return True

    async def _run_search(self, source: str, keyword: str, token: int) -> None:
        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(None, self._service.search, source, keyword)
            if token != self._search_seq:
                # A newer search was started while this one was in flight;
                # it already owns the UI state, so drop this stale result.
                return
            self.state.results = results
            self.state.selected_index = 0
            self.state.status = f"{len(results)} result(s) for {keyword!r} in {source}."
        except SearchError as exc:
            if token != self._search_seq:
                return
            self.state.results = []
            self.state.status = str(exc)
        except Exception:  # noqa: BLE001 - handlers must never crash the UI
            self._logger.exception("Unexpected error running search")
            if token != self._search_seq:
                return
            self.state.results = []
            self.state.status = "Unexpected error during search - see logs (F3)."
        finally:
            if token == self._search_seq:
                self.state.searching = False
            self._invalidate()

    def _cycle_source(self) -> None:
        try:
            n = len(SearchService.SOURCES)
            self.state.source_index = (self.state.source_index + 1) % n
            self.state.status = f"Source: {self.state.current_source()}"
        except Exception:  # noqa: BLE001 - handlers must never crash the UI
            self._logger.exception("Failed to cycle source")
            self.state.status = "Could not change source - see logs (F3)."
        self._invalidate()

    def _move_selection(self, delta: int) -> None:
        try:
            if not self.state.results:
                return
            n = len(self.state.results)
            self.state.selected_index = (self.state.selected_index + delta) % n
        except Exception:  # noqa: BLE001 - handlers must never crash the UI
            self._logger.exception("Failed to move selection")
            self.state.status = "Selection error - see logs (F3)."
        self._invalidate()

    def _load_requirements(self) -> None:
        """Button: Gemini-load requirements for the selected program (off-thread)."""
        try:
            if self.state.current_source() != "programs":
                self.state.status = "Load requirements only applies to the 'programs' source."
                self._invalidate()
                return
            result = self.state.selected_result()
            if result is None:
                self.state.status = "Select a program first, then press F5/Ctrl-G."
                self._invalidate()
                return
            code = result.key
            index = self.state.selected_index
            self.state.status = f"Loading requirements for {code} via Gemini..."
            self._invalidate()
            self._app.create_background_task(self._run_load_requirements(code, index))
        except Exception:  # noqa: BLE001 - handlers must never crash the UI
            self._logger.exception("Failed to start load-requirements")
            self.state.status = "Could not load requirements - see logs (F3)."
            self._invalidate()

    async def _run_load_requirements(self, code: str, index: int) -> None:
        try:
            loop = asyncio.get_event_loop()
            enriched = await loop.run_in_executor(None, self._service.load_requirements, code)
            # Only update if the selected row is still the same program.
            still_current = (
                0 <= index < len(self.state.results)
                and self.state.results[index].key == code
            )
            if enriched is None:
                self.state.status = f"No cached program {code} - search first."
            elif still_current:
                self.state.results[index] = enriched
                self.state.status = f"Loaded requirements for {code}."
            else:
                self.state.status = f"Loaded requirements for {code} (selection moved)."
        except SearchError as exc:
            self.state.status = str(exc)
        except Exception:  # noqa: BLE001 - handlers must never crash the UI
            self._logger.exception("Load requirements failed")
            self.state.status = "Error loading requirements - see logs (F3)."
        finally:
            self._invalidate()

    def _toggle_troubleshooter(self) -> None:
        try:
            if self.state.show_troubleshooter:
                self.state.show_troubleshooter = False
                self.state.status = "Ready."
                self._app.layout.focus(self.search_field)
                self._invalidate()
                return
            self.state.show_logs = False
            self.state.show_troubleshooter = True
            self.state.status = "Running diagnostics..."
            self.diag_field.text = "Running diagnostics..."
            self._app.layout.focus(self.diag_field)
            self._invalidate()
            self._app.create_background_task(self._run_diagnostics())
        except Exception:  # noqa: BLE001 - handlers must never crash the UI
            self._logger.exception("Failed to toggle troubleshooter")
            self.state.status = "Troubleshooter error - see logs (F3)."
            self._invalidate()

    async def _run_diagnostics(self) -> None:
        try:
            loop = asyncio.get_event_loop()
            checks = await loop.run_in_executor(None, self._troubleshooter.run_diagnostics)
            lines = []
            for check in checks:
                mark = "OK" if check.ok else "FAIL"
                line = f"[{mark}] {check.name} - {check.detail}"
                if not check.ok and check.suggestion:
                    line += f"\n      suggestion: {check.suggestion}"
                lines.append(line)
            self.diag_field.text = "\n".join(lines) if lines else "(no diagnostics)"
            self.state.status = "Diagnostics complete."
        except Exception:  # noqa: BLE001 - handlers must never crash the UI
            self._logger.exception("Troubleshooter run failed")
            self.diag_field.text = "Troubleshooter failed - see log (F3)."
            self.state.status = "Troubleshooter error - see logs (F3)."
        finally:
            self._invalidate()

    def _toggle_logs(self) -> None:
        try:
            if self.state.show_logs:
                self.state.show_logs = False
                self.state.status = "Ready."
                self._app.layout.focus(self.search_field)
                self._invalidate()
                return
            self.state.show_troubleshooter = False
            self.state.show_logs = True
            lines = self._troubleshooter.read_recent_logs()
            self.log_field.text = "\n".join(lines) if lines else "(log is empty)"
            self.state.status = f"Showing last {len(lines)} log line(s)."
            self._app.layout.focus(self.log_field)
            self._invalidate()
        except Exception:  # noqa: BLE001 - handlers must never crash the UI
            self._logger.exception("Failed to show log viewer")
            self.state.status = "Could not read logs - see logs (F3)."
            self._invalidate()

    # -- run ----------------------------------------------------------------

    def run(self) -> None:
        self._app.run()


def main() -> None:
    setup_logging()
    logger = logging.getLogger("planner.tui")
    try:
        PlannerTUI().run()
    except Exception:
        logger.exception("Fatal error - TUI exited")
        raise


if __name__ == "__main__":
    main()
