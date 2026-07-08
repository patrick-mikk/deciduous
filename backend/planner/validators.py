"""Degree-level checks, program-combination validity, and the breadth
requirement — `design/09-uoft-degree-rules.md` §§1-4, 7.

Pure functions over `planner.types.CourseRecord`/`ProgramRequirement`; no I/O.
Prerequisite/corequisite/exclusion checks live in `prereqs.py`; GPA/standing
math lives in `gpa.py`. This module composes all three for the top-level
`graduation_eligibility` check (§7).
"""

from __future__ import annotations

import itertools
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Iterable

from backend.planner.gpa import GRADUATION_MIN_CGPA
from backend.planner.types import CourseRecord, Issue, ProgramRequirement

# ---------------------------------------------------------------------------
# Constants (design/09-uoft-degree-rules.md §1-2)
# ---------------------------------------------------------------------------

DEGREE_TOTAL_CREDITS = 20.0
ARTSCI_MIN_CREDITS = 10.0
LEVEL_200_MIN_CREDITS = 13.0
LEVEL_300_MIN_CREDITS = 6.0
SAME_SUBJECT_MAX_CREDITS = 15.0
TRANSFER_CREDIT_300_CAP = 1.0
DISTINCT_CREDITS_MIN = 12.0

# §2 upper-level minimums and credit ranges, keyed by ProgramRequirement.program_type.
PROGRAM_UPPER_LEVEL_MIN: dict[str, dict[str, float]] = {
    "specialist": {"300": 4.0, "400": 1.0},
    "major": {"300": 2.0, "400": 0.5},
    "minor": {"300": 1.0, "400": 0.0},
}
PROGRAM_MIN_CREDITS: dict[str, float] = {"specialist": 10.0, "major": 6.0, "minor": 4.0}

BREADTH_CATEGORIES: tuple[int, ...] = (1, 2, 3, 4, 5)
_BREADTH_LABEL_RE = re.compile(r"\((\d)\)\s*$")

_STATUS_PRIORITY = {"completed": 0, "in_progress": 1, "planned": 2}


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def effective_courses(records: Iterable[CourseRecord]) -> list[CourseRecord]:
    """De-duplicate `records` by course code (keep the most "settled" status
    — completed > in_progress > planned) and drop Extra courses, which never
    count toward the degree, program, breadth, or GPA totals (§1, §6)."""
    best: dict[str, CourseRecord] = {}
    for record in records:
        if record.status == "extra":
            continue
        code = record.code_norm
        existing = best.get(code)
        if existing is None or _STATUS_PRIORITY.get(record.status, 9) < _STATUS_PRIORITY.get(
            existing.status, 9
        ):
            best[code] = record
    return list(best.values())


def parse_breadth_category(label: str) -> int | None:
    """Extract the 1-5 Breadth-Requirement category number from a
    `Course.breadth` label, e.g. "Society and Its Institutions (3)" -> 3.
    `None` if the label doesn't end in a recognizable "(N)"."""
    match = _BREADTH_LABEL_RE.search(label.strip())
    if not match:
        return None
    value = int(match.group(1))
    return value if value in BREADTH_CATEGORIES else None


def breadth_categories_from_labels(labels: Iterable[str]) -> tuple[int, ...]:
    """Build a `CourseRecord.breadth_categories` tuple from raw
    `Course.breadth` labels (deduped, sorted)."""
    categories = {parse_breadth_category(label) for label in labels}
    return tuple(sorted(c for c in categories if c is not None))


# ---------------------------------------------------------------------------
# 1. Degree-level credit checks
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DegreeCreditSummary:
    total_credits: float
    artsci_credits: float
    level_200_plus_credits: float
    level_300_plus_credits: float
    credits_by_subject: dict[str, float]
    same_subject_over_cap: dict[str, float]  # subject -> credits, only entries > cap


