"""Me blueprint: the signed-in student's degree audit, transcript, requirement
progress, and alerts.

Builds `CourseRecord`s (transcript entries — grades/marks decrypted with the
caller's data key — plus planned courses) and runs the pure
`backend.planner` validators/GPA engine (implementing
`design/09-uoft-degree-rules.md`). Breadth categories and Arts/Science
distribution are looked up from the course cache when available; a completed
course whose past session isn't cached simply contributes no breadth tag (a
best-effort limitation, surfaced as incomplete rather than wrong).
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import asdict
from typing import Any

from flask import Blueprint, jsonify

from backend.api import current_data_key, current_user, db_session, require_auth
from backend.api._audit import ProgramRow, TranscriptRow
from backend.api._audit import program_progress_summary as _program_progress_summary
from backend.api._audit import requirement_progress as _audit_requirement_progress
from backend.api.programs import _enrolment_json
from backend.data_sources.cache import SqliteCache
from backend.extensions import get_course_cache
from backend.ingest.degree_explorer import normalize_session as _parse_normalize_session
from backend.models_db import Plan, ProgramEnrolment, TranscriptEntry
from backend.planner.course_code import parse_course_code
from backend.planner.gpa import (
    academic_standing,
    cgpa,
    grade_mark_step_mismatch,
    max_credits_for_term,
    sgpa,
)
from backend.planner.types import CourseRecord, ProgramRequirement
from backend.planner.validators import (
    breadth_categories_from_labels,
    degree_credit_summary,
    evaluate_breadth,
    evaluate_program_combination,
    graduation_eligibility,
    validate_degree_credits,
)
from backend.security.crypto import decrypt_field

bp = Blueprint("me", __name__, url_prefix="/api/me")

_VALID_STATUSES = ("completed", "in_progress", "planned", "extra")

# A session string that's already a well-formed TTB code or code range
# ("20269", "20269-20271") -- left alone by `_normalize_session` below.
_SESSION_CODE_OR_RANGE_RE = re.compile(r"^2\d{3}[159](-2\d{3}[159])?$")

_REIMPORT_WARNING = (
    "Some grades look inconsistent with their marks — re-import your "
    "Academic History PDF to refresh them."
)


def _credit_of(code: str) -> float:
    parsed = parse_course_code(code)
    return parsed.credit_value if parsed else 0.5


def _decrypt_mark(token: str | None, data_key: bytes | None) -> float | None:
    if not token or not data_key:
        return None
    raw = decrypt_field(token, data_key)
    if raw in (None, "", "None"):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _breadth_dist(cache: SqliteCache, code: str, session: str | None) -> tuple[tuple[int, ...], tuple[str, ...]]:
    code_u = code.strip().upper()
    for part in [p for p in (session or "").split("-") if p]:
        for candidate in cache.search_courses(part, code_u, limit=3):
            if candidate.code.strip().upper() == code_u:
                return breadth_categories_from_labels(candidate.breadth), tuple(candidate.distribution)
    return (), ()


def _normalize_session(raw: str | None) -> str:
    """Best-effort normalize a possibly-legacy `term_session` string to
    TTB's 5-digit session code (see AGENTS.md: "20265"=Summer 2026,
    "20269"=Fall 2026, "20271"=Winter 2027, "20269-20271"=Fall-Winter full
    year), so a stale pre-5bbe9ae-import DB self-heals at the API layer.
    The DB row is never rewritten -- only what this module hands back to
    callers changes.

    A string that's already a valid code or code range is returned as-is.
    Otherwise this defers to the same `degree_explorer.normalize_session`
    the ACORN parser itself uses to recognise "2026 Winter" / "Winter 2026"
    -style legacy labels; anything neither of those can make sense of falls
    back to the original text VERBATIM (never dropped, never "?" — that
    fallback is what lets `formatSession` on the frontend render *something*
    reasonable no matter how old the row is).
    """
    text = (raw or "").strip()
    if not text or _SESSION_CODE_OR_RANGE_RE.match(text):
        return text
    return _parse_normalize_session(text) or text


def _session_sort_key(session: str) -> tuple[int, int | str]:
    """Chronological sort key for a (already-normalized) session string.
    Ranges ("20269-20271") sort by their start code. A session that never
    normalized to a leading digit string (an unrecognised legacy label kept
    verbatim by `_normalize_session`) sorts after every real session,
    stably, by its raw text -- better a visible straggler at the end than a
    crash or an arbitrary interleave."""
    first = session.split("-")[0]
    try:
        return (0, int(first))
    except (TypeError, ValueError):
        return (1, session)


def _is_snapshot_row(row: dict[str, Any]) -> bool:
    """A course row that's an ACORN in-progress/IPR snapshot rather than a
    real completed/graded registration -- see
    `_collapse_stale_snapshot_rows` below."""
    return row["status"] == "in_progress" or (row["grade"] or "").strip().upper() == "IPR"


def _collapse_stale_snapshot_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop stale in-progress/IPR "snapshot" rows a pre-5bbe9ae import wrote
    straight to the DB without the parser's own collapse
    (`degree_explorer._collapse_ipr_snapshots`) ever running for them (that
    collapse only runs on the PDF-upload path, not the bookmarklet-capture
    path, and didn't exist at all before that commit).

    ACORN prints a Y-course spanning sessions as an in-progress snapshot row
    in each earlier term plus a final row in its completing term. A student
    also can't be concurrently, genuinely "in progress" in the same course
    code twice -- so whenever a LATER-session row exists for the same code
    (whether that later row is itself a snapshot or a real completed/graded
    row), the earlier in-progress/IPR row is a stale leftover of a
    registration that has since resolved one way or another, and is
    dropped. Only the chronologically LAST in-progress/IPR row for a code
    is ever a genuine current registration (including a fresh retake), and
    it is always kept. Rows that are already completed/graded are never
    touched by this function -- a real retake of a previously-passed course
    is handled elsewhere (the Extra-designation rule), not here. Rows with
    no session are never collapsed (nothing to compare chronologically)."""
    kept: list[dict[str, Any]] = []
    for row in rows:
        if _is_snapshot_row(row) and row["session"]:
            superseded = any(
                other["id"] != row["id"]
                and other["code"].strip().upper() == row["code"].strip().upper()
                and other["session"]
                and other["session"] > row["session"]
                for other in rows
            )
            if superseded:
                continue
        kept.append(row)
    return kept


