"""Offline unit tests for backend/tui/service.py.

Monkeypatches CalendarCourseClient/TTBClient/ProgramClient at the
backend.tui.service module level so nothing here touches the network - per
docs/conventions.md ("Unit tests must not hit the network").

Runnable both ways:
    python -m pytest backend/tests/test_tui_service.py -q
    python backend/tests/test_tui_service.py
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

import pytest

from backend.data_sources.cache import SqliteCache
from backend.data_sources.models import (
    Course,
    Instructor,
    MeetingTime,
    Program,
    RequirementCourse,
    RequirementGroup,
    RequirementRule,
    Section,
)
from backend.tui import service as tui_service
from backend.tui.service import SearchError, SearchResult, SearchService


def _memory_cache() -> SqliteCache:
    return SqliteCache(":memory:")

# ---------------------------------------------------------------------------
# Fixtures: model builders and fake clients (no network, no real classes)
# ---------------------------------------------------------------------------


def _calendar_course(code: str = "POL208H1") -> Course:
    return Course(
        code=code,
        title="Politics of Development",
        section_code="",
        credit=0.5,
        campus="",
        description="An introduction to comparative politics of development.",
        prerequisites="POL200Y1",
        corequisites="",
        exclusions="POL208H5",
        breadth=["Society and its Institutions (3)"],
        distribution=[],
        sections=[],
    )


def _timetable_course(code: str = "CSC110Y1") -> Course:
    section = Section(
        name="LEC0101",
        teach_method="LEC",
        section_number="0101",
        current_enrol=45,
        max_enrol=60,
        waitlist=0,
        instructors=[Instructor(first="Jane", last="Doe")],
        meeting_times=[
            MeetingTime(day=2, start_min=600, end_min=660, building="BA", session="20239")
        ],
        delivery_modes=["INPER"],
    )
    return Course(
        code=code,
        title="Foundations of Computer Science I",
        section_code="F",
        credit=1.0,
        campus="St. George",
        description="Introductory programming.",
        prerequisites="",
        corequisites="",
        exclusions="",
        breadth=[],
        distribution=[],
        sections=[section],
    )


def _program(code: str = "ASMAJ1305A") -> Program:
    return Program(
        code=code,
        title="Geographic Data Science Major",
        program_type="major",
        department="Geography",
        department_url="https://example.org/geography",
        enrolment_requirements="Minimum 4.0 credits including GGR112H1.",
        total_credits=10.0,
        completion_requirements=[
            RequirementGroup(
                heading="First Year",
                credits=1.0,
                is_note=False,
                course_codes=["GGR112H1", "GGR172H1"],
                rules=[
                    RequirementRule(
                        credits=1.0,
                        description="1.0 credit from: GGR112H1, GGR172H1",
                        course_codes=["GGR112H1", "GGR172H1"],
                    )
                ],
                raw_text="1.0 credit from: GGR112H1, GGR172H1",
            )
        ],
        raw_completion_text="10.0 credits total ...",
    )


class _FakeCalendarClient:
    calls: list[str] = []

    def search(self, keyword: str) -> list[Course]:
        _FakeCalendarClient.calls.append(keyword)
        return [_calendar_course()]


class _FakeFailingCalendarClient:
    def search(self, keyword: str) -> list[Course]:
        raise RuntimeError("calendar boom")


class _FakeTTBClient:
    session_calls = 0

    def current_sessions(self) -> list[str]:
        _FakeTTBClient.session_calls += 1
        return ["20239"]

    def search(self, session: str, division: str = "ARTSC", course_code: str = "") -> list[Course]:
        assert session == "20239"  # Fall session (ends in 9) is preferred
        assert division == "ARTSC"
        assert course_code == ""  # full-session sync; keyword filtering is local
        return [_timetable_course("CSC110Y1"), _timetable_course("MAT137Y1")]


class _FakeTTBClientNoSessions:
    def current_sessions(self) -> list[str]:
        return []


class _FakeProgramClient:
    def search(self, keyword: str) -> list[Program]:
        return [_program()]


# ---------------------------------------------------------------------------
# SearchService.search("calendar", ...)
# ---------------------------------------------------------------------------


def test_calendar_search_maps_fields(monkeypatch: Any) -> None:
    monkeypatch.setattr(tui_service, "CalendarCourseClient", _FakeCalendarClient)

    results = SearchService().search("calendar", "POL208")

    assert len(results) == 1
    result = results[0]
    assert isinstance(result, SearchResult)
    assert result.key == "POL208H1"
    assert "Politics of Development" in result.title
    assert "Prerequisites: POL200Y1" in result.detail
    assert "Breadth: Society and its Institutions (3)" in result.detail


# ---------------------------------------------------------------------------
# SearchService.search("timetable", ...)
# ---------------------------------------------------------------------------


def test_timetable_search_resolves_and_caches_session(monkeypatch: Any) -> None:
    _FakeTTBClient.session_calls = 0
    monkeypatch.setattr(tui_service, "TTBClient", _FakeTTBClient)
    svc = SearchService(cache=_memory_cache())

    first = svc.search("timetable", "CSC110")
    second = svc.search("timetable", "CSC110")

    assert _FakeTTBClient.session_calls == 1, "session should be cached on the instance"
    assert len(first) == 1
    assert len(second) == 1
    result = first[0]
    assert result.key == "CSC110Y1"
    assert "(F)" in result.title
    assert "Sections (1):" in result.detail
    assert "45/60 enrolled" in result.detail


def test_timetable_search_raises_when_no_sessions(monkeypatch: Any) -> None:
    monkeypatch.setattr(tui_service, "TTBClient", _FakeTTBClientNoSessions)

    with pytest.raises(SearchError):
        SearchService().search("timetable", "CSC110")


# ---------------------------------------------------------------------------
# SearchService.search("programs", ...)
# ---------------------------------------------------------------------------


def test_programs_search_maps_fields(monkeypatch: Any) -> None:
    monkeypatch.setattr(tui_service, "ProgramClient", _FakeProgramClient)

    results = SearchService(
        cache=_memory_cache(), use_llm_grouping=False
    ).search("programs", "Geographic")

    assert len(results) == 1
    result = results[0]
    assert result.key == "ASMAJ1305A"
    assert "Geographic Data Science Major" in result.title
    assert "Department: Geography" in result.detail
    assert "Completion requirements:" in result.detail
    assert "First Year" in result.detail
    assert "GGR112H1" in result.detail


def test_program_search_does_not_call_gemini(monkeypatch: Any) -> None:
    # Search must stay fast: the grouper is never built during a search.
    monkeypatch.setattr(tui_service, "ProgramClient", _FakeProgramClient)
    svc = SearchService(cache=_memory_cache(), use_llm_grouping=True)

    def _boom(*_a: Any, **_k: Any) -> None:
        raise AssertionError("Gemini must not be called during a program search")

    monkeypatch.setattr(svc, "_grouper", _boom)
    results = svc.search("programs", "Geographic")
    assert len(results) == 1  # heuristic groups only, no LLM


def test_load_requirements_enriches_selected_program(monkeypatch: Any) -> None:
    from backend.data_sources.llm_grouper import GroupingResult

    monkeypatch.setattr(tui_service, "ProgramClient", _FakeProgramClient)
    svc = SearchService(cache=_memory_cache(), use_llm_grouping=True)
    svc.search("programs", "Geographic")  # caches the heuristic program first

    class _FakeGrouper:
        def group(self, _text: str) -> GroupingResult:
            grp = RequirementGroup(
                heading="Group A", credits=1.0, is_note=False,
                course_codes=["GGR112H1"], rules=[], raw_text="",
                notes="pick two departments",
                courses=[RequirementCourse(code="GGR112H1", credits=0.5, notes="req")],
            )
            return GroupingResult(groups=[grp], total_credits=10.0, report={"capture_pct": 100.0})

    svc._grouper_obj = _FakeGrouper()  # inject; no network
    card = svc.load_requirements("ASMAJ1305A")
    assert card is not None
    assert "GGR112H1 (0.5)" in card.detail
    assert "note: pick two departments" in card.detail


def test_load_requirements_unknown_code_returns_none() -> None:
    svc = SearchService(cache=_memory_cache(), use_llm_grouping=True)
    assert svc.load_requirements("ASZZZ0000") is None


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_unknown_source_raises_search_error() -> None:
    with pytest.raises(SearchError):
        SearchService().search("bogus-source", "x")


def test_calendar_search_failure_raises_search_error_and_logs(monkeypatch: Any) -> None:
    monkeypatch.setattr(tui_service, "CalendarCourseClient", _FakeFailingCalendarClient)
    logged_messages: list[str] = []

    class _RecordingLogger(logging.Logger):
        def exception(self, msg: object, *args: object, **kwargs: object) -> None:  # type: ignore[override]
            logged_messages.append(str(msg))

    with pytest.raises(SearchError, match="calendar search failed"):
        SearchService(logger=_RecordingLogger("test.tui")).search("calendar", "POL208")

    assert logged_messages, "the underlying failure should have been logged"


# ---------------------------------------------------------------------------
# Plain `python backend/tests/test_tui_service.py` runner (no pytest needed)
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

    _tests_needing_monkeypatch = [
        test_calendar_search_maps_fields,
        test_timetable_search_resolves_and_caches_session,
        test_timetable_search_raises_when_no_sessions,
        test_programs_search_maps_fields,
        test_program_search_does_not_call_gemini,
        test_load_requirements_enriches_selected_program,
        test_calendar_search_failure_raises_search_error_and_logs,
    ]
    for test_fn in _tests_needing_monkeypatch:
        mp = _ManualMonkeypatch()
        try:
            test_fn(mp)  # type: ignore[arg-type]
            print(f"PASS {test_fn.__name__}")
        finally:
            mp.undo()

    test_unknown_source_raises_search_error()
    print("PASS test_unknown_source_raises_search_error")
    test_load_requirements_unknown_code_returns_none()
    print("PASS test_load_requirements_unknown_code_returns_none")

    print("\nAll test_tui_service checks passed.")