def degree_credit_summary(records: Iterable[CourseRecord]) -> DegreeCreditSummary:
    """§1: total credits, ArtSci credits, 200+/300+ level credits (with the
    <=1.0 non-exchange-transfer cap on the 300+ minimum), and same-subject
    totals."""
    courses = effective_courses(records)
    total = sum(c.credits for c in courses)
    artsci = sum(c.credits for c in courses if c.is_artsci)
    level200 = sum(c.credits for c in courses if (c.level or 0) >= 200)

    capped_transfer_300 = min(
        TRANSFER_CREDIT_300_CAP,
        sum(
            c.credits
            for c in courses
            if (c.level or 0) >= 300 and c.is_transfer_credit and not c.is_uoft_exchange
        ),
    )
    uncapped_300 = sum(
        c.credits
        for c in courses
        if (c.level or 0) >= 300 and not (c.is_transfer_credit and not c.is_uoft_exchange)
    )
    level300 = uncapped_300 + capped_transfer_300

    by_subject: dict[str, float] = defaultdict(float)
    for c in courses:
        if c.subject:
            by_subject[c.subject] += c.credits

    over_cap = {s: round(v, 2) for s, v in by_subject.items() if v > SAME_SUBJECT_MAX_CREDITS}

    return DegreeCreditSummary(
        total_credits=round(total, 2),
        artsci_credits=round(artsci, 2),
        level_200_plus_credits=round(level200, 2),
        level_300_plus_credits=round(level300, 2),
        credits_by_subject={s: round(v, 2) for s, v in by_subject.items()},
        same_subject_over_cap=over_cap,
    )


def validate_degree_credits(summary: DegreeCreditSummary) -> list[Issue]:
    """"info" issues for targets not yet reached (still achievable by taking
    more courses); "error" for the same-subject cap, which is an actual
    violation once tripped."""
    issues: list[Issue] = []
    if summary.total_credits < DEGREE_TOTAL_CREDITS:
        issues.append(
            Issue(
                "info",
                "credits-total",
                f"{summary.total_credits:.1f}/{DEGREE_TOTAL_CREDITS:.1f} total credits "
                f"({DEGREE_TOTAL_CREDITS - summary.total_credits:.1f} more needed).",
            )
        )
    if summary.artsci_credits < ARTSCI_MIN_CREDITS:
        issues.append(
            Issue(
                "info",
                "credits-artsci",
                f"{summary.artsci_credits:.1f}/{ARTSCI_MIN_CREDITS:.1f} Arts & Science credits "
                f"({ARTSCI_MIN_CREDITS - summary.artsci_credits:.1f} more needed).",
            )
        )
    if summary.level_200_plus_credits < LEVEL_200_MIN_CREDITS:
        issues.append(
            Issue(
                "info",
                "credits-200-plus",
                f"{summary.level_200_plus_credits:.1f}/{LEVEL_200_MIN_CREDITS:.1f} credits at "
                f"the 200+ level ({LEVEL_200_MIN_CREDITS - summary.level_200_plus_credits:.1f} "
                "more needed).",
            )
        )
    if summary.level_300_plus_credits < LEVEL_300_MIN_CREDITS:
        issues.append(
            Issue(
                "info",
                "credits-300-plus",
                f"{summary.level_300_plus_credits:.1f}/{LEVEL_300_MIN_CREDITS:.1f} credits at "
                f"the 300+ level ({LEVEL_300_MIN_CREDITS - summary.level_300_plus_credits:.1f} "
                "more needed).",
            )
        )
    for subject, credits in sorted(summary.same_subject_over_cap.items()):
        issues.append(
            Issue(
                "error",
                "same-subject-cap",
                f"{credits:.1f} credits in {subject} exceed the "
                f"{SAME_SUBJECT_MAX_CREDITS:.1f}-credit same-subject cap.",
            )
        )
    return issues


# ---------------------------------------------------------------------------
# 2. Program-combination validity
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProgramProgress:
    code: str
    program_type: str
    subject: str
    total_credits_required: float
    earned_credits: float
    credits_300_plus: float
    credits_400_plus: float
    min_300_plus: float
    min_400_plus: float
    meets_credit_target: bool
    meets_upper_level_minimums: bool


