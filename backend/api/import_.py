"""Import blueprint: `POST /api/import/pdf`, `POST /api/import/capture`.

Parses an Academic History PDF (downloaded from ACORN; PDF handling lives in
`backend.ingest.degree_explorer`, module name kept as-is -- see that module's
docstring) or a bookmarklet capture (the `<degree-explorer-capture>…</degree-
explorer-capture>` JSON) into the caller's transcript + program enrolments,
then returns the record + parser warnings for the onboarding ImportPreview
step (`design/screens/01-auth-and-onboarding.md`).

**Account-optional by design.** Both routes parse for anyone; only the write
is gated on a session (`_import_result`). A guest gets `saved: false` plus the
parsed `courses` and stores them client-side -- onboarding's credits step is
reachable without an account, so a 401 there was a dead end, not a nudge.

Transcript grades/marks are encrypted at rest with the caller's per-session data
key (ADR-0005); nothing sensitive is written in plaintext. The guest path writes
nothing at rest, so that contract is untouched.

Parsing is deliberately unauthenticated CPU work on an uploaded file. The 8 MB
cap below bounds a single request; there is no per-IP rate limit yet, which is
the one thing to add if this is ever abused (noted in docs/roadmap.md).
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request

from backend.api import current_data_key, current_user, db_session, json_error, require_auth
from backend.ingest.degree_explorer import (
    DegreeExplorerParseError,
    DraftCourse,
    DraftProgram,
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

    return {**_preview(draft), "saved": True}


def _preview(draft: StudentRecordDraft) -> dict[str, Any]:
    """JSON-safe view of a parsed draft, independent of any account.

    Shared by the signed-in and guest paths so both return the same shape --
    the guest path additionally needs `courses`, since with no account to
    write to, the response *is* the only copy and the client stores it
    (localStorage, `frontend/src/api/guestProfile.ts`).

    Grades/marks are returned in the clear here. That is not a leak: this is
    the caller's own PDF coming straight back to them over the same request,
    never persisted server-side, and never touching another user's row. The
    ADR-0005 encryption contract governs data *at rest*, which the guest path
    does not create.
    """
    return {
        "programs": [
            {"code": p.code, "title": p.title, "startSession": p.start_session}
            for p in draft.programs
        ],
        "courses": [
            {
                "code": c.code.strip().upper(),
                "title": c.title or None,
                "credits": c.credits or 0.5,
                "session": c.session or None,
                "status": c.status,
                "grade": c.grade or None,
                "mark": c.mark,
            }
            for c in draft.courses
        ],
        "courseCount": len(draft.courses),
        "cgpa": draft.cgpa,
        "warnings": draft.warnings,
    }


def _import_result(draft: StudentRecordDraft):
    """Persist for a signed-in caller, or hand the parse straight back to a guest.

    Importing is deliberately account-optional (the onboarding "Do you have
    existing credits?" step is reachable with no account, and blocking it there
    is what made a guest dead-end). Parsing needs the server -- pdfplumber has
    no browser equivalent -- but persistence does not, so only persistence is
    gated on having a session.
    """
    user = current_user()
    if user is None:
        return jsonify({**_preview(draft), "saved": False})
    return jsonify(_persist(db_session(), user, current_data_key(), draft))


@bp.route("/pdf", methods=["POST"])
def import_pdf():
    upload = request.files.get("file")
    if upload is None:
        return json_error("Attach your Academic History PDF (from ACORN) as the form field 'file'.", 422)
    data = upload.read(_MAX_PDF_BYTES + 1)
    if len(data) > _MAX_PDF_BYTES:
        return json_error("That PDF is too large (max 8 MB).", 413)
    try:
        draft = parse_pdf_bytes(data)
    except DegreeExplorerParseError as exc:
        return json_error(f"Could not read that Academic History PDF: {exc}", 422)
    return _import_result(draft)


@bp.route("/courses", methods=["POST"])
@require_auth
def import_courses():
    """Persist an already-parsed record — the guest-import hand-off.

    A visitor who imported without an account holds the parse in localStorage
    (`saved: false` from the routes above). When they later sign up, SignUp.tsx
    posts it here so the credits follow them into the account instead of being
    stranded in one browser. Body is exactly what `_preview` returned.

    Re-parsing isn't an option: the PDF is long gone by then, only the parsed
    result was kept.
    """
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return json_error("Send the stored import as JSON.", 422)

    raw_courses = payload.get("courses")
    if not isinstance(raw_courses, list):
        return json_error("Expected a 'courses' array.", 422)

    try:
        draft = StudentRecordDraft(
            programs=[
                DraftProgram(
                    code=str(p["code"]).strip().upper(),
                    title=str(p.get("title") or ""),
                    start_session=str(p.get("startSession") or ""),
                )
                for p in payload.get("programs") or []
                if isinstance(p, dict) and p.get("code")
            ],
            courses=[
                DraftCourse(
                    code=str(c["code"]).strip().upper(),
                    title=str(c.get("title") or ""),
                    credits=float(c.get("credits") or 0.5),
                    mark=float(c["mark"]) if c.get("mark") is not None else None,
                    grade=str(c.get("grade") or ""),
                    session=str(c.get("session") or ""),
                    status=str(c.get("status") or "completed"),
                )
                for c in raw_courses
                if isinstance(c, dict) and c.get("code")
            ],
            cgpa=payload.get("cgpa") if isinstance(payload.get("cgpa"), (int, float)) else None,
        )
    except (TypeError, ValueError) as exc:
        return json_error(f"That stored import couldn't be read: {exc}", 422)

    return jsonify(_persist(db_session(), current_user(), current_data_key(), draft))


@bp.route("/capture", methods=["POST"])
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
    return _import_result(draft)
