"""Import blueprint: `POST /api/import/pdf`, `POST /api/import/capture`.

Parses a Degree Explorer audit (PDF, via `backend.ingest.degree_explorer`) or a
bookmarklet capture (the `<degree-explorer-capture>…</degree-explorer-capture>`
JSON) into the signed-in user's transcript + program enrolments, then returns the
persisted record + parser warnings for the onboarding ImportPreview step
(`design/screens/01-auth-and-onboarding.md`).

Transcript grades/marks are encrypted at rest with the caller's per-session data
key (ADR-0005); nothing sensitive is written in plaintext.
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request

from backend.api import current_data_key, current_user, db_session, json_error, require_auth
from backend.ingest.degree_explorer import (
    DegreeExplorerParseError,
    StudentRecordDraft,
    parse_capture,
    parse_pdf_bytes,
)
from backend.models_db import ProgramEnrolment, TranscriptEntry
from backend.security.crypto import encrypt_field

bp = Blueprint("import", __name__, url_prefix="/api/import")

_MAX_PDF_BYTES = 8 * 1024 * 1024  # 8 MB


def _persist(db, user, data_key, draft: StudentRecordDraft) -> dict[str, Any]:
    """Replace the user's transcript with the imported courses and add any new
    program enrolments. Returns a JSON-safe preview of what was stored."""
    db.query(TranscriptEntry).filter_by(user_id=user.id).delete()
    for course in draft.courses:
        grade = course.grade or None
        mark = course.mark
        db.add(
            TranscriptEntry(
                user_id=user.id,
                code=course.code.strip().upper(),
                title=course.title or None,
                credits=course.credits or 0.5,
                term_session=course.session or None,
                status=course.status,
                grade_encrypted=encrypt_field(grade, data_key) if (grade and data_key) else None,
                mark_encrypted=(
                    encrypt_field(str(mark), data_key) if (mark is not None and data_key) else None
                ),
            )
        )

    existing = {
        e.program_code
        for e in db.query(ProgramEnrolment).filter_by(user_id=user.id).all()
    }
    for program in draft.programs:
        if program.code in existing:
            continue
        db.add(
            ProgramEnrolment(
                user_id=user.id,
                program_code=program.code,
                program_title=program.title or None,
                start_session=program.start_session or None,
            )
        )
        existing.add(program.code)

    db.commit()

    return {
        "programs": [
            {"code": p.code, "title": p.title, "startSession": p.start_session}
            for p in draft.programs
        ],
        "courseCount": len(draft.courses),
        "cgpa": draft.cgpa,
        "warnings": draft.warnings,
    }


@bp.route("/pdf", methods=["POST"])
@require_auth
def import_pdf():
    upload = request.files.get("file")
    if upload is None:
        return json_error("Attach the Degree Explorer PDF as the form field 'file'.", 422)
    data = upload.read(_MAX_PDF_BYTES + 1)
    if len(data) > _MAX_PDF_BYTES:
        return json_error("That PDF is too large (max 8 MB).", 413)
    try:
        draft = parse_pdf_bytes(data)
    except DegreeExplorerParseError as exc:
        return json_error(f"Could not read that Degree Explorer PDF: {exc}", 422)
    return jsonify(_persist(db_session(), current_user(), current_data_key(), draft))


@bp.route("/capture", methods=["POST"])
@require_auth
def import_capture():
    payload: Any = request.get_json(silent=True)
    if payload is None:
        # Also accept the raw pasted "<degree-explorer-capture>…</…>" text.
        payload = request.get_data(as_text=True)
    if not payload:
        return json_error("Paste the bookmarklet capture as JSON or wrapped text.", 422)
    try:
        draft = parse_capture(payload)
    except DegreeExplorerParseError as exc:
        return json_error(f"Could not read that capture: {exc}", 422)
    return jsonify(_persist(db_session(), current_user(), current_data_key(), draft))