@dataclass(frozen=True)
class ProgramCombinationResult:
    combo_type: str | None  # "specialist" | "two_majors" | "major_plus_two_minors" | None
    combo_valid: bool
    program_progress: list[ProgramProgress]
    distinct_credits: float
    distinct_credits_ok: bool
    one_type_per_subject_violations: list[str] = field(default_factory=list)


def _combo_type(counts: Counter) -> str | None:
    if counts == Counter({"specialist": 1}):
        return "specialist"
    if counts == Counter({"major": 2}):
        return "two_majors"
    if counts == Counter({"major": 1, "minor": 2}):
        return "major_plus_two_minors"
    return None


def evaluate_program_combination(
    programs: list[ProgramRequirement], records: Iterable[CourseRecord]
) -> tuple[ProgramCombinationResult, list[Issue]]:
    """§1 combination shape (1 Specialist | 2 Majors | 1 Major + 2 Minors),
    §1 >=12.0 distinct credits across multi-program combos, §2 one-type-per-
    subject, and §2 per-program earned credits + 300+/400 minimums."""
    courses = effective_courses(records)
    credit_by_code = {c.code_norm: c.credits for c in courses}
    level_by_code = {c.code_norm: c.level for c in courses}
    owned_codes = set(credit_by_code)

    counts = Counter(p.program_type for p in programs)
    combo_type = _combo_type(counts)
    combo_valid = combo_type is not None

    issues: list[Issue] = []
    if not combo_valid and programs:
        issues.append(
            Issue(
                "warning",
                "program-combination",
                "Program combination must be 1 Specialist, 2 Majors, or 1 Major + 2 Minors "
                f"(currently: {dict(counts)}).",
            )
        )

    by_subject: dict[str, list[ProgramRequirement]] = defaultdict(list)
    for p in programs:
        by_subject[p.subject].append(p)
    subject_violations: list[str] = []
    for subject, group in sorted(by_subject.items()):
        if len(group) > 1:
            subject_violations.append(subject)
            issues.append(
                Issue(
                    "error",
                    "one-type-per-subject",
                    f"More than one program declared for subject {subject}: "
                    f"{', '.join(p.program_type for p in group)} (only one "
                    "Specialist/Major/Minor per subject is allowed, eff. Sept 2025).",
                )
            )

    progress: list[ProgramProgress] = []
    all_required: set[str] = set()
    for p in programs:
        covered = p.course_codes & owned_codes
        all_required |= p.course_codes
        earned = sum(credit_by_code[c] for c in covered)
        credits_300 = sum(credit_by_code[c] for c in covered if (level_by_code.get(c) or 0) >= 300)
        credits_400 = sum(credit_by_code[c] for c in covered if (level_by_code.get(c) or 0) >= 400)
        minimums = PROGRAM_UPPER_LEVEL_MIN.get(p.program_type, {"300": 0.0, "400": 0.0})
        target = p.total_credits if p.total_credits > 0 else PROGRAM_MIN_CREDITS.get(p.program_type, 0.0)

        pp = ProgramProgress(
            code=p.code,
            program_type=p.program_type,
            subject=p.subject,
            total_credits_required=target,
            earned_credits=round(earned, 2),
            credits_300_plus=round(credits_300, 2),
            credits_400_plus=round(credits_400, 2),
            min_300_plus=minimums["300"],
            min_400_plus=minimums["400"],
            meets_credit_target=earned + 1e-9 >= target,
            meets_upper_level_minimums=(
                credits_300 + 1e-9 >= minimums["300"] and credits_400 + 1e-9 >= minimums["400"]
            ),
        )
        progress.append(pp)
        if not pp.meets_credit_target:
            issues.append(
                Issue(
                    "info",
                    "program-credits",
                    f"{p.code}: {pp.earned_credits:.1f}/{target:.1f} credits earned.",
                )
            )
        if not pp.meets_upper_level_minimums:
            issues.append(
                Issue(
                    "info",
                    "program-upper-level",
                    f"{p.code}: needs >= {minimums['300']:.1f} credits at the 300+ level "
                    f"(>= {minimums['400']:.1f} at 400+); has {pp.credits_300_plus:.1f}/"
                    f"{pp.credits_400_plus:.1f}.",
                )
            )

    distinct_credits = 0.0
    distinct_ok = True
    if len(programs) >= 2:
        distinct_credits = sum(credit_by_code[c] for c in (all_required & owned_codes))
        distinct_ok = distinct_credits + 1e-9 >= DISTINCT_CREDITS_MIN
        if not distinct_ok:
            issues.append(
                Issue(
                    "warning",
                    "distinct-credits",
                    f"Only {distinct_credits:.1f} distinct credits count across declared "
                    f"programs; a multi-program combination needs >= {DISTINCT_CREDITS_MIN:.1f}.",
                )
            )

    result = ProgramCombinationResult(
        combo_type=combo_type,
        combo_valid=combo_valid,
        program_progress=progress,
        distinct_credits=round(distinct_credits, 2),
        distinct_credits_ok=distinct_ok,
        one_type_per_subject_violations=subject_violations,
    )
    return result, issues


