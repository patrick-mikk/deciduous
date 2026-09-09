"""Plan blueprint: `GET/PUT /api/plan`, `POST /api/plan/validate`, `POST /api/plan/autoplan`.

`Plan`/`PlanItem` (see `backend/models_db.py`) hold a user's term-by-term course
selections. Each user has one "primary" plan, auto-created on first access —
multi-plan support is future work, not part of this contract. `PlanItem.notes`
is encrypted at rest (`backend.security.crypto.encrypt_field`/`decrypt_field`)
with the caller's per-session data key (`backend.api.current_data_key`); it is
never written or read in plaintext.

Validation (`POST /api/plan/validate`) checks a plan (either the saved primary
plan or an ad hoc `items` list passed in the body, for "what-if" previews)
against:

- **Prerequisites / corequisites** — parsed heuristically out of the free-text
  `Course.prerequisites`/`corequisites` (TTB `cmCourseInfo` HTML, already
  stripped by `backend.data_sources.timetable.client`). There is no structured
  boolean grammar in the source data, so `_extract_code_groups` splits on `;`
  and the word "and" into AND-groups, and treats every course code found
  inside one segment as an OR-alternative (any one satisfies that segment).
  Segments with no recognizable course code are left unverified (can't be
  reduced further) rather than silently failing the course.
- **Exclusions** — same code-extraction; any planned/completed course whose
  code appears in another planned course's exclusion text is flagged.
- **Offering availability** — does the planned course actually appear in the
  `SqliteCache` for its `termSession`? Distinguishes "not cached at all"
  (skip, we simply don't know) from "cached session has other courses but not
  this one" (flag as not offered).
- **Requirement mapping** — for the user's declared `ProgramEnrolment`s,
  matches owned (completed + planned) course codes against each cached
  `Program`'s `RequirementGroup.course_codes`, plus the degree-combination
  rules from `design/09-uoft-degree-rules.md` §§1-2 that are directly about
  the *set of courses in the plan*: same-3-letter-subject ≤15.0 cap,
  one-program-type-per-subject, and the ≥12.0-distinct-credits rule across
  multiple declared programs. GPA/breadth/graduation-eligibility (§§4,6,7 of
  that doc) belong to the separate `GET /api/me/requirements` surface
  (`design/06-data-model-and-api.md`), not this endpoint.

`POST /api/plan/autoplan` topologically sorts a set of course codes against
their (heuristically extracted) prerequisites and greedily bin-packs them into
the caller-supplied ordered `sessions`, respecting `maxCreditsPerTerm`. It is a
suggestion, not a validator — see `_topo_schedule` for the conservative
approximation it makes for OR-prerequisite groups.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable

from flask import Blueprint, jsonify, request

from backend.api import current_data_key, current_user, db_session, json_error, require_auth
from backend.data_sources.cache import SqliteCache
from backend.data_sources.models import Course
from backend.extensions import get_course_cache
from backend.models_db import Plan, PlanItem, ProgramEnrolment, TranscriptEntry
from backend.planner.course_code import parse_course_code, parse_program_code
from backend.security.crypto import decrypt_field, encrypt_field

bp = Blueprint("plan", __name__, url_prefix="/api/plan")

_VALID_ITEM_STATUSES = {"planned", "completed", "in_progress", "extra"}
_DEFAULT_MAX_CREDITS_PER_TERM = 2.5

# ---------------------------------------------------------------------------
# Course-/program-code parsing reuses backend.planner.course_code (also used
# by backend/api/_audit.py and backend/ingest/degree_explorer.py) rather than
# re-deriving subject/level/credit from a second private regex.
# ---------------------------------------------------------------------------

_CODE_TOKEN_RE = re.compile(r"\b[A-Z]{3}\d{3}[HY]\d\b")

_UPPER_LEVEL_MINIMUMS = {
    # design/09-uoft-degree-rules.md §2
    "specialist": {"credits300Plus": 4.0, "credits400Plus": 1.0},
    "major": {"credits300Plus": 2.0, "credits400Plus": 0.5},
    "minor": {"credits300Plus": 1.0, "credits400Plus": 0.0},
}


def subject_of(code: str) -> str | None:
    """The 3-letter subject designator, e.g. "POL208H1" -> "POL"."""
    parsed = parse_course_code(code)
    return parsed.subject if parsed else None


def level_of(code: str) -> int | None:
    """The course level (first digit of the course number * 100), e.g. 208 -> 200."""
    parsed = parse_course_code(code)
    return parsed.level if parsed else None


def credit_of(code: str) -> float | None:
    """0.5 for an H course, 1.0 for a Y course; `None` if the code doesn't parse."""
    parsed = parse_course_code(code)
    return parsed.credit_value if parsed else None


