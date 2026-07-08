"""Share blueprint: `POST /api/share` (create a read-only link),
`GET /api/share/<token>` (public, no auth), `DELETE /api/share/<token>` (revoke).

The public view exposes only plaintext-safe data — course codes, credits,
sessions, statuses, and program codes — never grades or marks. That holds by
construction: the owner's Fernet data key lives only in their session cookie
(ADR-0005), so `view_share` cannot decrypt anything even if it wanted to.
"""

from __future__ import annotations

import datetime as dt
import secrets
from typing import Any

from flask import Blueprint, jsonify, request

from backend.api import current_user, db_session, json_error, require_auth
from backend.extensions import get_course_cache
from backend.models_db import Plan, ProgramEnrolment, Share, TranscriptEntry
from backend.planner.types import CourseRecord, ProgramRequirement
from backend.planner.validators import degree_credit_summary, evaluate_program_combination

bp = Blueprint("share", __name__, url_prefix="/api/share")

_VALID_STATUSES = ("completed", "in_progress", "planned", "extra")


@bp.route("", methods=["POST"])
@require_auth
def create_share():
    data = request.get_json(silent=True) or {}
    token = secrets.token_urlsafe(24)
    db = db_session()
    db.add(
        Share(
            token=token,
            user_id=current_user().id,
            include_plan=bool(data.get("includePlan", True)),
        )
    )
    db.commit()
    return jsonify({"token": token, "path": f"/share/{token}"})


@bp.route("/<token>", methods=["DELETE"])
@require_auth
def revoke_share(token: str):
    db = db_session()
    share = db.query(Share).filter_by(token=token, user_id=current_user().id).first()
    if share is not None and share.is_active:
        share.revoked_at = dt.datetime.now(dt.timezone.utc)
        db.commit()
    return jsonify({"revoked": True})


@bp.route("/<token>", methods=["GET"])
def view_share(token: str):
    """Public, unauthenticated read-only snapshot. Grades/marks never included."""
    db = db_session()
    share = db.query(Share).filter_by(token=token).first()
    if share is None or not share.is_active:
        return json_error("This shared link is no longer available.", 404)

    user_id = share.user_id
    records = [
        CourseRecord(
            code=entry.code,
            credits=entry.credits or 0.5,
            status=entry.status if entry.status in _VALID_STATUSES else "completed",
            session=entry.term_session,
        )
        for entry in db.query(TranscriptEntry).filter_by(user_id=user_id).all()
    ]
    credits = degree_credit_summary(records)

    enrolments = db.query(ProgramEnrolment).filter_by(user_id=user_id).all()
    cache = get_course_cache()
    reqs: list[ProgramRequirement] = []
    for enrolment in enrolments:
        program = cache.get_program(enrolment.program_code)
        if program is not None:
            requirement = ProgramRequirement.from_program(program, enrolment.program_code)
            if requirement is not None:
                reqs.append(requirement)
    combination, _issues = evaluate_program_combination(reqs, records)

    out: dict[str, Any] = {
        "programs": [
            {"code": e.program_code, "title": e.program_title} for e in enrolments
        ],
        "credits": {
            "totalCredits": credits.total_credits,
            "artsciCredits": credits.artsci_credits,
            "level300PlusCredits": credits.level_300_plus_credits,
        },
        "combination": {"comboType": combination.combo_type, "comboValid": combination.combo_valid},
        "includePlan": share.include_plan,
    }
    if share.include_plan:
        plan = db.query(Plan).filter_by(user_id=user_id, is_primary=True).first()
        out["plan"] = (
            [
                {"courseCode": i.course_code, "termSession": i.term_session, "status": i.status}
                for i in plan.items
            ]
            if plan is not None
            else []
        )
    return jsonify(out)
