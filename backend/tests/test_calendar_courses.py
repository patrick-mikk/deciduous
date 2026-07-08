"""Unit tests for the Academic Calendar course-search client.

Run either as:
    python -m pytest backend/tests/test_calendar_courses.py
    python backend/tests/test_calendar_courses.py

The unit tests here are network-free - they parse the saved fixture
(`backend/tests/fixtures/calendar_search_courses.html`), per docs/conventions.md
("Unit tests must not hit the network"). The one live smoke test hits the real
Academic Calendar endpoint and is skipped automatically when there's no
network access, so it's safe in offline CI while still exercising the real
service when run locally/manually.
"""

from __future__ import annotations

import socket
import sys
from pathlib import Path

# Allow running as a plain script (`python backend/tests/test_calendar_courses.py`)
# in addition to `python -m pytest ...` - both need the repo root on sys.path so
# `backend.*` imports resolve.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest

from backend.data_sources.calendar_courses.client import CalendarCourseClient, parse_results
from backend.tests.conftest import fixture

FIXTURE_NAME = "calendar_search_courses.html"


def _network_available(host: str = "artsci.calendar.utoronto.ca", timeout: float = 3.0) -> bool:
    """Best-effort check for outbound network access, used to skip the live smoke test."""
    try:
        socket.create_connection((host, 443), timeout=timeout).close()
        return True
    except OSError:
        return False


def test_parse_results_returns_all_courses_on_page() -> None:
    courses = parse_results(fixture(FIXTURE_NAME))
    # The fixture page has 30 course rows (Drupal's ~30-per-page view).
    assert len(courses) == 30


def test_parse_results_first_course_matches_expected() -> None:
    courses = parse_results(fixture(FIXTURE_NAME))
    first = courses[0]
    assert first.code == "ABP100Y1"
    assert first.title == "Introduction to Academic Studies"
    assert first.credit == 1.0  # Y course -> 1.0 credit


def test_parse_results_derives_credit_from_code() -> None:
    courses = parse_results(fixture(FIXTURE_NAME))
    by_code = {c.code: c for c in courses}
    assert by_code["ABP100Y1"].credit == 1.0  # Y = full-year = 1.0
    assert by_code["ACT100H1"].credit == 0.5  # H = half = 0.5


def test_parse_results_has_nonempty_prerequisites_and_breadth() -> None:
    courses = parse_results(fixture(FIXTURE_NAME))
    with_prereq = [c for c in courses if c.prerequisites]
    with_breadth = [c for c in courses if c.breadth]
    assert with_prereq, "expected at least one course with non-empty prerequisites"
    assert with_breadth, "expected at least one course with non-empty breadth"
    # Fields the Calendar (as opposed to TTB) doesn't provide stay empty.
    assert all(c.sections == [] for c in courses)
    assert all(c.section_code == "" for c in courses)


def test_parse_results_strips_labels_and_html() -> None:
    courses = parse_results(fixture(FIXTURE_NAME))
    act230 = next(c for c in courses if c.code == "ACT230H1")
    assert "Prerequisite" not in act230.prerequisites  # label stripped
    assert "<" not in act230.prerequisites  # tags stripped
    assert act230.exclusions == "ACT240H1"


@pytest.mark.skipif(not _network_available(), reason="no network access")
def test_search_live_smoke() -> None:
    """Network-guarded: only runs when artsci.calendar.utoronto.ca is reachable."""
    client = CalendarCourseClient()
    courses = client.search("POL208", max_pages=1)
    assert courses
    assert any(c.code.startswith("POL208") for c in courses)


def main() -> int:
    html = fixture(FIXTURE_NAME)
    courses = parse_results(html)

    assert len(courses) == 30, f"expected 30 courses, got {len(courses)}"

    first = courses[0]
    assert first.code == "ABP100Y1", first.code
    assert first.title == "Introduction to Academic Studies", first.title
    assert first.credit == 1.0, first.credit

    by_code = {c.code: c for c in courses}
    assert by_code["ACT100H1"].credit == 0.5

    assert any(c.prerequisites for c in courses)
    assert any(c.breadth for c in courses)
    assert all(c.sections == [] for c in courses)

    act230 = by_code["ACT230H1"]
    assert "Prerequisite" not in act230.prerequisites
    assert "<" not in act230.prerequisites
    assert act230.exclusions == "ACT240H1"

    print(f"OK - parse_results: {len(courses)} courses from fixture")

    if _network_available():
        client = CalendarCourseClient()
        live = client.search("POL208", max_pages=1)
        assert live, "expected at least one live result for POL208"
        assert any(c.code.startswith("POL208") for c in live)
        print(f"OK - live smoke: {len(live)} course(s) for POL208")
    else:
        print("SKIP - live smoke: no network access")

    print("OK - all calendar_courses tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