def _program_type_subject(program_code: str) -> tuple[str, str] | None:
    """`("major", "1305")` from "ASMAJ1305A", or `None` if it doesn't match the shape."""
    parsed = parse_program_code(program_code)
    return (parsed.program_type, parsed.subject) if parsed else None


def _extract_code_groups(text: str) -> list[list[str]]:
    """AND-of-OR course-code groups heuristically parsed out of free-text
    prerequisites/corequisites/exclusions. See module docstring. Segments with
    no recognizable course code are dropped (nothing to check, not a failure)."""
    if not text:
        return []
    segments = re.split(r";|\band\b", text, flags=re.IGNORECASE)
    groups: list[list[str]] = []
    for segment in segments:
        codes = sorted(set(_CODE_TOKEN_RE.findall(segment.upper())))
        if codes:
            groups.append(codes)
    return groups


# ---------------------------------------------------------------------------
# Session-code ordering. Session codes sort chronologically as plain integers
# (see AGENTS.md "Domain glossary": ...5=Summer, ...9=Fall, ...1=Winter of the
# *next* numeric year, e.g. 20265 < 20269 < 20271 is Summer26 < Fall26 <
# Winter27). A full-year course's session is "start-end", e.g. "20269-20271".
# ---------------------------------------------------------------------------


def _session_bounds(term_session: str) -> tuple[int, int]:
    def _to_int(value: str) -> int:
        try:
            return int(value)
        except ValueError:
            return 0

    parts = [p for p in term_session.split("-") if p]
    if not parts:
        return (0, 0)
    return (_to_int(parts[0]), _to_int(parts[-1]))


def _strictly_before(a_session: str, b_session: str) -> bool:
    _, a_end = _session_bounds(a_session)
    b_start, _ = _session_bounds(b_session)
    return a_end < b_start


def _candidate_sessions(term_session: str) -> list[str]:
    return [s for s in term_session.split("-") if s] or [term_session]


# ---------------------------------------------------------------------------
# Cache lookups
# ---------------------------------------------------------------------------


def _find_cached_course(cache: SqliteCache, term_session: str | None, code: str) -> Course | None:
    """Exact-code lookup within `term_session` (or either half of a Y-course's
    "start-end" session). `None` if not cached — never raises."""
    if not term_session:
        return None
    code_norm = code.strip().upper()
    for session in _candidate_sessions(term_session):
        for candidate in cache.search_courses(session, code_norm, limit=5):
            if candidate.code.strip().upper() == code_norm:
                return candidate
    return None


def _offering_status(cache: SqliteCache, term_session: str | None, code: str) -> str:
    """"offered" / "not_offered" / "unknown" (session never synced into the cache)."""
    if not term_session:
        return "unknown"
    sessions = _candidate_sessions(term_session)
    if not any(cache.course_count(session) > 0 for session in sessions):
        return "unknown"
    return "offered" if _find_cached_course(cache, term_session, code) is not None else "not_offered"


def _issue(severity: str, kind: str, course_code: str, message: str) -> dict[str, Any]:
    return {"severity": severity, "type": kind, "courseCode": course_code, "message": message}


