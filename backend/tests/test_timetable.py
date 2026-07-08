"""Unit tests for backend/data_sources/timetable/client.py.

Offline by design: every test except `test_live_smoke` loads the saved TTB
fixture (backend/tests/fixtures/ttb_getPageableCourses_sample.json, a real
`getPageableCourses` response) and exercises the pure `normalize_course`
function - no network. `test_live_smoke` is the one deliberate exception: it
calls the real TTB API and is guarded to skip/no-op (not fail) when there is
no network, per docs/conventions.md ("Unit tests must not hit the network").

Runnable both ways:
    python -m pytest backend/tests/test_timetable.py -q
    python backend/tests/test_timetable.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Make `backend` importable as a namespace package regardless of how this
# file is invoked (pytest rootdir insertion only adds `backend/`, not the
# repo root, because backend/tests/__init__.py exists but backend/ itself
# has none; `python backend/tests/test_timetable.py` only adds the script's
# own directory). Inserting the repo root explicitly makes both work.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest
import requests

from backend.data_sources.timetable.client import TTBClient, normalize_course

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "ttb_getPageableCourses_sample.json"


def _load_raw_courses() -> list[dict[str, Any]]:
    with FIXTURE_PATH.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return data["payload"]["pageableCourse"]["courses"]


def _find_raw_course(raw_courses: list[dict[str, Any]], code: str) -> dict[str, Any]:
    for raw in raw_courses:
        if raw["code"] == code:
            return raw
    raise AssertionError(f"fixture is missing expected course {code!r}")


def _find_raw_section(raw_course: dict[str, Any], name: str) -> dict[str, Any]:
    for raw in raw_course["sections"]:
        if raw["name"] == name:
            return raw
    raise AssertionError(f"course {raw_course['code']!r} is missing expected section {name!r}")


# ---------------------------------------------------------------------------
# normalize_course: basic top-level fields
# ---------------------------------------------------------------------------


def test_normalize_course_basic_fields() -> None:
    raw_courses = _load_raw_courses()
    raw = _find_raw_course(raw_courses, "ACT230H1")
    course = normalize_course(raw)

    assert course.code == "ACT230H1"
    assert course.title == "Mathematics of Finance for Non-Actuaries"
    assert course.section_code == "F"
    assert course.credit == 0.5
    assert course.campus == "St. George"


# ---------------------------------------------------------------------------
# normalize_course: HTML stripping on the cmCourseInfo *Text fields
# ---------------------------------------------------------------------------


def test_normalize_course_strips_html_prerequisites() -> None:
    raw_courses = _load_raw_courses()
    raw = _find_raw_course(raw_courses, "ACT240H1")
    # Sanity-check the fixture actually contains HTML to strip, so this test
    # would fail loudly if the fixture changed shape.
    assert "<" in (raw["cmCourseInfo"]["prerequisitesText"] or "")

    course = normalize_course(raw)

    assert course.prerequisites != ""
    assert "<" not in course.prerequisites
    assert ">" not in course.prerequisites
    assert "MAT137Y1" in course.prerequisites


# ---------------------------------------------------------------------------
# normalize_course: breadth requirements list
# ---------------------------------------------------------------------------


def test_normalize_course_breadth_list() -> None:
    raw_courses = _load_raw_courses()
    raw = _find_raw_course(raw_courses, "ACT230H1")
    course = normalize_course(raw)

    assert isinstance(course.breadth, list)
    assert course.breadth == ["The Physical and Mathematical Universes (5)"]
    assert course.distribution == ["Science"]


# ---------------------------------------------------------------------------
# normalize_course: sections + parsed MeetingTime
# ---------------------------------------------------------------------------


def test_normalize_course_section_and_meeting_time() -> None:
    raw_courses = _load_raw_courses()
    raw_course = _find_raw_course(raw_courses, "ACT230H1")
    raw_section = _find_raw_section(raw_course, "TUT0101")
    raw_meeting = raw_section["meetingTimes"][0]
    # Fixture ground truth: day 5 (Friday), 43_200_000ms -> 720min (12:00),
    # 46_800_000ms -> 780min (13:00), building MS.
    assert raw_meeting["start"]["day"] == 5
    assert raw_meeting["start"]["millisofday"] == 43_200_000
    assert raw_meeting["end"]["millisofday"] == 46_800_000

    course = normalize_course(raw_course)
    section = next(s for s in course.sections if s.name == "TUT0101")

    assert section.teach_method == "TUT"
    assert section.section_number == "0101"
    assert section.max_enrol == 60
    assert len(section.meeting_times) >= 1

    meeting = section.meeting_times[0]
    assert meeting.day == 5
    assert meeting.start_min == 720  # 12:00
    assert meeting.end_min == 780  # 13:00
    assert meeting.building == "MS"
    assert meeting.session == "20269"


def test_normalize_course_instructor() -> None:
    raw_courses = _load_raw_courses()
    raw_course = _find_raw_course(raw_courses, "ACT240H1")
    raw_section = _find_raw_section(raw_course, "LEC0101")
    assert raw_section["instructors"], "fixture expected at least one instructor here"

    course = normalize_course(raw_course)
    section = next(s for s in course.sections if s.name == "LEC0101")

    assert len(section.instructors) >= 1
    assert section.instructors[0].full_name == "Christopher Blier-Wong"


def test_normalize_course_handles_missing_optional_fields() -> None:
    """A minimal/sparse raw course object should normalize without raising."""
    raw = {"code": "XXX100H1", "name": "Minimal Course"}
    course = normalize_course(raw)

    assert course.code == "XXX100H1"
    assert course.title == "Minimal Course"
    assert course.credit == 0.0
    assert course.prerequisites == ""
    assert course.breadth == []
    assert course.sections == []


def test_search_treats_no_results_as_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """A search with zero matches (TTB's 404-with-null-payload quirk) must
    come back as an empty list, not raise."""
    import backend.data_sources.timetable.client as client_module

    monkeypatch.setattr(client_module, "post_json", lambda url, body: None)

    client = TTBClient()
    assert client.search(session="20265", division="ARTSC", course_code="ZZZZZ") == []


def test_search_paginates_by_running_total(monkeypatch: pytest.MonkeyPatch) -> None:
    """search() must keep requesting pages until the collected count reaches
    `total`, even though TTB caps each page well below the requested size."""
    import backend.data_sources.timetable.client as client_module

    raw_courses = _load_raw_courses()
    # Simulate TTB's real behaviour: 45 total courses, ~20 returned per page,
    # regardless of the pageSize this client requests.
    fake_total = 45
    page_contents = {
        1: raw_courses[0:20],
        2: raw_courses[0:20],
        3: raw_courses[0:5],
    }
    calls: list[int] = []

    def fake_post_json(url: str, body: dict[str, Any]) -> dict[str, Any] | None:
        page = body["page"]
        calls.append(page)
        courses = page_contents.get(page, [])
        if not courses:
            return None
        return {"payload": {"pageableCourse": {"total": fake_total, "courses": courses}}}

    monkeypatch.setattr(client_module, "post_json", fake_post_json)

    client = TTBClient()
    results = client.search(session="20265", division="ARTSC")

    assert calls == [1, 2, 3]
    assert len(results) == 45
    assert all(hasattr(c, "code") for c in results)


# ---------------------------------------------------------------------------
# Live smoke test - real network, guarded to skip/no-op when unreachable.
# ---------------------------------------------------------------------------


def _live_smoke_check() -> str:
    """Call current_sessions() and a small search() against the real TTB API.

    Returns "ok" on success, "skipped" if the network/service is unavailable
    (connection error, timeout, or no usable sessions) - this is a smoke
    check, not a correctness test, so it must never hard-fail a normal
    offline unit-test run.
    """
    client = TTBClient()
    try:
        sessions = client.current_sessions()
    except requests.exceptions.RequestException:
        return "skipped"

    if not sessions:
        return "skipped"

    try:
        courses = client.search(session=sessions[0], division="ARTSC", course_code="ACT")
    except requests.exceptions.RequestException:
        return "skipped"

    assert isinstance(courses, list)
    for course in courses:
        assert course.code.startswith("ACT")
        assert course.sections is not None
    return "ok"


def test_live_smoke() -> None:
    result = _live_smoke_check()
    if result == "skipped":
        pytest.skip("TTB API unreachable or returned nothing usable (offline dev environment)")


if __name__ == "__main__":

    def _run(name: str, fn) -> None:  # type: ignore[no-untyped-def]
        fn()
        print(f"PASS {name}")

    _run("test_normalize_course_basic_fields", test_normalize_course_basic_fields)
    _run(
        "test_normalize_course_strips_html_prerequisites",
        test_normalize_course_strips_html_prerequisites,
    )
    _run("test_normalize_course_breadth_list", test_normalize_course_breadth_list)
    _run(
        "test_normalize_course_section_and_meeting_time",
        test_normalize_course_section_and_meeting_time,
    )
    _run("test_normalize_course_instructor", test_normalize_course_instructor)
    _run(
        "test_normalize_course_handles_missing_optional_fields",
        test_normalize_course_handles_missing_optional_fields,
    )

    # The two monkeypatch-based tests use pytest's fixture; drive them by
    # hand here with a tiny stand-in so `python test_timetable.py` needs no
    # pytest session.
    class _ManualMonkeypatch:
        def __init__(self) -> None:
            self._restores: list[tuple[Any, str, Any]] = []

        def setattr(self, obj: Any, name: str, value: Any) -> None:
            self._restores.append((obj, name, getattr(obj, name)))
            setattr(obj, name, value)

        def undo(self) -> None:
            for obj, name, original in self._restores:
                setattr(obj, name, original)

    mp = _ManualMonkeypatch()
    try:
        test_search_treats_no_results_as_empty(mp)  # type: ignore[arg-type]
        print("PASS test_search_treats_no_results_as_empty")
    finally:
        mp.undo()

    mp = _ManualMonkeypatch()
    try:
        test_search_paginates_by_running_total(mp)  # type: ignore[arg-type]
        print("PASS test_search_paginates_by_running_total")
    finally:
        mp.undo()

    live_result = _live_smoke_check()
    print(f"{'PASS' if live_result == 'ok' else 'SKIPPED'} test_live_smoke ({live_result})")

    print("\nAll test_timetable checks passed.")
