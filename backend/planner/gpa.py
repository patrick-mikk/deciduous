"""GPA scale, SGPA/AGPA/CGPA computation, grade notations, and academic
standing — `design/09-uoft-degree-rules.md` §6.

Pure functions over `planner.types.CourseRecord`; no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.planner.types import CourseRecord

# ---------------------------------------------------------------------------
# Grade scale (design/09-uoft-degree-rules.md §6)
# ---------------------------------------------------------------------------

# (minimum %, letter, grade points), checked highest-first.
_MARK_BANDS: tuple[tuple[int, str, float], ...] = (
    (90, "A+", 4.0),
    (85, "A", 4.0),
    (80, "A-", 3.7),
    (77, "B+", 3.3),
    (73, "B", 3.0),
    (70, "B-", 2.7),
    (67, "C+", 2.3),
    (63, "C", 2.0),
    (60, "C-", 1.7),
    (57, "D+", 1.3),
    (53, "D", 1.0),
    (50, "D-", 0.7),
    (0, "F", 0.0),
)

LETTER_POINTS: dict[str, float] = {letter: points for _, letter, points in _MARK_BANDS}

# Grade *notations* excluded from GPA (but the CR/NCR pair, Extra, etc. still
# count toward the 20.0 total and breadth — see `validators.py`). `FL` is
# deliberately NOT in this set: per the calendar, "FL/failure = 0.0 if
# calculated" — i.e. it's included in GPA math as a fail, unlike the rest.
NOTATIONS_EXCLUDED_FROM_GPA: frozenset[str] = frozenset(
    {"AEG", "CR", "NCR", "EXT", "XTR", "GWR", "IPR", "LWD", "WDR", "SDF", "P"}
)

PASSING_NOTATIONS: frozenset[str] = frozenset({"P", "CR"})
FAILING_NOTATIONS: frozenset[str] = frozenset({"NCR", "FL"})

GRADUATION_MIN_CGPA = 1.85
GOOD_STANDING_MIN_CGPA = 1.50
PROBATION_MIN_RECENT_GPA = 1.70
PROBATION_CREDIT_CAP = {"fall": 2.5, "winter": 2.5, "summer": 1.0}


def letter_for_mark(mark: float) -> str:
    """The letter grade for a numeric percentage mark (0-100)."""
    if not 0 <= mark <= 100:
        raise ValueError(f"mark must be in [0, 100], got {mark!r}")
    for minimum, letter, _ in _MARK_BANDS:
        if mark >= minimum:
            return letter
    raise AssertionError("unreachable: bands cover [0, 100]")  # pragma: no cover


def points_for_mark(mark: float) -> float:
    """The grade-point value (0.0-4.0) for a numeric percentage mark."""
    return LETTER_POINTS[letter_for_mark(mark)]


# ---------------------------------------------------------------------------
# Per-course grade-point resolution
# ---------------------------------------------------------------------------


def grade_points(record: CourseRecord) -> tuple[float | None, bool]:
    """`(points, counts_toward_gpa)` for one course record.

    Resolution order: an explicit `grade` notation/letter wins over a raw
    `mark`. Planned and Extra courses never count. A course with neither a
    recognizable grade nor a mark can't be resolved -> `(None, False)`.
    """
    if record.status in ("planned", "extra"):
        return (None, False)

    grade = (record.grade or "").strip().upper()
    if grade:
        if grade in NOTATIONS_EXCLUDED_FROM_GPA:
            return (None, False)
        if grade == "FL":
            return (0.0, True)
        if grade in LETTER_POINTS:
            return (LETTER_POINTS[grade], True)
        # Unrecognized grade string: fall through to `mark`, if any.

    if record.mark is not None:
        return (points_for_mark(record.mark), True)

    return (None, False)


def is_passing(record: CourseRecord) -> bool:
    """"Passing grade = 50% / P / CR" (design/09-uoft-degree-rules.md §1)."""
    grade = (record.grade or "").strip().upper()
    if grade in PASSING_NOTATIONS:
        return True
    if grade in FAILING_NOTATIONS:
        return False
    if record.mark is not None:
        return record.mark >= 50
    if grade in LETTER_POINTS:
        return grade not in ("F",)
    return False


# ---------------------------------------------------------------------------
# SGPA / AGPA / CGPA
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GpaSummary:
    gpa: float | None  # None when there are no GPA-countable credits
    credits_counted: float
    courses_counted: int


def compute_gpa(records: list[CourseRecord]) -> GpaSummary:
    """Weighted-average GPA (weight = course credit value) over whichever
    `records` the caller passes in — filter by session first for SGPA/AGPA,
    or pass the whole transcript for CGPA."""
    weighted_total = 0.0
    credits_counted = 0.0
    courses_counted = 0
    for record in records:
        points, counts = grade_points(record)
        if not counts or points is None:
            continue
        weighted_total += points * record.credits
        credits_counted += record.credits
        courses_counted += 1

    if credits_counted <= 0:
        return GpaSummary(gpa=None, credits_counted=0.0, courses_counted=0)
    return GpaSummary(
        gpa=round(weighted_total / credits_counted, 3),
        credits_counted=round(credits_counted, 2),
        courses_counted=courses_counted,
    )


def sgpa(records: list[CourseRecord], session: str) -> GpaSummary:
    """SGPA: one session (a single Fall, Winter, or whole-Summer session code)."""
    return compute_gpa([r for r in records if r.session == session])


def agpa(records: list[CourseRecord], sessions: list[str]) -> GpaSummary:
    """AGPA: Fall + Winter of one academic year — pass both session codes."""
    session_set = set(sessions)
    return compute_gpa([r for r in records if r.session in session_set])


def cgpa(records: list[CourseRecord]) -> GpaSummary:
    """CGPA: every session, i.e. the whole transcript."""
    return compute_gpa(records)


# ---------------------------------------------------------------------------
# Academic standing
# ---------------------------------------------------------------------------

Standing = str  # "good" | "probation" | "suspension" | "refused"


def academic_standing(
    cgpa_value: float, recent_gpa_value: float, previously_suspended: bool = False
) -> Standing:
    """Good >= 1.50 CGPA; Probation if CGPA < 1.50 but the most recent
    sessional/annual GPA is >= 1.70; Suspension if both are below threshold.
    `previously_suspended=True` escalates a second suspension to "refused"
    (the calendar text doesn't fully specify this progression — treated as a
    conservative best-effort extension, not a hard rule)."""
    if cgpa_value >= GOOD_STANDING_MIN_CGPA:
        return "good"
    if recent_gpa_value >= PROBATION_MIN_RECENT_GPA:
        return "probation"
    return "refused" if previously_suspended else "suspension"


def max_credits_for_term(standing: Standing, term_type: str) -> float | None:
    """The course-load cap implied by `standing` for a term of `term_type`
    ("fall" | "winter" | "summer"). `None` means "no cap" (good standing)."""
    if term_type not in PROBATION_CREDIT_CAP:
        raise ValueError(f'term_type must be one of {sorted(PROBATION_CREDIT_CAP)}, got {term_type!r}')
    if standing == "probation":
        return PROBATION_CREDIT_CAP[term_type]
    if standing in ("suspension", "refused"):
        return 0.0
    return None


def meets_graduation_gpa(cgpa_value: float) -> bool:
    """CGPA >= 1.85 — the GPA half of graduation eligibility (§1, §7); the
    other half (good standing, credit/level/program requirements) lives in
    `validators.py`."""
    return cgpa_value >= GRADUATION_MIN_CGPA