# ---------------------------------------------------------------------------
# Plan CRUD
# ---------------------------------------------------------------------------


def _get_or_create_primary_plan(db, user) -> Plan:
    plan = db.query(Plan).filter_by(user_id=user.id, is_primary=True).first()
    if plan is None:
        plan = Plan(user_id=user.id, label="My Plan", is_primary=True)
        db.add(plan)
        db.commit()
    return plan


def _plan_item_out(item: PlanItem, data_key: bytes | None) -> dict[str, Any]:
    return {
        "id": item.id,
        "courseCode": item.course_code,
        "termSession": item.term_session,
        "status": item.status,
        "position": item.position,
        "notes": decrypt_field(item.notes_encrypted, data_key) if data_key else None,
    }


def _plan_out(plan: Plan, data_key: bytes | None) -> dict[str, Any]:
    items = sorted(plan.items, key=lambda i: i.position)
    return {
        "id": plan.id,
        "label": plan.label,
        "isPrimary": plan.is_primary,
        "items": [_plan_item_out(i, data_key) for i in items],
    }


@bp.route("", methods=["GET"])
@require_auth
def get_plan():
    db = db_session()
    plan = _get_or_create_primary_plan(db, current_user())
    return jsonify({"plan": _plan_out(plan, current_data_key())})


@bp.route("", methods=["PUT"])
@require_auth
def put_plan():
    data = request.get_json(silent=True) or {}
    items_payload = data.get("items")
    if not isinstance(items_payload, list):
        return json_error("`items` must be a list.", 422)

    db = db_session()
    user = current_user()
    data_key = current_data_key()
    plan = _get_or_create_primary_plan(db, user)

    label = data.get("label")
    if isinstance(label, str) and label.strip():
        plan.label = label.strip()[:120]

    normalized: list[PlanItem] = []
    for idx, raw in enumerate(items_payload):
        if not isinstance(raw, dict):
            return json_error(f"items[{idx}] must be an object.", 422)
        code = (raw.get("courseCode") or "").strip().upper()
        term_session = (raw.get("termSession") or "").strip()
        if not code or not term_session:
            return json_error(f"items[{idx}] requires courseCode and termSession.", 422)
        status = raw.get("status") or "planned"
        if status not in _VALID_ITEM_STATUSES:
            return json_error(
                f"items[{idx}].status must be one of {sorted(_VALID_ITEM_STATUSES)}.", 422
            )
        notes = raw.get("notes")
        notes_encrypted = encrypt_field(notes, data_key) if notes and data_key else None
        normalized.append(
            PlanItem(
                plan_id=plan.id,
                course_code=code,
                term_session=term_session,
                status=status,
                position=idx,
                notes_encrypted=notes_encrypted,
            )
        )

    db.query(PlanItem).filter(PlanItem.plan_id == plan.id).delete()
    for item in normalized:
        db.add(item)
    db.commit()

    return jsonify({"plan": _plan_out(plan, data_key)})


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@dataclass
class _OwnedCourse:
    """A course the student has completed, is taking, or has planned — the
    unit `_check_prereqs_and_exclusions`/`_degree_summary`/`_program_progress`
    all operate over."""

    code: str
    credit: float
    term_session: str | None
    status: str


