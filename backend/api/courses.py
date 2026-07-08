"""Courses blueprint: sessions, catalog search, and course detail.

Three public (no-auth) endpoints, matching `design/06-data-model-and-api.md`
and `design/screens/03-programs-and-courses.md`:

- `GET /api/sessions` -- the usable TTB session codes right now (from
  `/reference-data`), decoded into `{code, term, termName, year, label}` plus
  a `defaultSession` (the current Fall session, matching
  `backend.tui.service.SearchService.session`'s "prefer Fall" default).
- `GET /api/courses` -- cache-backed, code-prefix-ranked keyword search over
  one synced TTB session (`SqliteCache.search_courses`), with `level`/
  `breadth`/`term`/`hasSeats` filters and paging. TTB has no server-side
  keyword search (`backend/docs/TTB_API_REFERENCE.md`), so the first request
  for a session pulls the whole ARTSC session into the cache once -- this is
  the same one-time bulk sync `backend.tui.service.SearchService.
  _ensure_courses_synced` does; it is *not* reimplemented by importing the
  TUI module (`backend/api` doesn't depend on `backend/tui`), just mirrored
  here at the same cache/client layer.
- `GET /api/courses/:code` -- always-live catalog + section detail. Unlike
  the list endpoint, this deliberately bypasses the cache: seat counts need
  to be current, and `GET /getCoursesByCodeAndSectionCode/<code>`
  (`TTBClient.get_course`) is a single cheap call, not a bulk pull. A code
  can have more than one live TTB entry (one per term offering -- e.g. a
  half course taught both Fall and Winter has separate `sectionCode` "F"
  and "S" entries), so the response groups sections per `offerings[]` entry
  rather than flattening them, letting the UI show "Fall ● Winter ○" and a
  per-term section list (design/screens/03 course-detail mock). If TTB has
  no live offering at all (not scheduled this cycle), falls back to the
  Academic Calendar (`CalendarCourseClient`) for catalog-only fields with no
  sections -- still real, just not live-schedulable.
"""

from __future__ import annotations

import datetime
import re
from typing import Any

from flask import Blueprint, jsonify, request

from backend.api import json_error
from backend.data_sources.calendar_courses.client import CalendarCourseClient
from backend.data_sources.models import Course, Instructor, MeetingTime, Section
from backend.data_sources.timetable.client import TTBClient
from backend.extensions import get_course_cache

bp = Blueprint("courses", __name__, url_prefix="/api")

_TTB_DIVISION = "ARTSC"  # AGENTS.md: division starts scoped to Arts & Science
_FALL_TERM_DIGIT = "9"  # matches backend/tui/service.py's SearchService default

_SESSION_RE = re.compile(r"^\d{5}$")
_LEVEL_CODE_RE = re.compile(r"^[A-Z]{3,7}(\d)\d{2}[HY]\d$")

_TERM_BY_DIGIT = {"1": ("S", "Winter"), "5": ("Y", "Summer"), "9": ("F", "Fall")}
_VALID_TERM_LETTERS = {"F", "S", "Y"}
_VALID_BREADTH = {"1", "2", "3", "4", "5"}

_DEFAULT_PAGE_SIZE = 20
_MAX_PAGE_SIZE = 100
# Generous enough to hold a full ARTSC session (~1,600 courses per
# backend/tui/service.py) so filtering/paging below sees every match, not
# just the first page of the underlying cache query.
_SEARCH_FETCH_LIMIT = 5000


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


# ------------------------------------------------------------- serialization
def _instructor_dict(i: Instructor) -> dict[str, Any]:
    return {"first": i.first, "last": i.last}


def _meeting_time_dict(mt: MeetingTime) -> dict[str, Any]:
    return {
        "day": mt.day,
        "startMin": mt.start_min,
        "endMin": mt.end_min,
        "building": mt.building,
        "session": mt.session,
    }