def _load_transcript_entries(db, user, data_key: bytes | None) -> list[dict[str, Any]]:
    """Query, decrypt, normalize-session, and collapse this user's
    `TranscriptEntry` rows exactly ONCE. Every `/api/me/*` route below
    (`_course_records`, `_transcript_courses`, `transcript()`) reads from
    this single canonical list instead of re-querying/re-decrypting the
    table itself, so they can never disagree about which rows exist, what a
    session string looks like, or which stale duplicate rows got dropped."""
    rows: list[dict[str, Any]] = []
    for entry in db.query(TranscriptEntry).filter_by(user_id=user.id).all():
        grade = (
            decrypt_field(entry.grade_encrypted, data_key)
            if (entry.grade_encrypted and data_key)
            else None
        )
        rows.append(
            {
                "id": entry.id,
                "code": entry.code,
                "title": entry.title,
                "credits": entry.credits,
                "mark": _decrypt_mark(entry.mark_encrypted, data_key),
                "grade": grade or "",
                "session": _normalize_session(entry.term_session),
                "status": entry.status if entry.status in _VALID_STATUSES else "completed",
            }
        )
    return _collapse_stale_snapshot_rows(rows)


def _course_records(db, user, data_key: bytes | None) -> list[CourseRecord]:
    cache = get_course_cache()
    records: list[CourseRecord] = []
    seen: set[str] = set()
    for row in _load_transcript_entries(db, user, data_key):
        breadth, distribution = _breadth_dist(cache, row["code"], row["session"])
        records.append(
            CourseRecord(
                code=row["code"],
                credits=row["credits"] or _credit_of(row["code"]),
                status=row["status"],
                session=row["session"],
                distribution=distribution,
                breadth_categories=breadth,
                grade=row["grade"] or None,
                mark=row["mark"],
            )
        )
        seen.add(row["code"].strip().upper())

    plan = db.query(Plan).filter_by(user_id=user.id, is_primary=True).first()
    if plan is not None:
        for item in plan.items:
            if item.course_code.strip().upper() in seen:
                continue
            session = _normalize_session(item.term_session)
            breadth, distribution = _breadth_dist(cache, item.course_code, session)
            records.append(
                CourseRecord(
                    code=item.course_code,
                    credits=_credit_of(item.course_code),
                    status="planned",
                    session=session,
                    distribution=distribution,
                    breadth_categories=breadth,
                )
            )
    return records


def _program_requirements(db, user) -> list[ProgramRequirement]:
    cache = get_course_cache()
    reqs: list[ProgramRequirement] = []
    enrolments = (
        db.query(ProgramEnrolment).filter_by(user_id=user.id).order_by(ProgramEnrolment.position).all()
    )
    for enrolment in enrolments:
        program = cache.get_program(enrolment.program_code)
        if program is None:
            continue
        requirement = ProgramRequirement.from_program(program, enrolment.program_code)
        if requirement is not None:
            reqs.append(requirement)
    return reqs


def _issues(issues) -> list[dict[str, Any]]:
    return [asdict(issue) for issue in issues]