def _collect_owned_courses(db, user, override_items: list[dict] | None) -> list[_OwnedCourse]:
    """Completed/in-progress transcript entries (always) + either the given
    ad hoc `items` (a "what-if" preview) or the user's saved primary plan."""
    owned: list[_OwnedCourse] = []
    for entry in db.query(TranscriptEntry).filter_by(user_id=user.id).all():
        if entry.status not in ("completed", "in_progress"):
            continue
        code = entry.code.strip().upper()
        owned.append(
            _OwnedCourse(
                code=code,
                credit=entry.credits or credit_of(code) or 0.5,
                term_session=entry.term_session,
                status=entry.status,
            )
        )

    if override_items is not None:
        for raw in override_items:
            code = (raw.get("courseCode") or "").strip().upper()
            if not code:
                continue
            owned.append(
                _OwnedCourse(
                    code=code,
                    credit=credit_of(code) or 0.5,
                    term_session=(raw.get("termSession") or "").strip() or None,
                    status=raw.get("status") or "planned",
                )
            )
    else:
        plan = _get_or_create_primary_plan(db, user)
        for item in plan.items:
            owned.append(
                _OwnedCourse(
                    code=item.course_code,
                    credit=credit_of(item.course_code) or 0.5,
                    term_session=item.term_session,
                    status=item.status,
                )
            )
    return owned


def _check_prereqs_and_exclusions(cache: SqliteCache, owned: list[_OwnedCourse]) -> list[dict]:
    issues: list[dict] = []
    all_codes = {c.code for c in owned}

    for it in owned:
        if it.status != "planned":
            continue

        prior_codes = {
            c.code
            for c in owned
            if c.code != it.code
            and (
                c.status in ("completed", "in_progress")
                or (
                    c.status == "planned"
                    and c.term_session
                    and it.term_session
                    and _strictly_before(c.term_session, it.term_session)
                )
            )
        }
        same_term_codes = {
            c.code
            for c in owned
            if c.code != it.code
            and c.status == "planned"
            and c.term_session
            and it.term_session
            and c.term_session == it.term_session
        }

        offering = _offering_status(cache, it.term_session, it.code)
        course = _find_cached_course(cache, it.term_session, it.code)
        if course is None:
            if offering == "not_offered":
                issues.append(
                    _issue(
                        "warning",
                        "offering",
                        it.code,
                        f"{it.code} is not offered in session {it.term_session} "
                        "(per cached timetable data).",
                    )
                )
            else:
                issues.append(
                    _issue(
                        "info",
                        "unverified",
                        it.code,
                        f"{it.code}: no cached course data for "
                        f"{it.term_session or 'this term'} — prerequisites, exclusions, "
                        "and offering could not be checked.",
                    )
                )
            continue

        for group in _extract_code_groups(course.prerequisites):
            if not (set(group) & prior_codes):
                issues.append(
                    _issue(
                        "error",
                        "prerequisite",
                        it.code,
                        f"{it.code}: prerequisite not met — needs one of "
                        f"{', '.join(group)} completed in an earlier term.",
                    )
                )

        for group in _extract_code_groups(course.corequisites):
            if not (set(group) & (prior_codes | same_term_codes)):
                issues.append(
                    _issue(
                        "error",
                        "corequisite",
                        it.code,
                        f"{it.code}: corequisite not met — needs one of "
                        f"{', '.join(group)} in the same or an earlier term.",
                    )
                )

        excluded = {code for group in _extract_code_groups(course.exclusions) for code in group}
        conflicts = excluded & (all_codes - {it.code})
        if conflicts:
            issues.append(
                _issue(
                    "error",
                    "exclusion",
                    it.code,
                    f"{it.code} cannot be taken with {', '.join(sorted(conflicts))} (exclusion).",
                )
            )

    return issues


