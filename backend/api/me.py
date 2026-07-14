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

from collections import defaultdict
from dataclasses import asdict
from typing import Any

from flask import Blueprint, jsonify

from backend.api import current_data_key, current_user, db_session, require_auth
from backend.api._audit import TranscriptRow
from backend.api._audit import requirement_progress as _audit_requirement_progress
from backend.api.programs import _enrolment_json
from backend.data_sources.cache import SqliteCache
from backend.extensions import get_course_cache
from backend.models_db import Plan, ProgramEnrolment, TranscriptEntry
from backend.planner.course_code import parse_course_code
from backend.planner.gpa import academic_standing, cgpa, max_credits_for_term, sgpa
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


def _course_records(db, user, data_key: bytes | None) -> list[CourseRecord]:
    cache = get_course_cache()
    records: list[CourseRecord] = []
    seen: set[str] = set()
    for entry in db.query(TranscriptEntry).filter_by(user_id=user.id).all():
        grade = (
            decrypt_field(entry.grade_encrypted, data_key)
            if (entry.grade_encrypted and data_key)
            else None
        )
        breadth, distribution = _breadth_dist(cache, entry.code, entry.term_session)
        status = entry.status if entry.status in _VALID_STATUSES else "completed"
        records.append(
            CourseRecord(
                code=entry.code,
                credits=entry.credits or _credit_of(entry.code),
                status=status,
                session=entry.term_session,
                distribution=distribution,
                breadth_categories=breadth,
                grade=grade or None,
                mark=_decrypt_mark(entry.mark_encrypted, data_key),
            )
        )
        seen.add(entry.code.strip().upper())

    plan = db.query(Plan).filter_by(user_id=user.id, is_primary=True).first()
    if plan is not None:
        for item in plan.items:
            if item.course_code.strip().upper() in seen:
                continue
            breadth, distribution = _breadth_dist(cache, item.course_code, item.term_session)
            records.append(
                CourseRecord(
                    code=item.course_code,
                    credits=_credit_of(item.course_code),
                    status="planned",
                    session=item.term_session,
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


def _program_refs(enrolments: list[ProgramEnrolment]) -> list[dict[str, Any]]:
    """`EnrolledProgramRef[]` (frontend/src/api/types.ts) — the same
    `{code, name, startSession}` mapping `httpClient.getMyPrograms` derives
    client-side from `_enrolment_json` (backend/api/programs.py), done here
    server-side so `/api/me` doesn't need a second round trip."""
    return [
        {"code": j["code"], "name": j["title"] or j["code"], "startSession": j["startSession"] or ""}
        for j in map(_enrolment_json, enrolments)
    ]


def _transcript_courses(db, user, data_key: bytes | None) -> list[dict[str, Any]]:
    """`TranscriptCourse[]` (frontend/src/api/types.ts) — a flat, per-course
    variant of the `/transcript` route's per-session grouping, reusing the
    same decrypt helpers (`decrypt_field`, `_decrypt_mark`)."""
    out: list[dict[str, Any]] = []
    for entry in db.query(TranscriptEntry).filter_by(user_id=user.id).all():
        grade = (
            decrypt_field(entry.grade_encrypted, data_key)
            if (entry.grade_encrypted and data_key)
            else None
        )
        out.append(
            {
                "code": entry.code,
                "title": entry.title,
                "credits": entry.credits,
                "mark": _decrypt_mark(entry.mark_encrypted, data_key),
                "grade": grade or "",
                "session": entry.term_session or "",
                "status": entry.status if entry.status in _VALID_STATUSES else "completed",
            }
        )
    return out


def _requirement_progress_by_program(
    enrolments: list[ProgramEnrolment], records: list[CourseRecord]
) -> dict[str, list[dict[str, Any]]]:
    """`Record<programCode, RequirementProgress[]>` (frontend/src/api/
    types.ts), via `backend.api._audit.requirement_progress` — the
    already-written per-`RequirementGroup` cross-reference against the
    transcript, adapted from the same `CourseRecord`s `_course_records`
    builds for the other `/api/me/*` routes."""
    cache = get_course_cache()
    rows = [
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
            "programs": _program_refs(enrolments),
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
    db = db_session()
    user = current_user()
    data_key = current_data_key()

    records = _course_records(db, user, data_key)
    graded = [r for r in records if r.status != "planned"]

    by_session: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in db.query(TranscriptEntry).filter_by(user_id=user.id).all():
        grade = (
            decrypt_field(entry.grade_encrypted, data_key)
            if (entry.grade_encrypted and data_key)
            else None
        )
        by_session[entry.term_session or ""].append(
            {
                "code": entry.code,
                "title": entry.title,
                "credits": entry.credits,
                "grade": grade,
                "mark": _decrypt_mark(entry.mark_encrypted, data_key),
                "status": entry.status,
            }
        )

    sessions = [
        {"session": s, "courses": by_session[s], "sgpa": sgpa(graded, s).gpa}
        for s in sorted(by_session, reverse=True)
    ]
    return jsonify({"sessions": sessions, "cgpa": cgpa(graded).gpa})


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