def _enrolments_for_user(db, user) -> list[ProgramEnrolment]:
    """Same query/ordering as `backend.api.programs.list_my_programs`."""
    return (
        db.query(ProgramEnrolment)
        .filter_by(user_id=user.id)
        .order_by(ProgramEnrolment.position, ProgramEnrolment.created_at)
        .all()
    )


def _program_refs(
    enrolments: list[ProgramEnrolment], records: list[CourseRecord]
) -> list[dict[str, Any]]:
    """`EnrolledProgramRef[]` (frontend/src/api/types.ts) — the same
    `{code, name, startSession}` mapping `httpClient.getMyPrograms` derives
    client-side from `_enrolment_json` (backend/api/programs.py), done here
    server-side so `/api/me` doesn't need a second round trip.

    Each ref also carries the AUTHORITATIVE program-completion summary
    (`earnedCredits`/`totalCredits`/`percent`/`requirementsLoaded`) computed by
    `_audit.program_progress_summary` — the single source of truth every card
    that shows "how much of this program have I completed" must use, so the
    top-of-page summary can't disagree with the per-group breakdown (which is
    the same engine). `requirementsLoaded=False` means the program's
    requirements aren't cached yet, so the client should offer "Load
    requirements" rather than treat 0% as a real answer."""
    cache = get_course_cache()
    rows = _transcript_rows(records)
    refs: list[dict[str, Any]] = []
    for enrolment, j in zip(enrolments, map(_enrolment_json, enrolments)):
        ref = {
            "code": j["code"],
            "name": j["title"] or j["code"],
            "startSession": j["startSession"] or "",
        }
        program = cache.get_program(enrolment.program_code)
        summary = _program_progress_summary(
            program, ProgramRow(code=j["code"], title=j["title"] or "", program_type=j["programType"]), rows
        )
        ref["earnedCredits"] = summary["earnedCredits"]
        ref["totalCredits"] = summary["totalCredits"]
        ref["percent"] = summary["percent"]
        ref["requirementsLoaded"] = summary["loaded"]
        refs.append(ref)
    return refs


def _transcript_courses(db, user, data_key: bytes | None) -> list[dict[str, Any]]:
    """`TranscriptCourse[]` (frontend/src/api/types.ts) — a flat, per-course
    variant of the `/transcript` route's per-session grouping, reading from
    the same canonical, normalized, collapsed row list `_load_transcript_
    entries` builds (so the Transcript screen's table/projector and the
    `/transcript` route's session groups never disagree about which rows
    exist)."""
    return [
        {
            "code": row["code"],
            "title": row["title"],
            "credits": row["credits"],
            "mark": row["mark"],
            "grade": row["grade"],
            "session": row["session"],
            "status": row["status"],
        }
        for row in _load_transcript_entries(db, user, data_key)
    ]


def _transcript_rows(records: list[CourseRecord]) -> list[TranscriptRow]:
    """The `_audit` engine's `TranscriptRow` view of the same `CourseRecord`s
    `_course_records` builds — shared by the requirement-progress and
    program-summary computations so they can't diverge."""
    return [
        TranscriptRow(
            code=r.code,
            credits=r.credits,
            status=r.status,
            session=r.session or "",
            grade=r.grade or "",
            mark=r.mark,
            is_artsci=r.is_artsci,
        )
        for r in records
    ]


def _requirement_progress_by_program(
    enrolments: list[ProgramEnrolment], records: list[CourseRecord]
) -> dict[str, list[dict[str, Any]]]:
    """`Record<programCode, RequirementProgress[]>` (frontend/src/api/
    types.ts), via `backend.api._audit.requirement_progress` — the
    already-written per-`RequirementGroup` cross-reference against the
    transcript, adapted from the same `CourseRecord`s `_course_records`
    builds for the other `/api/me/*` routes."""
    cache = get_course_cache()
    rows = _transcript_rows(records)
    progress: dict[str, list[dict[str, Any]]] = {}
    for enrolment in enrolments:
        program = cache.get_program(enrolment.program_code)
        if program is None:
            continue
        progress[enrolment.program_code] = _audit_requirement_progress(program, rows)
    return progress


@bp.route("", methods=["GET"])
@require_auth
def student_record():
    """`GET /api/me` — the aggregate `StudentRecord` the frontend's
    `httpClient.getMyRecord()` fetches for the Dashboard and several other
    screens (frontend/src/api/client.ts, frontend/src/api/types.ts). A thin
    composition of the same building blocks the sibling `/summary`,
    `/transcript`, `/requirements` routes here and `GET /api/me/programs`
    (backend/api/programs.py) already use — see those for the canonical
    per-field behavior; this route does not change any of them."""
    db = db_session()
    user = current_user()
    data_key = current_data_key()

    enrolments = _enrolments_for_user(db, user)
    records = _course_records(db, user, data_key)

    return jsonify(
        {
            "programs": _program_refs(enrolments, records),
            "transcript": _transcript_courses(db, user, data_key),
            "requirementProgress": _requirement_progress_by_program(enrolments, records),
            "cgpa": cgpa(records).gpa or 0.0,
        }
    )