def _degree_summary(owned: list[_OwnedCourse]) -> dict[str, Any]:
    """design/09-uoft-degree-rules.md §1: credit totals, level distribution,
    same-subject cap. (ArtSci/GPA/breadth are §§1,4 items that need a richer
    distribution taxonomy than a single cached label reliably gives us here —
    left to `GET /api/me/requirements`, see module docstring.)"""
    seen: dict[str, _OwnedCourse] = {}
    for c in owned:
        if c.status == "extra":
            continue
        seen.setdefault(c.code, c)  # transcript entries are collected first, so they win ties

    total = 0.0
    level200 = 0.0
    level300 = 0.0
    by_subject: dict[str, float] = {}
    for c in seen.values():
        total += c.credit
        level = level_of(c.code)
        if level is not None and level >= 200:
            level200 += c.credit
        if level is not None and level >= 300:
            level300 += c.credit
        subject = subject_of(c.code)
        if subject:
            by_subject[subject] = by_subject.get(subject, 0.0) + c.credit

    over_cap = [
        {"subject": subject, "credits": round(credits, 2)}
        for subject, credits in by_subject.items()
        if credits > 15.0
    ]

    return {
        "totalCredits": round(total, 2),
        "level200PlusCredits": round(level200, 2),
        "level300PlusCredits": round(level300, 2),
        "creditsBySubject": {s: round(v, 2) for s, v in by_subject.items()},
        "sameSubjectOverCap": over_cap,
        "courseCount": len(seen),
    }


