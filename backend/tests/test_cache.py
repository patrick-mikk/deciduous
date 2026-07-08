"""Round-trip tests for the local SQLite cache (offline, in-memory)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.data_sources.cache import SqliteCache  # noqa: E402
from backend.data_sources.models import (  # noqa: E402
    Course,
    Instructor,
    MeetingTime,
    Program,
    RequirementCourse,
    RequirementGroup,
    RequirementRule,
    Section,
)


def _course(code: str = "CSC110Y1") -> Course:
    section = Section(
        name="LEC0101",
        teach_method="LEC",
        section_number="0101",
        current_enrol=45,
        max_enrol=60,
        waitlist=3,
        instructors=[Instructor(first="Jane", last="Doe")],
        meeting_times=[MeetingTime(day=2, start_min=600, end_min=660, building="BA", session="20269")],
        delivery_modes=["In Person"],
    )
    return Course(
        code=code,
        title="Foundations of Computer Science",
        section_code="F",
        credit=1.0,
        campus="St. George",
        description="Intro programming.",
        prerequisites="",
        corequisites="",
        exclusions="",
        breadth=["The Physical and Mathematical Universes (5)"],
        distribution=["Science"],
        sections=[section],
    )


def _program() -> Program:
    return Program(
        code="ASMAJ1305A",
        title="Geographic Data Science Major",
        program_type="major",
        department="Geography and Planning",
        department_url="https://example.org",
        enrolment_requirements="Limited enrolment.",
        total_credits=7.5,
        completion_requirements=[
            RequirementGroup(
                heading="First Year",
                credits=0.5,
                is_note=False,
                course_codes=["GGR172H1"],
                rules=[RequirementRule(credits=0.5, description="0.5 from GGR172H1", course_codes=["GGR172H1"])],
                raw_text="0.5 from GGR172H1",
                notes="Complete in the first year of study.",
                courses=[RequirementCourse(code="GGR172H1", credits=0.5, notes="required")],
            )
        ],
        raw_completion_text="7.5 credits ...",
    )


def test_course_round_trip_and_prefix_search() -> None:
    cache = SqliteCache(":memory:")
    cache.upsert_courses("20269", [_course("CSC110Y1"), _course("MAT137Y1")], "now")
    assert cache.course_count("20269") == 2

    hits = cache.search_courses("20269", "CSC")
    assert [c.code for c in hits] == ["CSC110Y1"]
    got = hits[0]
    # nested value objects survive the JSON round-trip
    assert got.sections[0].meeting_times[0].day == 2
    assert got.sections[0].instructors[0].full_name == "Jane Doe"
    assert got.breadth == ["The Physical and Mathematical Universes (5)"]


def test_course_title_substring_search() -> None:
    cache = SqliteCache(":memory:")
    cache.upsert_courses("20269", [_course("CSC110Y1")], "now")
    assert [c.code for c in cache.search_courses("20269", "Foundations")] == ["CSC110Y1"]


def test_upsert_is_idempotent() -> None:
    cache = SqliteCache(":memory:")
    cache.upsert_courses("20269", [_course("CSC110Y1")], "now")
    cache.upsert_courses("20269", [_course("CSC110Y1")], "later")
    assert cache.course_count("20269") == 1


def test_program_round_trip() -> None:
    cache = SqliteCache(":memory:")
    cache.upsert_programs([_program()], "now")
    assert cache.program_count() == 1
    hits = cache.search_programs("geographic")
    assert len(hits) == 1
    prog = hits[0]
    assert prog.total_credits == 7.5
    grp = prog.completion_requirements[0]
    assert grp.heading == "First Year"
    assert grp.course_codes == ["GGR172H1"]
    # new fields survive the JSON round-trip
    assert grp.notes == "Complete in the first year of study."
    assert grp.courses[0].code == "GGR172H1"
    assert grp.courses[0].credits == 0.5
    assert grp.courses[0].notes == "required"


if __name__ == "__main__":
    test_course_round_trip_and_prefix_search()
    test_course_title_substring_search()
    test_upsert_is_idempotent()
    test_program_round_trip()
    print("OK - all cache tests passed")
