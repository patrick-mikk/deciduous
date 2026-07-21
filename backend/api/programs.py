"""Programs blueprint: catalog search/detail/requirements + enrolled programs.

Two families of endpoints, both registered off this single module-level `bp`
(the blueprint auto-registration contract in `backend/api/__init__.py` only
picks up one `bp` per module):

- **Catalog** (public, no auth) - `GET /api/programs`, `GET /api/programs/:code`,
  `GET /api/programs/:code/requirements`, `POST /api/programs/:code/requirements/reparse`.
  Backed by `ProgramClient` (Academic Calendar) + the shared `SqliteCache`
  (`backend.extensions.get_course_cache`), reused exactly as the TUI's
  `SearchService` uses them (`backend/tui/service.py`) - cache-first, and the
  Gemini grouper only runs on the explicit `/reparse` action, never during a
  plain search (see `design/06-data-model-and-api.md`: "Requirement grouping
  is on-demand").
- **Enrolled programs** (`require_auth`) - `GET/POST /api/me/programs`,
  `DELETE /api/me/programs/:code`. Persists to `ProgramEnrolment`
  (`backend/models_db.py`) and enforces the structural POSt-combination rules
  from `design/09-uoft-degree-rules.md` #2 that are derivable from program
  codes alone:
    - **one-type-per-subject** (eff. Sept 2025): only one Specialist/Major/
      Minor per subject area (same 4-digit code) - a hard 409 on conflict.
    - **combination shape**: 1 Specialist, OR 2 Majors, OR 1 Major + 2 Minors
      - reported as a non-blocking `combination` summary (students add/drop
      programs incrementally while exploring, so this never blocks a POST).
  The >=12.0-distinct-credits rule (#1) needs each program's completion-
  requirement course lists cross-referenced against the transcript/plan; that
  belongs to the future plan validator, not this endpoint, and is
  deliberately NOT computed here.

`ProgramClient` and `_grouper()` are referenced at module level (not
constructed inline) so tests can monkeypatch them - see
`backend/tests/test_api_programs.py` and the identical pattern in
`backend/tui/service.py` / `backend/tests/test_tui_service.py`.
"""

from __future__ import annotations

import datetime
import re
from collections import Counter
from dataclasses import replace

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import IntegrityError

from backend.api import current_user, db_session, json_error, require_auth
from backend.api._audit import effective_total_credits
from backend.data_sources.cache import PROGRAMS_CATALOG_FULL_AT
from backend.data_sources.llm_grouper import GeminiGrouper, LLMGroupingError
from backend.data_sources.models import Program, RequirementGroup
from backend.data_sources.programs.client import ProgramClient
from backend.extensions import get_course_cache
from backend.models_db import ProgramEnrolment

bp = Blueprint("programs", __name__)

_DEFAULT_PAGE_SIZE = 20
_MAX_PAGE_SIZE = 100
# Page cap for the one-time full-catalog pull below — same generous ceiling as
# `refresh_cache.py`'s (the whole catalog needed ~14 pages as of 2026-07-08);
# `ProgramClient.search` stops early at the first empty page and throttles
# between pages, so the cap only bounds a runaway, it isn't the expected cost.
_FULL_CATALOG_MAX_PAGES = 60

# AS + 3-letter type prefix + 3-4 digit subject + optional stream letter, e.g.
# "ASMAJ1305A" (see backend/data_sources/programs/client.py's own copy of this
# shape - duplicated here, deliberately, so this module stays decoupled).
_PROGRAM_CODE_RE = re.compile(r"^AS(SPE|MAJ|MIN|FOC|CER)(\d{3,4})([A-Z]?)$")
_TYPE_LABELS = {
    "SPE": "specialist",
    "MAJ": "major",
    "MIN": "minor",
    "FOC": "focus",
    "CER": "certificate",
}
# Only these three types participate in the one-type-per-subject rule and the
# combination shape - Focus (a cluster inside a Specialist/Major) and
# Certificate (doesn't count toward degree *program* requirements, per
# design/09-uoft-degree-rules.md #2) are informational only.
_COMBINATION_TYPES = ("specialist", "major", "minor")


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _parse_program_code(code: str) -> tuple[str, str] | None:
    """`(program_type, subject_key)` from a program code, or `None` if unparseable.

    `subject_key` is the code's 3-4 digit subject number (the "same final
    4-digit code" the one-type-per-subject rule keys off of) - stream letter
    suffixes (A/B/C) are intentionally excluded so e.g. "ASMAJ1305A" and
    "ASMAJ1305B" share one subject key.
    """
    match = _PROGRAM_CODE_RE.match(code.strip().upper())
    if match is None:
        return None
    return _TYPE_LABELS.get(match.group(1), ""), match.group(2)