# ---------------------------------------------------------------------------
# 3. Breadth requirement
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BreadthAllocation:
    course_code: str
    category: int
    credits: float


def allocate_breadth_credits(record: CourseRecord) -> list[BreadthAllocation]:
    """§4: an H course puts its 0.5 credit toward its one tagged category; a
    Y course either puts its full 1.0 toward one category, or splits evenly
    across however many categories it's tagged with (typically two, 0.5
    each) — driven entirely by how many `breadth_categories` the course
    carries, which the calendar/TTB data itself specifies."""
    categories = record.breadth_categories
    if not categories:
        return []
    share = record.credits / len(categories)
    return [BreadthAllocation(record.code_norm, cat, share) for cat in categories]


@dataclass(frozen=True)
class BreadthResult:
    earned_by_category: dict[int, float]
    satisfied: bool
    satisfied_via: str | None  # "4-of-5" | "3-plus-2" | None
    categories_at_or_above_1: list[int]
    categories_at_or_above_half: list[int]
    cheapest_additional_credits: float
    cheapest_path: dict[int, float]  # category -> additional credits still needed


def evaluate_breadth(records: Iterable[CourseRecord]) -> BreadthResult:
    """§4: satisfied by EITHER 1.0 credit in each of 4-of-5 categories, OR
    1.0 in each of any 3 + 0.5 in each of the other 2. Also returns the
    cheapest remaining path toward whichever option is closer. CR/NCR
    courses count toward breadth (per §4) — the caller should include them
    in `records`; only Extra courses (`status == "extra"`) are excluded
    here. Pass whichever subset of statuses represents "earned" for your
    purposes (e.g. completed-only, or completed+planned for a projection).
    """
    earned: dict[int, float] = {c: 0.0 for c in BREADTH_CATEGORIES}
    for record in records:
        if record.status == "extra":
            continue
        for alloc in allocate_breadth_credits(record):
            if alloc.category in earned:
                earned[alloc.category] += alloc.credits
    earned = {c: round(v, 3) for c, v in earned.items()}

    def deficit(target: float, category: int) -> float:
        return max(0.0, round(target - earned[category], 3))

    deficits_to_1 = {c: deficit(1.0, c) for c in BREADTH_CATEGORIES}
    worst_category = max(BREADTH_CATEGORIES, key=lambda c: deficits_to_1[c])
    option_a_cost = sum(v for c, v in deficits_to_1.items() if c != worst_category)
    option_a_path = {c: v for c, v in deficits_to_1.items() if c != worst_category and v > 0}

    best_b_cost = None
    best_b_path: dict[int, float] = {}
    for combo in itertools.combinations(BREADTH_CATEGORIES, 3):
        others = [c for c in BREADTH_CATEGORIES if c not in combo]
        cost = sum(deficit(1.0, c) for c in combo) + sum(deficit(0.5, c) for c in others)
        if best_b_cost is None or cost < best_b_cost:
            best_b_cost = cost
            best_b_path = {
                **{c: deficit(1.0, c) for c in combo if deficit(1.0, c) > 0},
                **{c: deficit(0.5, c) for c in others if deficit(0.5, c) > 0},
            }
    assert best_b_cost is not None  # combinations(5, 3) is always non-empty

    satisfied_a = option_a_cost <= 1e-9
    satisfied_b = best_b_cost <= 1e-9
    satisfied = satisfied_a or satisfied_b

    if satisfied_a:
        via = "4-of-5"
    elif satisfied_b:
        via = "3-plus-2"
    else:
        via = None

    if option_a_cost <= best_b_cost:
        cheapest_cost, cheapest_path = option_a_cost, option_a_path
    else:
        cheapest_cost, cheapest_path = best_b_cost, best_b_path

    return BreadthResult(
        earned_by_category=earned,
        satisfied=satisfied,
        satisfied_via=via,
        categories_at_or_above_1=sorted(c for c in BREADTH_CATEGORIES if earned[c] >= 1.0 - 1e-9),
        categories_at_or_above_half=sorted(c for c in BREADTH_CATEGORIES if earned[c] >= 0.5 - 1e-9),
        cheapest_additional_credits=round(cheapest_cost, 3),
        cheapest_path=cheapest_path,
    )