def _program_progress(
    cache: SqliteCache, owned: list[_OwnedCourse], enrolments: list[ProgramEnrolment]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Per-program requirement-group coverage + the cross-program combination
    checks from design/09-uoft-degree-rules.md §2 (one-type-per-subject) and
    §1 (>=12.0 distinct credits across a multi-program combination)."""
    owned_codes = {c.code for c in owned if c.status != "extra"}
    credit_by_code = {c.code: c.credit for c in owned}

    def _credit(code: str) -> float:
        return credit_by_code.get(code, credit_of(code) or 0.5)

    results: list[dict[str, Any]] = []
    subject_types: dict[str, list[str]] = {}
    all_required_codes: set[str] = set()
    combo_issues: list[dict[str, Any]] = []
    # Count of enrolled programs whose requirements actually parsed (nonzero
    # course codes) — the distinct-credits check below only makes sense
    # across these; an unparsed program already gets its own
    # "requirements_unparsed" warning above, so folding its (necessarily
    # empty) `required_codes` into the union would silently understate the
    # total instead of just leaving it out with an explanation.
    parsed_program_count = 0

    for enrolment in enrolments:
        type_subject = _program_type_subject(enrolment.program_code)
        if type_subject:
            ptype, subject = type_subject
            subject_types.setdefault(subject, []).append(ptype)

        program = cache.get_program(enrolment.program_code)
        if program is None:
            results.append(
                {
                    "programCode": enrolment.program_code,
                    "title": enrolment.program_title or "",
                    "cached": False,
                    "groups": [],
                }
            )
            combo_issues.append(
                _issue(
                    "warning",
                    "requirements_unparsed",
                    enrolment.program_code,
                    f"Requirements for {enrolment.program_title or enrolment.program_code} "
                    "haven't been parsed yet — program progress can't be checked.",
                )
            )
            continue

        group_out = []
        required_codes: set[str] = set()
        for group in program.completion_requirements:
            group_codes = set(group.course_codes)
            required_codes |= group_codes
            covered = sorted(group_codes & owned_codes)
            earned = sum(_credit(code) for code in covered)
            group_out.append(
                {
                    "heading": group.heading,
                    "requiredCredits": group.credits,
                    "earnedCredits": round(earned, 2),
                    "coveredCourses": covered,
                }
            )

        if not required_codes:
            # Cached, but no course codes were ever extracted from its
            # completion-requirement text (neither the heuristic parse nor a
            # Gemini reparse succeeded) — false success otherwise: every group
            # would read 0/0 with no indication anything is actually unknown.
            combo_issues.append(
                _issue(
                    "warning",
                    "requirements_unparsed",
                    enrolment.program_code,
                    f"Requirements for {program.title or enrolment.program_code} "
                    "haven't been parsed yet — program progress can't be checked.",
                )
            )
        else:
            parsed_program_count += 1

        all_required_codes |= required_codes
        covered_program_codes = required_codes & owned_codes
        earned_total = sum(_credit(code) for code in covered_program_codes)
        credits_300 = sum(_credit(c) for c in covered_program_codes if (level_of(c) or 0) >= 300)
        credits_400 = sum(_credit(c) for c in covered_program_codes if (level_of(c) or 0) >= 400)
        minimums = _UPPER_LEVEL_MINIMUMS.get(type_subject[0]) if type_subject else None

        results.append(
            {
                "programCode": enrolment.program_code,
                "title": program.title,
                "programType": program.program_type,
                "cached": True,
                "totalCreditsRequired": program.total_credits,
                "earnedCredits": round(earned_total, 2),
                "credits300Plus": round(credits_300, 2),
                "credits400Plus": round(credits_400, 2),
                "upperLevelMinimums": minimums,
                "groups": group_out,
            }
        )

    for subject, types in subject_types.items():
        if len(types) > 1:
            combo_issues.append(
                _issue(
                    "error",
                    "one-type-per-subject",
                    "",
                    f"More than one program type declared for subject {subject}: "
                    f"{', '.join(types)} (only one Specialist/Major/Minor per subject "
                    "is allowed, eff. Sept 2025).",
                )
            )

    if parsed_program_count >= 2:
        distinct_credits = sum(_credit(code) for code in (all_required_codes & owned_codes))
        if distinct_credits < 12.0:
            combo_issues.append(
                _issue(
                    "warning",
                    "distinct-credits",
                    "",
                    f"Only {distinct_credits:.1f} distinct credits count across your "
                    "declared programs; a multi-program combination needs ≥12.0.",
                )
            )

    return results, combo_issues


@bp.route("/validate", methods=["POST"])
@require_auth
def validate_plan():
    data = request.get_json(silent=True) or {}
    override_items = data.get("items")
    if override_items is not None:
        if not isinstance(override_items, list):
            return json_error("`items` must be a list.", 422)
        for idx, raw in enumerate(override_items):
            if not isinstance(raw, dict) or not (raw.get("courseCode") or "").strip():
                return json_error(f"items[{idx}] requires a courseCode.", 422)

    db = db_session()
    user = current_user()
    cache = get_course_cache()

    owned = _collect_owned_courses(db, user, override_items)
    issues = _check_prereqs_and_exclusions(cache, owned)
    summary = _degree_summary(owned)

    enrolments = db.query(ProgramEnrolment).filter_by(user_id=user.id).all()
    programs, combo_issues = _program_progress(cache, owned, enrolments)
    issues.extend(combo_issues)

    return jsonify({"issues": issues, "summary": summary, "programs": programs})


# ---------------------------------------------------------------------------
# Autoplan
# ---------------------------------------------------------------------------


def _topo_schedule(
    course_codes: list[str],
    completed: set[str],
    sessions: list[str],
    max_credits_per_term: float,
    prereq_groups_of: Callable[[str], list[list[str]]],
    credit_of_code: Callable[[str], float],
) -> dict[str, Any]:
    """Kahn's-algorithm topological sort + greedy credit-cap bin-packing into
    `sessions`, in order. Nodes become "ready" for a session only after every
    predecessor placed in an *earlier* session (never the same one).

    OR-prerequisite groups are approximated conservatively: if a group isn't
    already satisfied by `completed`, every one of its members that is also in
    `course_codes` is treated as a required predecessor (an AND), rather than
    picking just one arbitrarily. That can schedule a course later than
    strictly necessary, which is a safe bias for a *suggestion* — it never
    invents a false "ready" state validate() would then reject.
    """
    course_set = set(course_codes)
    successors: dict[str, set[str]] = {c: set() for c in course_codes}
    indegree: dict[str, int] = {c: 0 for c in course_codes}

    for code in course_codes:
        for group in prereq_groups_of(code):
            if set(group) & completed:
                continue
            for predecessor in group:
                if predecessor == code or predecessor not in course_set:
                    continue
                if code not in successors[predecessor]:
                    successors[predecessor].add(code)
                    indegree[code] += 1

    ready = sorted(
        (c for c in course_codes if indegree[c] == 0), key=lambda c: (level_of(c) or 0, c)
    )
    placed: set[str] = set()
    terms: list[dict[str, Any]] = []

    term_idx = 0
    while ready and term_idx < len(sessions):
        session = sessions[term_idx]
        total = 0.0
        term_items: list[dict[str, Any]] = []
        still_ready: list[str] = []

        for code in ready:
            credit = credit_of_code(code)
            if total + credit <= max_credits_per_term + 1e-9:
                term_items.append({"courseCode": code, "credit": credit})
                total += credit
                placed.add(code)
            else:
                still_ready.append(code)

        newly_ready: list[str] = []
        for item in term_items:
            for successor in successors[item["courseCode"]]:
                indegree[successor] -= 1
                if indegree[successor] == 0:
                    newly_ready.append(successor)

        ready = sorted(still_ready + newly_ready, key=lambda c: (level_of(c) or 0, c))
        terms.append({"session": session, "items": term_items, "totalCredits": round(total, 2)})
        term_idx += 1

    unplaced = []
    for code in course_codes:
        if code in placed:
            continue
        reason = (
            "circular prerequisite reference" if indegree[code] > 0 else "not enough terms provided"
        )
        unplaced.append({"courseCode": code, "reason": reason})

    return {"terms": terms, "unplaced": unplaced}


@bp.route("/autoplan", methods=["POST"])
@require_auth
def autoplan():
    data = request.get_json(silent=True) or {}

    sessions = data.get("sessions")
    if not sessions or not isinstance(sessions, list):
        return json_error(
            "`sessions` (an ordered list of term-session codes to fill) is required.", 422
        )
    sessions = [str(s) for s in sessions]

    max_credits = data.get("maxCreditsPerTerm", _DEFAULT_MAX_CREDITS_PER_TERM)
    try:
        max_credits = float(max_credits)
    except (TypeError, ValueError):
        return json_error("`maxCreditsPerTerm` must be a number.", 422)
    if max_credits <= 0:
        return json_error("`maxCreditsPerTerm` must be positive.", 422)

    db = db_session()
    user = current_user()

    course_codes = data.get("courseCodes")
    if course_codes is None:
        plan = _get_or_create_primary_plan(db, user)
        course_codes = [i.course_code for i in plan.items if i.status == "planned"]
    if not isinstance(course_codes, list):
        return json_error("`courseCodes` must be a list.", 422)
    seen_codes: dict[str, None] = {}
    for code in course_codes:
        if isinstance(code, str) and code.strip():
            seen_codes.setdefault(code.strip().upper(), None)
    course_codes = list(seen_codes)

    completed = data.get("completedCodes")
    if completed is None:
        completed = [
            entry.code
            for entry in db.query(TranscriptEntry).filter_by(user_id=user.id).all()
            if entry.status in ("completed", "in_progress")
        ]
    completed_set = {c.strip().upper() for c in completed if isinstance(c, str) and c.strip()}

    course_info = data.get("courseInfo") if isinstance(data.get("courseInfo"), dict) else {}
    cache = get_course_cache()

    def prereq_groups_of(code: str) -> list[list[str]]:
        hint = course_info.get(code)
        if isinstance(hint, dict) and "prerequisites" in hint:
            return _extract_code_groups(hint.get("prerequisites") or "")
        for session in sessions:
            course = _find_cached_course(cache, session, code)
            if course is not None:
                return _extract_code_groups(course.prerequisites)
        return []

    def credit_of_code(code: str) -> float:
        hint = course_info.get(code)
        if isinstance(hint, dict) and hint.get("credit"):
            try:
                return float(hint["credit"])
            except (TypeError, ValueError):
                pass
        return credit_of(code) or 0.5

    result = _topo_schedule(
        course_codes, completed_set, sessions, max_credits, prereq_groups_of, credit_of_code
    )
    return jsonify(result)