def _grouper() -> GeminiGrouper:
    """Build a `GeminiGrouper`, loading `.env` first (picks up `GEMINI_API_KEY`)."""
    from backend.config import load_env

    load_env()
    return GeminiGrouper()


# --------------------------------------------------------------- JSON shapes
def _program_json(program: Program) -> dict:
    """Lightweight card shape for search results (see design/06 `Program`)."""
    return {
        "code": program.code,
        "title": program.title,
        "programType": program.program_type,
        "department": program.department,
        "departmentUrl": program.department_url,
        "enrolmentRequirements": program.enrolment_requirements,
        "totalCredits": effective_total_credits(program),
    }


def _requirement_group_json(group: RequirementGroup) -> dict:
    return {
        "heading": group.heading,
        "credits": group.credits,
        "isNote": group.is_note,
        "courseCodes": group.course_codes,
        "rules": [
            {"credits": r.credits, "description": r.description, "courseCodes": r.course_codes}
            for r in group.rules
        ],
        "courses": [
            {"code": c.code, "credits": c.credits, "notes": c.notes} for c in group.courses
        ],
        "notes": group.notes,
    }


def _requirements_json(program: Program) -> dict:
    return {
        "code": program.code,
        "totalCredits": effective_total_credits(program),
        # True once a course under any group carries per-course detail - only
        # the Gemini grouper populates `courses` (design/06: "Per-course
        # credits + notes only appear after LLM grouping").
        "requirementsLoaded": any(g.courses for g in program.completion_requirements),
        "completionRequirements": [
            _requirement_group_json(g) for g in program.completion_requirements
        ],
        "rawCompletionText": program.raw_completion_text,
    }


def _program_detail_json(program: Program) -> dict:
    data = _program_json(program)
    data.update(_requirements_json(program))
    return data


def _enrolment_json(row: ProgramEnrolment) -> dict:
    parsed = _parse_program_code(row.program_code)
    return {
        "id": row.id,
        "code": row.program_code,
        "title": row.program_title,
        "startSession": row.start_session,
        "programType": parsed[0] if parsed else "",
        "subject": parsed[1] if parsed else "",
        "position": row.position,
        "addedAt": row.created_at.isoformat(),
    }


# -------------------------------------------------------------------- lookup
def _fetch_program(code: str) -> Program | None:
    """Cache-first single-program lookup; falls back to a live Calendar search.

    Mirrors `backend.tui.service.SearchService._search_programs`: the cache is
    checked first, and any *heuristically*-parsed program fetched live is
    cached before returning so a follow-up `/requirements` call is instant.
    """
    cache = get_course_cache()
    cached = cache.get_program(code)
    if cached is not None:
        return cached

    matches = ProgramClient().search(code)
    if matches:
        cache.upsert_programs(matches, _now_iso())
    for program in matches:
        if program.code == code:
            return program
    return None


# ------------------------------------------------------------------ catalog
@bp.route("/api/programs", methods=["GET"])
def search_programs():
    q = (request.args.get("q") or "").strip()
    program_type = (request.args.get("type") or "").strip().lower()
    subject = (request.args.get("subject") or "").strip()

    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        return json_error("page must be an integer.", 422)
    try:
        page_size = int(request.args.get("pageSize", _DEFAULT_PAGE_SIZE))
    except ValueError:
        return json_error("pageSize must be an integer.", 422)
    page = max(1, page)
    page_size = max(1, min(page_size, _MAX_PAGE_SIZE))

    cache = get_course_cache()
    results = cache.search_programs(q, limit=500)

    # A "catalog browse" (no q, no type — e.g. onboarding loading the whole
    # list to filter client-side) must see the FULL catalog. Until a full pull
    # has completed (PROGRAMS_CATALOG_FULL_AT meta, normally set by
    # backend/scripts/refresh_cache.py), the cache may hold only the handful
    # of programs individual keyword searches happened to seed — so a browse
    # self-heals with one full, page-throttled pull instead of trusting it.
    is_browse = not q and not program_type
    needs_full_pull = is_browse and cache.get_meta(PROGRAMS_CATALOG_FULL_AT) is None
    if needs_full_pull or (not results and not is_browse):
        try:
            if needs_full_pull:
                fetched = ProgramClient().search(max_pages=_FULL_CATALOG_MAX_PAGES)
            else:
                # Keyword/type cache miss: pull live from the Academic Calendar
                # (docs/conventions.md: cache aggressively) and seed the cache.
                fetched = ProgramClient().search(q, program_type)
        except Exception as exc:  # noqa: BLE001 - degrade to a clean JSON error
            if not results:
                return json_error(f"Program search failed: {exc}", 502)
            # Partial cache beats a hard failure for a browse; say so in the log.
            current_app.logger.warning(
                "Full program-catalog pull failed (%s); serving %d cached program(s).",
                exc,
                len(results),
            )
            fetched = []
        if fetched:
            fetched_at = _now_iso()
            cache.upsert_programs(fetched, fetched_at)
            if needs_full_pull:
                cache.set_meta(PROGRAMS_CATALOG_FULL_AT, fetched_at)
            results = cache.search_programs(q, limit=500)

    if program_type:
        results = [p for p in results if p.program_type == program_type]
    if subject:
        results = [
            p for p in results
            if (parsed := _parse_program_code(p.code)) is not None and parsed[1] == subject
        ]

    total = len(results)
    start = (page - 1) * page_size
    page_items = results[start:start + page_size]

    return jsonify(
        {
            "programs": [_program_json(p) for p in page_items],
            "page": page,
            "pageSize": page_size,
            "total": total,
            "totalPages": (total + page_size - 1) // page_size if total else 0,
        }
    )