@bp.route("/summary", methods=["GET"])
@require_auth
def summary():
    db = db_session()
    user = current_user()
    records = _course_records(db, user, current_data_key())

    credits = degree_credit_summary(records)
    degree_issues = validate_degree_credits(credits)
    breadth = evaluate_breadth(records)

    cgpa_summary = cgpa(records)
    cgpa_value = cgpa_summary.gpa or 0.0
    recent_sessions = sorted({r.session for r in records if r.session}, reverse=True)
    recent_gpa = sgpa(records, recent_sessions[0]).gpa if recent_sessions else None
    standing = academic_standing(cgpa_value, recent_gpa if recent_gpa is not None else cgpa_value)

    grad = graduation_eligibility(records, _program_requirements(db, user), cgpa_value, standing)

    return jsonify(
        {
            "credits": asdict(credits),
            "degreeIssues": _issues(degree_issues),
            "breadth": asdict(breadth),
            "gpa": {
                "cgpa": cgpa_summary.gpa,
                "creditsCounted": cgpa_summary.credits_counted,
                "recent": recent_gpa,
            },
            "standing": standing,
            "probationCap": {
                term: max_credits_for_term(standing, term) for term in ("fall", "winter", "summer")
            },
            "graduation": {"eligible": grad.eligible, "issues": _issues(grad.issues)},
        }
    )


@bp.route("/transcript", methods=["GET"])
@require_auth
def transcript():
    """`GET /api/me/transcript` — the ONE authoritative source for every
    GPA figure the Transcript screen displays (frontend/src/screens/
    Transcript.tsx): per-session `sgpa`, a running per-session `cumGpa`
    (chronological order, same `backend.planner.gpa` engine as the rest of
    the app -- see that module's `grade_points()` for the letter-over-mark
    precedence rule), and the overall `cgpa`. The frontend must not
    recompute any of these client-side from raw marks; that split engine is
    exactly what caused the CGPA/"Cum" mismatch this route now closes off.
    `cumGpa` of the chronologically LAST session is mathematically
    identical to the top-level `cgpa` (both are `cgpa()` over the exact same
    accumulated `graded` list) -- not a coincidence to maintain by hand.
    """
    db = db_session()
    user = current_user()
    data_key = current_data_key()

    records = _course_records(db, user, data_key)
    graded = [r for r in records if r.status != "planned"]

    by_session: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _load_transcript_entries(db, user, data_key):
        by_session[row["session"] or ""].append(
            {
                "code": row["code"],
                "title": row["title"],
                "credits": row["credits"],
                "grade": row["grade"] or None,
                "mark": row["mark"],
                "status": row["status"],
            }
        )

    chronological = sorted(by_session, key=_session_sort_key)  # oldest first
    running: list[CourseRecord] = []
    cum_by_session: dict[str, float | None] = {}
    for s in chronological:
        running = running + [r for r in graded if (r.session or "") == s]
        cum_by_session[s] = cgpa(running).gpa
    overall_cgpa = cum_by_session[chronological[-1]] if chronological else None

    sessions = [
        {
            "session": s,
            "courses": by_session[s],
            "sgpa": sgpa(graded, s).gpa,
            "cumGpa": cum_by_session[s],
        }
        for s in reversed(chronological)  # newest first, matching prior behavior
    ]

    warnings: list[str] = []
    if any(grade_mark_step_mismatch(r) for r in records):
        warnings.append(_REIMPORT_WARNING)

    return jsonify({"sessions": sessions, "cgpa": overall_cgpa, "warnings": warnings})


@bp.route("/requirements", methods=["GET"])
@require_auth
def requirements():
    db = db_session()
    user = current_user()
    records = _course_records(db, user, current_data_key())
    combination, issues = evaluate_program_combination(_program_requirements(db, user), records)
    return jsonify({"combination": asdict(combination), "issues": _issues(issues)})


@bp.route("/alerts", methods=["GET"])
@require_auth
def alerts():
    db = db_session()
    user = current_user()
    records = _course_records(db, user, current_data_key())
    degree_issues = validate_degree_credits(degree_credit_summary(records))
    _combination, combo_issues = evaluate_program_combination(_program_requirements(db, user), records)
    surfaced = [
        asdict(issue)
        for issue in (degree_issues + combo_issues)
        if issue.severity in ("error", "warning")
    ]
    return jsonify({"alerts": surfaced})