def _section_dict(s: Section) -> dict[str, Any]:
    return {
        "name": s.name,
        "teachMethod": s.teach_method,
        "sectionNumber": s.section_number,
        "currentEnrol": s.current_enrol,
        "maxEnrol": s.max_enrol,
        "waitlist": s.waitlist,
        "isFull": s.is_full,
        "instructors": [_instructor_dict(i) for i in s.instructors],
        "meetingTimes": [_meeting_time_dict(m) for m in s.meeting_times],
        "deliveryModes": list(s.delivery_modes),
    }


def _course_summary_dict(course: Course) -> dict[str, Any]:
    """Row shape for `/api/courses` search results (design/screens/03 CourseCard)."""
    has_seats = any(not s.is_full for s in course.sections) if course.sections else False
    return {
        "code": course.code,
        "title": course.title,
        "sectionCode": course.section_code,
        "credit": course.credit,
        "campus": course.campus,
        "breadth": list(course.breadth),
        "sectionCount": len(course.sections),
        "hasSeats": has_seats,
    }


# ------------------------------------------------------------------- filters
def _course_level(code: str) -> int | None:
    """`100`/`200`/`300`/`400`/`500` from a course code's first digit, e.g.
    `POL208H1` -> `200`; `None` if `code` doesn't match the expected shape
    (matches TTB's `courseLevels` dropdown: `100/A .. 400/D, 5+`)."""
    match = _LEVEL_CODE_RE.match(code.strip().upper())
    if match is None:
        return None
    digit = int(match.group(1))
    return min(digit, 5) * 100


def _matches_level(course: Course, level: str) -> bool:
    return _course_level(course.code) == int(level)


def _matches_breadth(course: Course, breadth: str) -> bool:
    marker = f"({breadth})"
    return any(marker in b for b in course.breadth)


def _matches_term(course: Course, term: str) -> bool:
    return course.section_code.strip().upper() == term


def _matches_has_seats(course: Course) -> bool:
    return bool(course.sections) and any(not s.is_full for s in course.sections)


# ---------------------------------------------------------------- sessions
def _decode_session(code: str) -> dict[str, Any] | None:
    """`{code, term, termName, year, label}` for a usable TTB session code,
    or `None` if `code` isn't one of the plain-digit codes `TTBClient.
    current_sessions` returns (see `_TERM_BY_DIGIT`; hyphenated combined
    Fall-Winter codes never reach here -- `current_sessions` already filters
    to all-digit values)."""
    if not _SESSION_RE.match(code):
        return None
    digit = code[4]
    term_info = _TERM_BY_DIGIT.get(digit)
    if term_info is None:
        return None
    term, term_name = term_info
    year = int(code[:4])
    return {
        "code": code,
        "term": term,
        "termName": term_name,
        "year": year,
        "label": f"{term_name} {year}",
    }


def _default_session(sessions: list[str]) -> str | None:
    """Prefer the current Fall session; else the first usable session; else
    `None` (matches `SearchService.session`'s default)."""
    preferred = [s for s in sessions if s.endswith(_FALL_TERM_DIGIT)]
    if preferred:
        return preferred[0]
    return sessions[0] if sessions else None


@bp.route("/sessions", methods=["GET"])
def list_sessions():
    sessions = TTBClient().current_sessions()
    decoded = [d for s in sessions if (d := _decode_session(s)) is not None]
    decoded.sort(key=lambda d: (d["year"], d["term"] != "F", d["term"]))
    return jsonify({"sessions": decoded, "defaultSession": _default_session(sessions)})


# ------------------------------------------------------------------ sync
def _ensure_session_synced(session: str) -> None:
    """One-time bulk pull of `session` into the shared cache.

    Mirrors `backend.tui.service.SearchService._ensure_courses_synced`
    exactly (cache-first, sync-once) -- TTB has no server-side keyword
    search, so a whole-session pull is the only way to support prefix/
    title search (docs/conventions.md, backend/docs/TTB_API_REFERENCE.md).
    """
    cache = get_course_cache()
    if cache.course_count(session) > 0:
        return
    courses = TTBClient().search(session, division=_TTB_DIVISION, course_code="")
    cache.upsert_courses(session, courses, _now_iso())
    cache.set_meta(f"synced:courses:{session}", _now_iso())