@bp.route("/api/programs/<code>", methods=["GET"])
def get_program(code: str):
    program = _fetch_program(code.strip().upper())
    if program is None:
        return json_error(f"No program found for code {code!r}.", 404)
    return jsonify(_program_detail_json(program))


@bp.route("/api/programs/<code>/requirements", methods=["GET"])
def get_requirements(code: str):
    program = _fetch_program(code.strip().upper())
    if program is None:
        return json_error(f"No program found for code {code!r}.", 404)
    return jsonify(_requirements_json(program))


@bp.route("/api/programs/<code>/requirements/reparse", methods=["POST"])
def reparse_requirements(code: str):
    """On-demand Gemini re-segmentation of one program's completion requirements.

    Cache-first: if a prior reparse already populated per-course detail,
    return it as-is rather than spending another Gemini call (mirrors
    `SearchService.load_requirements`).
    """
    code = code.strip().upper()
    program = _fetch_program(code)
    if program is None:
        return json_error(f"No program found for code {code!r}.", 404)
    if any(g.courses for g in program.completion_requirements):
        body = _program_detail_json(program)
        body["parseReport"] = {"cached": True}
        return jsonify(body)
    if not program.raw_completion_text:
        return jsonify(_program_detail_json(program))

    try:
        result = _grouper().group(program.raw_completion_text)
    except LLMGroupingError as exc:
        # `exc.status_code` distinguishes a server misconfiguration (503, e.g.
        # no GEMINI_API_KEY) from an actual Gemini-side failure (502) -- the
        # frontend surfaces `str(exc)` verbatim, so keep these messages
        # distinct and actionable (see llm_grouper.py's exception hierarchy).
        return json_error(str(exc), getattr(exc, "status_code", 502))

    program = replace(
        program,
        completion_requirements=result.groups,
        total_credits=result.total_credits or program.total_credits,
    )
    get_course_cache().upsert_programs([program], _now_iso())

    body = _program_detail_json(program)
    body["parseReport"] = result.report
    return jsonify(body)


# ------------------------------------------------------------- enrolled programs
def _combination_status(rows: list[ProgramEnrolment]) -> dict:
    """Structural POSt-combination summary from program codes alone.

    Checks the two rules a program *code* alone can decide
    (design/09-uoft-degree-rules.md #1-#2): one-type-per-subject, and whether
    the current set already forms one of the three valid combination shapes
    (1 Specialist / 2 Majors / 1 Major + 2 Minors). This is advisory, not a
    gate on enrolling - it never blocks a POST by itself; see module
    docstring for what's deliberately out of scope (the >=12.0 distinct-
    credits rule).
    """
    parsed = [(row.program_code, _parse_program_code(row.program_code)) for row in rows]

    subject_types: dict[str, set[str]] = {}
    for code, info in parsed:
        if info is None:
            continue
        ptype, subject = info
        if ptype not in _COMBINATION_TYPES:
            continue
        subject_types.setdefault(subject, set()).add(ptype)

    warnings = [
        f"Subject {subject} has more than one program type enrolled "
        f"({', '.join(sorted(types))}); only one is allowed per subject (eff. Sept 2025)."
        for subject, types in sorted(subject_types.items())
        if len(types) > 1
    ]

    counts = Counter(
        info[0] for _, info in parsed if info is not None and info[0] in _COMBINATION_TYPES
    )
    specialists, majors, minors = counts["specialist"], counts["major"], counts["minor"]

    if specialists == 0 and majors == 0 and minors == 0:
        combination_type = "none"
    elif specialists == 1 and majors == 0 and minors == 0:
        combination_type = "specialist"
    elif specialists == 0 and majors == 2 and minors == 0:
        combination_type = "major+major"
    elif specialists == 0 and majors == 1 and minors == 2:
        combination_type = "major+minor+minor"
    else:
        combination_type = "incomplete"

    is_complete_shape = combination_type not in ("none", "incomplete")
    if not is_complete_shape and combination_type != "none":
        warnings.append(
            "Current programs don't yet form a valid combination "
            "(1 Specialist, OR 2 Majors, OR 1 Major + 2 Minors)."
        )

    return {
        "specialistCount": specialists,
        "majorCount": majors,
        "minorCount": minors,
        "combinationType": combination_type,
        "valid": is_complete_shape and not warnings,
        "warnings": warnings,
    }


