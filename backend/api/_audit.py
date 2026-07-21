"""Pure degree-audit math shared by `backend/api/me.py`'s summary/alerts/
requirements endpoints (and reused by `backend/api/import_.py`'s import
preview response). Implements `design/09-uoft-degree-rules.md` section 7
("What the app must compute").

Deliberately NOT `backend/planner/` -- that package's docstring reserves it
for the full prereq/exclusion/enrolment-eligibility validator engine (design/
09 items 5-6), which is a separate build outside this file's ownership. This
module only covers items 1-4 (degree progress, program combination credits,
breadth, GPA/standing) -- what `/api/me/*` actually needs to render the
dashboard and requirements views.

Every function here takes plain dataclasses (`TranscriptRow`/`ProgramRow`),
never SQLAlchemy models or Flask request objects, so it's unit-testable with
synthetic data (`backend/tests/test_audit.py`) independent of the DB/HTTP
layers. `backend/api/me.py` is the adapter that builds these rows from
`TranscriptEntry`/`ProgramEnrolment` and calls in here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from backend.data_sources.models import Program
from backend.ingest.degree_explorer import (
    GRADE_POINTS,
    NOTATIONS_EXCLUDED_FROM_GPA,
    mark_to_letter,
)
from backend.planner.course_code import parse_course_code
from backend.planner.validators import PROGRAM_MIN_CREDITS

# Degree-wide thresholds, design/09-uoft-degree-rules.md section 1.
TOTAL_CREDITS_REQUIRED = 20.0


def effective_total_credits(program: Program) -> float:
    """The single source of truth for a program's total required credits.

    The Calendar/grouper only sometimes states a program-level total, so
    `program.total_credits` is frequently 0.0 (e.g. the Economics Major, whose
    requirements are given as groups with no summary line). A bare 0.0 makes
    every "X / 0.0 cr" / "0% complete" summary look broken next to a detailed
    breakdown that clearly totals more. So fall back, in order:

    1. the parsed program total, when > 0;
    2. otherwise the largest single requirement group's credits — for a program
       written as one umbrella "Program Course Requirements N.0" group plus
       sub-groups, that umbrella *is* the real total (and is exactly what the
       breakdown shows), so we never sum overlapping groups and over-count;
    3. otherwise the standard minimum for the program type.

    Every place that shows a program denominator (the search/detail serializers
    and `program_progress_summary`) routes through here, so the top-of-page
    summary and the group breakdown can never disagree on the total.
    """
    if program.total_credits and program.total_credits > 0:
        return program.total_credits
    group_max = max(
        (g.credits for g in program.completion_requirements if not g.is_note and g.credits > 0),
        default=0.0,
    )
    return max(group_max, PROGRAM_MIN_CREDITS.get(program.program_type, 0.0))
ARTSCI_CREDITS_REQUIRED = 10.0
LEVEL200_CREDITS_REQUIRED = 13.0
LEVEL300_CREDITS_REQUIRED = 6.0
SAME_SUBJECT_CREDITS_CAP = 15.0
DISTINCT_CREDITS_REQUIRED_MULTI_PROGRAM = 12.0
GRADUATION_CGPA_MINIMUM = 1.85
GOOD_STANDING_CGPA_MINIMUM = 1.50
PROBATION_SESSIONAL_MINIMUM = 1.70

BREADTH_CATEGORIES = {
    1: "Creative and Cultural Representations",
    2: "Thought, Belief, and Behaviour",
    3: "Society and Its Institutions",
    4: "Living Things and Their Environment",
    5: "The Physical and Mathematical Universes",
}

_EARNED_STATUSES = {"completed", "in_progress"}
_BREADTH_SUFFIX_RE = re.compile(r"\((\d)\)\s*$")


@dataclass(frozen=True)
class TranscriptRow:
    """One transcript course, decoupled from the `TranscriptEntry` DB model
    so this module never imports SQLAlchemy. `is_artsci` defaults to True --
    every course offered through this planner is an Arts & Science course
    unless the caller has real `Course.distribution` data saying otherwise
    (see `design/09-uoft-degree-rules.md` section 5)."""

    code: str
    credits: float
    status: str  # completed | in_progress | planned | extra
    session: str = ""
    grade: str = ""
    mark: float | None = None
    is_artsci: bool = True


@dataclass(frozen=True)
class ProgramRow:
    code: str
    title: str = ""
    program_type: str = ""


def _earned(rows: list[TranscriptRow]) -> list[TranscriptRow]:
    """Completed + in-progress rows -- what counts toward credits/GPA.
    `extra` (Second Attempt for Credit) and `planned` (future) are excluded."""
    return [r for r in rows if r.status in _EARNED_STATUSES]


# --------------------------------------------------------------- degree progress
def degree_progress(rows: list[TranscriptRow]) -> dict:
    """design/09 section 7 item 1: total/ArtSci/200+/300+ credits, same-
    subject cap. NOTE: the <=1.0-transfer-credit carve-out for the 300+
    minimum isn't modelled -- `TranscriptEntry` has no transfer-credit flag
    at the DB layer this reads from."""
    earned = _earned(rows)

    total = 0.0
    artsci = 0.0
    level200 = 0.0
    level300 = 0.0
    by_subject: dict[str, float] = {}

    for row in earned:
        total += row.credits
        if row.is_artsci:
            artsci += row.credits
        cc = parse_course_code(row.code)
        if cc is not None:
            if cc.level >= 200:
                level200 += row.credits
            if cc.level >= 300:
                level300 += row.credits
            by_subject[cc.subject] = by_subject.get(cc.subject, 0.0) + row.credits

    same_subject_top = max(by_subject.items(), key=lambda kv: kv[1]) if by_subject else None
    planned = sum(r.credits for r in rows if r.status == "planned")

    return {
        "totalCredits": round(total, 2),
        "totalRequired": TOTAL_CREDITS_REQUIRED,
        "plannedCredits": round(planned, 2),
        "artsciCredits": round(artsci, 2),
        "artsciRequired": ARTSCI_CREDITS_REQUIRED,
        "level200Credits": round(level200, 2),
        "level200Required": LEVEL200_CREDITS_REQUIRED,
        "level300Credits": round(level300, 2),
        "level300Required": LEVEL300_CREDITS_REQUIRED,
        "creditsBySubject": {k: round(v, 2) for k, v in by_subject.items()},
        "sameSubjectSubject": same_subject_top[0] if same_subject_top else None,
        "sameSubjectCredits": round(same_subject_top[1], 2) if same_subject_top else 0.0,
        "sameSubjectCap": SAME_SUBJECT_CREDITS_CAP,
        "sameSubjectOverCap": bool(same_subject_top and same_subject_top[1] > SAME_SUBJECT_CREDITS_CAP),
        "percentComplete": round(min(total / TOTAL_CREDITS_REQUIRED, 1.0) * 100, 1)
        if TOTAL_CREDITS_REQUIRED
        else 0.0,
    }


# ------------------------------------------------------------------------ breadth
def _breadth_category(label: str) -> int | None:
    """"Society and its Institutions (3)" -> 3. None if unparseable."""
    m = _BREADTH_SUFFIX_RE.search(label)
    if not m:
        return None
    n = int(m.group(1))
    return n if n in BREADTH_CATEGORIES else None


def breadth_progress(rows: list[TranscriptRow], breadth_by_code: dict[str, list[str]]) -> dict:
    """design/09 section 4 + section 7 item 3.

    `breadth_by_code` maps course code -> `Course.breadth` labels (from the
    catalog cache); a course with no entry contributes nothing (unknown, not
    zero -- `design/06-data-model-and-api.md`: "Surface it, don't gate on
    it"). credits are split evenly across however many categories a course's
    breadth list names (1 for a straight H/Y course, 2 for a split Y course).
    """
    # CR/NCR and planned courses still count toward breadth per design/09
    # ("CR/NCR courses can still count toward breadth"); only `extra`
    # (Second Attempt for Credit) rows are excluded.
    counted = [r for r in rows if r.status != "extra"]

    totals: dict[int, float] = {n: 0.0 for n in BREADTH_CATEGORIES}
    for row in counted:
        labels = breadth_by_code.get(row.code) or []
        categories = [c for c in (_breadth_category(l) for l in labels) if c is not None]
        if not categories:
            continue
        share = row.credits / len(categories)
        for cat in categories:
            totals[cat] += share

    full = [n for n, credits in totals.items() if credits >= 1.0 - 1e-9]
    half_plus = [n for n, credits in totals.items() if credits >= 0.5 - 1e-9]

    option_4of5 = len(full) >= 4
    option_3plus2 = len(full) >= 3 and len(half_plus) >= 5
    satisfied = option_4of5 or option_3plus2
    option_used = "4of5" if option_4of5 else ("3plus2" if option_3plus2 else None)

    missing: list[str] = []
    if not satisfied:
        # Closest path to satisfying: top up whichever categories are short
        # of 0.5, favouring the "3 full + 2 half" option once 3 are already full.
        for n in sorted(BREADTH_CATEGORIES):
            credits = totals[n]
            need = (1.0 if len(full) < 3 else 0.5) - credits
            if need > 1e-9:
                missing.append(f"Need {need:.1f} more credit(s) in BR{n} ({BREADTH_CATEGORIES[n]})")

    return {
        "categories": {n: round(v, 2) for n, v in totals.items()},
        "categoryLabels": BREADTH_CATEGORIES,
        "satisfiedCount": len(full),
        "satisfied": satisfied,
        "optionUsed": option_used,
        "missing": missing,
    }


# ---------------------------------------------------------------------------- GPA
def _grade_point(row: TranscriptRow) -> float | None:
    """The grade-point value counted toward GPA for `row`, or None if it's
    excluded (a notation like CR/NCR/IPR, or no grade/mark recorded yet)."""
    grade = (row.grade or "").strip().upper()
    if grade in NOTATIONS_EXCLUDED_FROM_GPA:
        return None
    if grade in GRADE_POINTS:
        return GRADE_POINTS[grade]
    if row.mark is not None:
        return GRADE_POINTS[mark_to_letter(row.mark)]
    return None


def _weighted_gpa(rows: list[TranscriptRow]) -> float | None:
    total_credits = 0.0
    total_points = 0.0
    for row in rows:
        gp = _grade_point(row)
        if gp is None:
            continue
        total_credits += row.credits
        total_points += gp * row.credits
    return round(total_points / total_credits, 3) if total_credits > 0 else None


def _academic_year_label(session: str) -> str | None:
    """"20269" (Fall 2026) or "20271" (Winter 2027) -> "2026-2027"."""
    if len(session) != 5 or not session.isdigit():
        return None
    year, term = int(session[:4]), session[4]
    if term == "9":  # Fall
        return f"{year}-{year + 1}"
    if term == "1":  # Winter
        return f"{year - 1}-{year}"
    return None  # Summer stands alone, not part of an F/W academic year


def gpa_summary(rows: list[TranscriptRow]) -> dict:
    """design/09 section 6 + section 7 item 4: CGPA, per-session SGPA,
    per-academic-year AGPA (Fall+Winter), latest-session GPA, standing."""
    counted = [r for r in rows if r.status in _EARNED_STATUSES]

    sessions: dict[str, list[TranscriptRow]] = {}
    for row in counted:
        if row.session:
            sessions.setdefault(row.session, []).append(row)

    sgpa = {session: _weighted_gpa(group) for session, group in sessions.items()}
    sgpa = {k: v for k, v in sgpa.items() if v is not None}

    years: dict[str, list[TranscriptRow]] = {}
    for row in counted:
        label = _academic_year_label(row.session)
        if label:
            years.setdefault(label, []).append(row)
    agpa = {label: v for label, group in years.items() if (v := _weighted_gpa(group)) is not None}

    cgpa = _weighted_gpa(counted)
    latest_session = max(sgpa.keys(), default=None)
    latest_session_gpa = sgpa.get(latest_session) if latest_session else None

    return {
        "cgpa": cgpa,
        "sgpaBySession": sgpa,
        "agpaByYear": agpa,
        "latestSession": latest_session,
        "latestSessionGpa": latest_session_gpa,
        "standing": standing(cgpa, latest_session_gpa),
        "graduationEligible": cgpa is not None and cgpa >= GRADUATION_CGPA_MINIMUM,
    }


def standing(cgpa: float | None, sessional_or_annual_gpa: float | None) -> str:
    """design/09 section 6: Good >= 1.50 CGPA; else Probation if sessional/
    annual >= 1.70; else Suspension. "unknown" when there's no GPA data yet."""
    if cgpa is None:
        return "unknown"
    if cgpa >= GOOD_STANDING_CGPA_MINIMUM:
        return "good"
    if sessional_or_annual_gpa is not None and sessional_or_annual_gpa >= PROBATION_SESSIONAL_MINIMUM:
        return "probation"
    return "suspension"


# ----------------------------------------------------------------- requirements
def _slugify(text: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")
    return slug or fallback


def requirement_progress(program: Program, rows: list[TranscriptRow]) -> list[dict]:
    """Cross-reference one program's `RequirementGroup`s against the
    student's transcript -- `RequirementProgress[]` per `design/06-data-
    model-and-api.md`. A course counts toward a group once it appears in
    that group's `course_codes` and the student has completed/is taking it.
    """
    earned_codes = {r.code for r in _earned(rows)}
    out: list[dict] = []
    for i, group in enumerate(program.completion_requirements):
        label = group.heading or f"Requirements {i + 1}"
        key = f"{_slugify(label, f'group-{i}')}-{i}"
        applied = [c for c in group.course_codes if c in earned_codes]

        if group.is_note:
            status = "na"
        elif group.credits <= 0:
            status = "na"
        else:
            code_credits = {c.code: c.credits for c in group.courses}
            earned_credits = sum(code_credits.get(c, 0.5) for c in applied)
            status = "complete" if earned_credits + 1e-9 >= group.credits else "incomplete"

        code_credits = {c.code: c.credits for c in group.courses}
        earned = round(sum(code_credits.get(c, 0.5) for c in applied), 2)

        out.append(
            {
                "key": key,
                "label": label,
                "status": status,
                "earned": earned,
                "required": group.credits,
                "appliedCourses": applied,
            }
        )
    return out


def program_progress_summary(program: Program | None, program_row: ProgramRow, rows: list[TranscriptRow]) -> dict:
    """One `ProgramCard`'s worth of data (design/screens/02-dashboard-and-
    progress.md): earned/total credits + completion percent. `loaded=False`
    means the program's requirements aren't cached yet -- the client should
    offer the "Load requirements" action (`GET /api/programs/:code/
    requirements`) rather than treat 0% as a real answer."""
    if program is None:
        return {
            "code": program_row.code,
            "title": program_row.title,
            "type": program_row.program_type,
            "earnedCredits": 0.0,
            "totalCredits": 0.0,
            "percent": 0.0,
            "loaded": False,
        }

    all_codes = {c for group in program.completion_requirements for c in group.course_codes}
    earned_codes = {r.code for r in _earned(rows) if r.code in all_codes}
    code_credits = {
        c.code: c.credits for group in program.completion_requirements for c in group.courses
    }
    earned_credits = sum(code_credits.get(c, 0.5) for c in earned_codes)
    total = effective_total_credits(program)
    percent = round(min(earned_credits / total, 1.0) * 100, 1) if total else 0.0

    return {
        "code": program.code,
        "title": program.title or program_row.title,
        "type": program.program_type or program_row.program_type,
        "earnedCredits": round(earned_credits, 2),
        "totalCredits": round(total, 2),
        "percent": percent,
        "loaded": True,
    }


# ------------------------------------------------------------------------ alerts
@dataclass(frozen=True)
class Alert:
    type: str
    severity: str  # info | warning | critical
    message: str


def build_alerts(
    *,
    progress: dict,
    breadth: dict,
    gpa: dict,
    program_rows: list[ProgramRow],
) -> list[dict]:
    """design/09 section 7: surface the things a student should act on, not
    a restatement of "you're not done yet" for every incomplete number."""
    alerts: list[Alert] = []

    if not program_rows:
        alerts.append(
            Alert("no_program", "warning", "No program declared yet -- add one to track requirements.")
        )

    if gpa["standing"] == "suspension":
        alerts.append(Alert("standing", "critical", "Academic standing: Suspension."))
    elif gpa["standing"] == "probation":
        alerts.append(
            Alert("standing", "warning", "Academic standing: Probation (course load is capped).")
        )

    if gpa["cgpa"] is not None and gpa["cgpa"] < GRADUATION_CGPA_MINIMUM and progress["totalCredits"] >= 15.0:
        alerts.append(
            Alert(
                "cgpa_below_minimum",
                "warning",
                f"CGPA {gpa['cgpa']:.2f} is below the {GRADUATION_CGPA_MINIMUM:.2f} graduation minimum.",
            )
        )

    if progress["sameSubjectOverCap"]:
        alerts.append(
            Alert(
                "same_subject_cap",
                "warning",
                f"{progress['sameSubjectSubject']}: {progress['sameSubjectCredits']:.1f} credits "
                f"exceeds the {SAME_SUBJECT_CREDITS_CAP:.1f}-credit same-subject cap.",
            )
        )

    if not breadth["satisfied"] and progress["totalCredits"] >= 10.0:
        for line in breadth["missing"][:2]:  # don't flood the panel
            alerts.append(Alert("breadth_gap", "info", line))

    return [a.__dict__ for a in alerts]
