"""Normalized, source-agnostic dataclasses shared by the TTB and Calendar clients.

These are the internal shapes the data-source clients parse *into* - callers
(cache layer, planner) work with these, not raw TTB/Calendar JSON or HTML.
All dataclasses are frozen (immutable) value objects; construct a new instance
rather than mutating one.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MeetingTime:
    """A single weekly meeting slot for a section.

    `day` is ISO-8601 (1=Mon .. 7=Sun). `start_min`/`end_min` are minutes since
    midnight, so timetable-conflict checks are plain integer comparisons.
    """

    day: int
    start_min: int
    end_min: int
    building: str
    session: str

    @classmethod
    def from_millis(
        cls,
        day: int,
        start_millis: int,
        end_millis: int,
        building: str,
        session: str,
    ) -> "MeetingTime":
        """Build from TTB's raw `millisofday` fields (see TTB_API_REFERENCE.md)."""
        return cls(
            day=day,
            start_min=start_millis // 60_000,
            end_min=end_millis // 60_000,
            building=building,
            session=session,
        )


@dataclass(frozen=True)
class Instructor:
    first: str
    last: str

    @property
    def full_name(self) -> str:
        return f"{self.first} {self.last}".strip()


@dataclass(frozen=True)
class Section:
    """One teaching-method section (LEC/TUT/PRA) of a course offering."""

    name: str
    teach_method: str
    section_number: str
    current_enrol: int
    max_enrol: int
    waitlist: int
    instructors: list[Instructor]
    meeting_times: list[MeetingTime]
    delivery_modes: list[str]

    @property
    def is_full(self) -> bool:
        return self.max_enrol > 0 and self.current_enrol >= self.max_enrol


@dataclass(frozen=True)
class Course:
    """A single course offering (one code + section_code, e.g. POL208H1 / F)."""

    code: str
    title: str
    section_code: str
    credit: float
    campus: str
    description: str
    prerequisites: str
    corequisites: str
    exclusions: str
    breadth: list[str]
    distribution: list[str]
    sections: list[Section]


@dataclass(frozen=True)
class RequirementRule:
    """One line item within a requirement group.

    `course_codes` is the set of course codes this rule references when it can
    be parsed into an explicit list; leave it empty for free-text rules the
    parser can't reduce further (see `raw_text` on `RequirementGroup`).
    """

    credits: float
    description: str
    course_codes: list[str]


@dataclass(frozen=True)
class RequirementCourse:
    """A single course listed under a requirement group.

    - `code`    the course code, e.g. "POL208H1"
    - `credits` the course's credit weight, derived from the code
                (H = 0.5, Y = 1.0)
    - `notes`   any additional information attached to this course in the
                requirement text (e.g. "only for students in the double major")
    """

    code: str
    credits: float
    notes: str = ""


@dataclass(frozen=True)
class RequirementGroup:
    """A labelled group of completion requirements and the courses under it.

    Calendar completion-requirements are organised into groups expressed
    inconsistently across programs: section headers (`First Year:`,
    `Higher Years:`), bold group titles (`Group A: ...`), numbered items, or
    `<ol><li>` lists. This captures that grouping uniformly:

    - `heading`      the group label ("" for the intro/ungrouped block)
    - `credits`      credits this group requires when stated, else 0.0
    - `is_note`      True for note/annotation blocks, not an actual requirement
    - `course_codes` every course code listed under the group (deduped)
    - `rules`        finer sub-rules (e.g. numbered items) when separable
    - `raw_text`     the group's text, for display / debugging
    - `notes`        any additional information about the group as a whole
    - `courses`      per-course detail (code + credit weight + per-course notes);
                     richer than `course_codes`, which stays the flat code list
    """

    heading: str
    credits: float
    is_note: bool
    course_codes: list[str]
    rules: list[RequirementRule]
    raw_text: str
    notes: str = ""
    courses: list[RequirementCourse] = field(default_factory=list)


@dataclass(frozen=True)
class Program:
    """A POSt (specialist/major/minor) or certificate from the Academic Calendar."""

    code: str
    title: str
    program_type: str
    department: str
    department_url: str
    enrolment_requirements: str
    total_credits: float
    completion_requirements: list[RequirementGroup]
    raw_completion_text: str