# ---------------------------------------------------------------------------
# 7. Graduation eligibility (composes 1-4 above + gpa.py)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GraduationEligibilityResult:
    eligible: bool
    checklist: dict[str, bool]
    issues: list[Issue]


def graduation_eligibility(
    records: list[CourseRecord],
    programs: list[ProgramRequirement],
    cgpa_value: float,
    standing: str,
) -> GraduationEligibilityResult:
    """§7: all of §§1-4 green + CGPA >= 1.85 + good standing."""
    summary = degree_credit_summary(records)
    credit_issues = validate_degree_credits(summary)
    combo_result, combo_issues = evaluate_program_combination(programs, records)
    breadth_result = evaluate_breadth(records)

    checklist = {
        "credits-20": summary.total_credits >= DEGREE_TOTAL_CREDITS,
        "artsci-10": summary.artsci_credits >= ARTSCI_MIN_CREDITS,
        "level-200-13": summary.level_200_plus_credits >= LEVEL_200_MIN_CREDITS,
        "level-300-6": summary.level_300_plus_credits >= LEVEL_300_MIN_CREDITS,
        "same-subject-cap": not summary.same_subject_over_cap,
        "program-combination": combo_result.combo_valid,
        "one-type-per-subject": not combo_result.one_type_per_subject_violations,
        "distinct-credits": combo_result.distinct_credits_ok,
        "program-progress": all(
            p.meets_credit_target and p.meets_upper_level_minimums for p in combo_result.program_progress
        ),
        "breadth": breadth_result.satisfied,
        "cgpa-1.85": cgpa_value >= GRADUATION_MIN_CGPA,
        "good-standing": standing == "good",
    }

    issues = list(credit_issues) + list(combo_issues)
    if not checklist["breadth"]:
        issues.append(
            Issue(
                "info",
                "breadth",
                "Breadth requirement not yet satisfied; needs "
                f"{breadth_result.cheapest_additional_credits:.1f} more credits "
                f"(closest path: {breadth_result.cheapest_path or 'n/a'}).",
            )
        )
    if not checklist["cgpa-1.85"]:
        issues.append(
            Issue(
                "info",
                "cgpa",
                f"CGPA {cgpa_value:.2f} is below the {GRADUATION_MIN_CGPA:.2f} graduation minimum.",
            )
        )
    if not checklist["good-standing"]:
        issues.append(
            Issue("error", "standing", f"Academic standing is {standing!r}, not good standing.")
        )

    return GraduationEligibilityResult(
        eligible=all(checklist.values()), checklist=checklist, issues=issues
    )