# ------------------------------------------------------------------- search
@bp.route("/courses", methods=["GET"])
def search_courses():
    session = (request.args.get("session") or "").strip()
    if session and not _SESSION_RE.match(session):
        return json_error("session must be a 5-digit TTB session code, e.g. '20269'.", 422)
    if not session:
        sessions = TTBClient().current_sessions()
        session = _default_session(sessions)
        if session is None:
            return json_error("Timetable Builder has no current sessions available right now.", 502)

    q = (request.args.get("q") or "").strip()

    level = (request.args.get("level") or "").strip()
    if level and level not in {"100", "200", "300", "400", "500"}:
        return json_error("level must be one of 100, 200, 300, 400, 500.", 422)

    breadth = (request.args.get("breadth") or "").strip()
    if breadth and breadth not in _VALID_BREADTH:
        return json_error("breadth must be one of 1, 2, 3, 4, 5.", 422)

    term = (request.args.get("term") or "").strip().upper()
    if term and term not in _VALID_TERM_LETTERS:
        return json_error("term must be one of F, S, Y.", 422)

    has_seats_raw = (request.args.get("hasSeats") or "").strip().lower()
    has_seats = has_seats_raw in {"1", "true", "yes"}

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

    try:
        _ensure_session_synced(session)
    except Exception as exc:  # noqa: BLE001 - degrade to a clean JSON error
        return json_error(f"Course sync failed: {exc}", 502)

    cache = get_course_cache()
    results = cache.search_courses(session, q, limit=_SEARCH_FETCH_LIMIT)

    if level:
        results = [c for c in results if _matches_level(c, level)]
    if breadth:
        results = [c for c in results if _matches_breadth(c, breadth)]
    if term:
        results = [c for c in results if _matches_term(c, term)]
    if has_seats:
        results = [c for c in results if _matches_has_seats(c)]

    total = len(results)
    start = (page - 1) * page_size
    page_items = results[start:start + page_size]

    return jsonify(
        {
            "session": session,
            "courses": [_course_summary_dict(c) for c in page_items],
            "page": page,
            "pageSize": page_size,
            "total": total,
            "totalPages": (total + page_size - 1) // page_size if total else 0,
        }
    )


# ------------------------------------------------------------------- detail
def _offering_dict(course: Course) -> dict[str, Any]:
    return {"sectionCode": course.section_code, "sections": [_section_dict(s) for s in course.sections]}


def _detail_dict(courses: list[Course], source: str) -> dict[str, Any]:
    """Merge same-code TTB/Calendar entries into one detail body.

    Catalog fields (title/description/prereqs/...) come from the first
    entry -- they're expected to be identical across a code's term
    offerings; each offering's live sections stay grouped separately (see
    module docstring).
    """
    base = courses[0]
    return {
        "code": base.code,
        "title": base.title,
        "credit": base.credit,
        "campus": base.campus,
        "description": base.description,
        "prerequisites": base.prerequisites,
        "corequisites": base.corequisites,
        "exclusions": base.exclusions,
        "breadth": list(base.breadth),
        "distribution": list(base.distribution),
        "terms": [c.section_code for c in courses if c.section_code],
        "offerings": [_offering_dict(c) for c in courses],
        "source": source,
    }


@bp.route("/courses/<code>", methods=["GET"])
def get_course_detail(code: str):
    code = code.strip().upper()
    if not code:
        return json_error("code is required.", 422)

    try:
        ttb_courses = TTBClient().get_course(code)
    except Exception as exc:  # noqa: BLE001 - degrade to a clean JSON error
        return json_error(f"Course lookup failed: {exc}", 502)

    if ttb_courses:
        return jsonify(_detail_dict(ttb_courses, source="ttb"))

    try:
        calendar_courses = [c for c in CalendarCourseClient().search(code) if c.code == code]
    except Exception as exc:  # noqa: BLE001 - degrade to a clean JSON error
        return json_error(f"Course lookup failed: {exc}", 502)

    if calendar_courses:
        return jsonify(_detail_dict(calendar_courses, source="calendar"))

    return json_error(f"No course found for code {code!r}.", 404)