@bp.route("/api/me/programs", methods=["GET"])
@require_auth
def list_my_programs():
    db = db_session()
    rows = (
        db.query(ProgramEnrolment)
        .filter_by(user_id=current_user().id)
        .order_by(ProgramEnrolment.position, ProgramEnrolment.created_at)
        .all()
    )
    return jsonify(
        {
            "programs": [_enrolment_json(r) for r in rows],
            "combination": _combination_status(rows),
        }
    )


@bp.route("/api/me/programs", methods=["POST"])
@require_auth
def add_my_program():
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip().upper()
    if not code:
        return json_error("code is required.", 422)

    parsed = _parse_program_code(code)
    if parsed is None:
        return json_error(
            f"{code!r} is not a recognized program code (expected AS + type + subject digits, "
            "e.g. ASMAJ1305A).",
            422,
        )
    program_type, subject = parsed

    db = db_session()
    user = current_user()
    existing = db.query(ProgramEnrolment).filter_by(user_id=user.id).all()

    if any(r.program_code == code for r in existing):
        return json_error(f"Already enrolled in {code}.", 409)

    if program_type in _COMBINATION_TYPES:
        for row in existing:
            other = _parse_program_code(row.program_code)
            if (
                other is not None
                and other[1] == subject
                and other[0] in _COMBINATION_TYPES
                and other[0] != program_type
            ):
                return json_error(
                    f"Cannot enrol in a {program_type} for subject {subject}: already enrolled in a "
                    f"{other[0]} ({row.program_code}) for the same subject area - only one program "
                    "type per subject is allowed (eff. Sept 2025).",
                    409,
                )

    title = (data.get("title") or "").strip() or None
    if title is None:
        cached = get_course_cache().get_program(code)
        title = cached.title if cached is not None else None
    start_session = (data.get("startSession") or "").strip() or None

    row = ProgramEnrolment(
        user_id=user.id,
        program_code=code,
        program_title=title,
        start_session=start_session,
        position=len(existing),
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return json_error(f"Already enrolled in {code}.", 409)

    return (
        jsonify(
            {
                "program": _enrolment_json(row),
                "combination": _combination_status([*existing, row]),
            }
        ),
        201,
    )


@bp.route("/api/me/programs/<code>", methods=["DELETE"])
@require_auth
def remove_my_program(code: str):
    db = db_session()
    user = current_user()
    code = code.strip().upper()
    row = db.query(ProgramEnrolment).filter_by(user_id=user.id, program_code=code).first()
    if row is None:
        return json_error(f"Not enrolled in program {code!r}.", 404)
    db.delete(row)
    db.commit()

    remaining = db.query(ProgramEnrolment).filter_by(user_id=user.id).all()
    return jsonify({"ok": True, "combination": _combination_status(remaining)})


@bp.route("/api/me/programs/order", methods=["PUT"])
@require_auth
def reorder_my_programs():
    """Persist "My programs" display order (design/02-user-flows.md: "reorder
    priority"). Body: `{"codes": [...]}` — every enrolled program code, in the
    student's desired order. Rejects a mismatched set (missing/unknown/duplicate
    codes) with 422 rather than silently reordering a subset, since a partial
    write would leave `position` values ambiguous relative to the omitted rows.
    """
    data = request.get_json(silent=True) or {}
    codes = data.get("codes")
    if not isinstance(codes, list) or not all(isinstance(c, str) for c in codes):
        return json_error("codes must be a list of program codes.", 422)
    codes = [c.strip().upper() for c in codes]

    db = db_session()
    user = current_user()
    rows = db.query(ProgramEnrolment).filter_by(user_id=user.id).all()
    by_code = {row.program_code: row for row in rows}

    if len(codes) != len(set(codes)) or set(codes) != set(by_code):
        return json_error("codes must match your enrolled programs exactly, with no duplicates.", 422)

    for index, code in enumerate(codes):
        by_code[code].position = index
    db.commit()

    ordered = sorted(rows, key=lambda r: r.position)
    return jsonify({"programs": [_enrolment_json(r) for r in ordered]})
