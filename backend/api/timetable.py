"""Timetable blueprint: planned-term sections + a conflict-free schedule optimizer.

Two endpoints (design/06-data-model-and-api.md, design/screens/04-plan-and-timetable.md):

- `GET /api/plan/<term>/sections` -- the signed-in user's `PlanItem` rows for one
  TTB session code (`term`, e.g. `"20269"`), each resolved to its live TTB
  section list (LEC/TUT/PRA, seats, meeting times). Backs the Timetable
  builder's CourseTray.
- `POST /api/timetable/optimize` -- given a set of course codes (+ optional
  locked sections + scheduling preferences), search for ranked, conflict-free
  candidate schedules. Backs the Timetable optimizer panel.

Course/section data comes from the shared `SqliteCache` (`backend.extensions
.get_course_cache`) with `TTBClient` as the fill-on-miss source -- never
reimplemented here (docs/conventions.md). A course is looked up by an *exact*,
session-scoped `getPageableCourses` search (`TTBClient.search(session,
division, course_code=<exact code>)`), not a bulk session sync: a plan/optimize
request only ever needs a handful of specific codes, unlike the TUI's keyword
search which has to cache a whole session to filter locally.

Conflict rule (design/06): two sections conflict if any of their meeting times
share a `day` and their `[start_min, end_min)` intervals overlap.

Slot model for the optimizer: each requested course contributes one "slot" per
distinct `teach_method` present in its sections (e.g. one LEC slot + one TUT
slot) -- TTB doesn't expose an explicit "this teach method is required"
flag, so requiring exactly one section per teach-method group actually offered
is the documented simplification (matches how students actually register: one
lecture + one tutorial/practical if offered).
"""

from __future__ import annotations

import datetime as dt
import re
from typing import Any

from flask import Blueprint, jsonify, request

from backend.api import current_user, db_session, json_error, require_auth
from backend.data_sources.models import Course, Instructor, MeetingTime, Section
from backend.data_sources.timetable.client import TTBClient
from backend.extensions import get_course_cache
from backend.models_db import Plan, PlanItem

bp = Blueprint("timetable", __name__, url_prefix="/api")

_TTB_DIVISION = "ARTSC"  # AGENTS.md: division starts scoped to Arts & Science
_SESSION_RE = re.compile(r"^\d{5}$")
_HHMM_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")

_MAX_COURSES = 16  # bounds request size / optimizer combinatorics
_MAX_RESULTS_DEFAULT = 5
_MAX_RESULTS_CAP = 10
_MAX_CANDIDATE_POOL = 200  # complete assignments collected before ranking
_MAX_SEARCH_NODES = 50_000  # backtracking node budget (safety valve)


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


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


def _course_dict(course: Course) -> dict[str, Any]:
    return {
        "code": course.code,
        "title": course.title,
        "sectionCode": course.section_code,
        "credit": course.credit,
        "campus": course.campus,
        "sections": [_section_dict(s) for s in course.sections],
    }


# ------------------------------------------------------------------- lookup
def _lookup_courses(
    session_code: str, codes: list[str]
) -> tuple[dict[str, Course], list[str]]:
    """Resolve `codes` to `Course` objects for `session_code`.

    Cache-first (exact code match within the session), TTB on miss (exact
    session-scoped search), caching the result for next time. Returns
    `(found_by_code, missing_codes)` -- a code TTB has no listing for in this
    session is not an error (docs/conventions.md: empty result, not an
    exception), just reported back for the caller to show as "not offered".
    """
    cache = get_course_cache()
    ttb = TTBClient()
    found: dict[str, Course] = {}
    missing: list[str] = []
    fetched_at = _now_iso()

    for code in codes:
        if code in found:
            continue
        cached = [c for c in cache.search_courses(session_code, code, limit=5) if c.code == code]
        if cached:
            found[code] = cached[0]
            continue
        results = ttb.search(session_code, division=_TTB_DIVISION, course_code=code)
        exact = [c for c in results if c.code == code]
        if exact:
            course = exact[0]
            found[code] = course
            cache.upsert_courses(session_code, [course], fetched_at)
        else:
            missing.append(code)
    return found, missing


# --------------------------------------------------------------- validation
def _validate_term(term: str) -> str | None:
    """None if valid, else an error message."""
    if not _SESSION_RE.match(term or ""):
        return "term must be a 5-digit TTB session code, e.g. '20269' (see /api/sessions)."
    return None


def _parse_hhmm(value: Any, field: str) -> int:
    """Parse an "HH:MM" string to minutes-since-midnight; raises ValueError."""
    if not isinstance(value, str) or not _HHMM_RE.match(value):
        raise ValueError(f"{field} must be an \"HH:MM\" 24-hour time string.")
    hh, mm = value.split(":")
    return int(hh) * 60 + int(mm)


def _parse_preferences(raw: Any) -> dict[str, Any]:
    """Parse+validate the optional `preferences` object; raises ValueError."""
    raw = raw or {}
    if not isinstance(raw, dict):
        raise ValueError("preferences must be an object.")

    avoid_days = raw.get("avoidDays") or []
    if not isinstance(avoid_days, list) or not all(
        isinstance(d, int) and 1 <= d <= 7 for d in avoid_days
    ):
        raise ValueError("preferences.avoidDays must be a list of ISO weekday ints (1=Mon..7=Sun).")

    earliest = raw.get("earliestStart")
    latest = raw.get("latestEnd")
    prefs = {
        "avoid_days": set(avoid_days),
        "earliest_start": _parse_hhmm(earliest, "preferences.earliestStart") if earliest else None,
        "latest_end": _parse_hhmm(latest, "preferences.latestEnd") if latest else None,
        "minimize_days_on_campus": bool(raw.get("minimizeDaysOnCampus", True)),
        "allow_full": bool(raw.get("allowFull", False)),
    }
    return prefs


def _parse_locked(raw: Any, codes: list[str]) -> dict[str, dict[str, str]]:
    """`{courseCode: {teachMethod: sectionName}}`; raises ValueError on bad shape/refs."""
    raw = raw or {}
    if not isinstance(raw, dict):
        raise ValueError("locked must be an object keyed by course code.")
    for code, by_method in raw.items():
        if code not in codes:
            raise ValueError(f"locked course {code!r} must also appear in courses.")
        if not isinstance(by_method, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in by_method.items()
        ):
            raise ValueError(f"locked[{code!r}] must be an object of teachMethod -> sectionName.")
    return raw


# ---------------------------------------------------------------- conflicts
def _overlaps(a: MeetingTime, b: MeetingTime) -> bool:
    return a.day == b.day and a.start_min < b.end_min and b.start_min < a.end_min


def _conflicts(existing: list[MeetingTime], candidate: list[MeetingTime]) -> bool:
    return any(_overlaps(a, b) for a in existing for b in candidate)


# -------------------------------------------------------------------- slots
_Slot = tuple[str, str, list[Section]]  # (course_code, teach_method, candidate sections)


def _build_slots(
    found: dict[str, Course], locked: dict[str, dict[str, str]], allow_full: bool
) -> tuple[list[_Slot], list[dict[str, str]]]:
    """One slot per (course, teach_method); returns `(slots, blocked)`.

    `blocked` entries describe a course/teach-method with zero eligible
    candidates (e.g. every section full and `allowFull` is false) -- not a
    client error, just an unschedulable request the caller should relax.
    """
    slots: list[_Slot] = []
    blocked: list[dict[str, str]] = []

    for code, course in found.items():
        by_method: dict[str, list[Section]] = {}
        for section in course.sections:
            by_method.setdefault(section.teach_method, []).append(section)

        for method, sections in sorted(by_method.items()):
            locked_name = (locked.get(code) or {}).get(method)
            if locked_name is not None:
                candidates = [s for s in sections if s.name == locked_name]
                if not candidates:
                    raise ValueError(
                        f"locked section {locked_name!r} not found for {code} ({method})."
                    )
            else:
                candidates = [s for s in sections if allow_full or not s.is_full]
                candidates.sort(key=lambda s: s.name)

            if not candidates:
                blocked.append({"courseCode": code, "teachMethod": method})
            else:
                slots.append((code, method, candidates))

    return slots, blocked


# ------------------------------------------------------------- backtracking
def _search_schedules(slots: list[_Slot]) -> tuple[list[list[Section]], list[_Slot]]:
    """All conflict-free complete assignments, up to `_MAX_CANDIDATE_POOL`.

    Slots are searched in fewest-candidates-first order (classic CSP
    ordering: fail fast), with a node budget (`_MAX_SEARCH_NODES`) as a
    worst-case safety valve -- this is best-effort search, not exhaustive
    enumeration, for pathological inputs. Returns `(assignments, ordered_slots)`
    -- each assignment is a list of `Section`s positionally aligned with
    `ordered_slots` (not the caller's original `slots` order).
    """
    ordered = sorted(slots, key=lambda slot: len(slot[2]))
    results: list[list[Section]] = []
    assignment: list[Section] = []
    meeting_acc: list[MeetingTime] = []
    nodes = 0

    def backtrack(i: int) -> bool:
        """Returns True to stop the whole search (pool full / budget spent)."""
        nonlocal nodes
        if len(results) >= _MAX_CANDIDATE_POOL:
            return True
        nodes += 1
        if nodes > _MAX_SEARCH_NODES:
            return True
        if i == len(ordered):
            results.append(list(assignment))
            return False
        for section in ordered[i][2]:
            if _conflicts(meeting_acc, section.meeting_times):
                continue
            assignment.append(section)
            meeting_acc.extend(section.meeting_times)
            stop = backtrack(i + 1)
            del meeting_acc[len(meeting_acc) - len(section.meeting_times):]
            assignment.pop()
            if stop:
                return True
        return False

    if ordered:
        backtrack(0)

    return results, ordered


def _score_assignment(sections: list[Section], prefs: dict[str, Any]) -> dict[str, Any]:
    """Heuristic 0..100 score: lower days-on-campus/gaps/preference violations score higher."""
    meetings = [mt for s in sections for mt in s.meeting_times]
    days = sorted({mt.day for mt in meetings})
    days_on_campus = len(days)

    total_gap = 0
    for day in days:
        day_meetings = sorted((mt for mt in meetings if mt.day == day), key=lambda m: m.start_min)
        for prev, nxt in zip(day_meetings, day_meetings[1:]):
            gap = nxt.start_min - prev.end_min
            if gap > 0:
                total_gap += gap

    avoid_hits = sum(1 for mt in meetings if mt.day in prefs["avoid_days"])
    earliest, latest = prefs["earliest_start"], prefs["latest_end"]
    out_of_window = 0
    for mt in meetings:
        if earliest is not None and mt.start_min < earliest:
            out_of_window += 1
        if latest is not None and mt.end_min > latest:
            out_of_window += 1

    score = 100.0
    if prefs["minimize_days_on_campus"]:
        score -= days_on_campus * 4
    score -= total_gap * 0.05
    score -= avoid_hits * 12
    score -= out_of_window * 8
    score = max(0.0, round(score, 1))

    return {"score": score, "daysOnCampus": days_on_campus, "totalGapMinutes": total_gap}


# -------------------------------------------------------------------- views
@bp.route("/plan/<term>/sections", methods=["GET"])
@require_auth
def plan_sections(term: str):
    error = _validate_term(term)
    if error:
        return json_error(error, 422)

    plan_id_param = request.args.get("planId", type=int)
    db = db_session()
    user = current_user()

    query = db.query(Plan).filter_by(user_id=user.id)
    if plan_id_param is not None:
        plan = query.filter_by(id=plan_id_param).first()
        if plan is None:
            return json_error("Plan not found.", 404)
    else:
        plan = query.filter_by(is_primary=True).first() or query.first()
        if plan is None:
            return jsonify({"term": term, "courses": [], "missing": []})

    items = (
        db.query(PlanItem)
        .filter_by(plan_id=plan.id, term_session=term)
        .order_by(PlanItem.position)
        .all()
    )
    if not items:
        return jsonify({"term": term, "courses": [], "missing": []})

    codes = list(dict.fromkeys(item.course_code for item in items))  # de-dup, preserve order
    found, missing = _lookup_courses(term, codes)

    return jsonify(
        {
            "term": term,
            "courses": [_course_dict(found[code]) for code in codes if code in found],
            "missing": missing,
        }
    )


@bp.route("/timetable/optimize", methods=["POST"])
@require_auth
def optimize():
    data = request.get_json(silent=True) or {}

    term = data.get("term")
    error = _validate_term(term or "")
    if error:
        return json_error(error, 422)

    codes = data.get("courses")
    if not isinstance(codes, list) or not codes or not all(isinstance(c, str) and c for c in codes):
        return json_error("courses must be a non-empty list of course code strings.", 422)
    codes = list(dict.fromkeys(codes))  # de-dup, preserve order
    if len(codes) > _MAX_COURSES:
        return json_error(f"courses is limited to {_MAX_COURSES} at a time.", 422)

    try:
        locked = _parse_locked(data.get("locked"), codes)
        prefs = _parse_preferences(data.get("preferences"))
    except ValueError as exc:
        return json_error(str(exc), 422)

    max_results = data.get("maxResults", _MAX_RESULTS_DEFAULT)
    if not isinstance(max_results, int) or not (1 <= max_results <= _MAX_RESULTS_CAP):
        return json_error(f"maxResults must be an integer from 1 to {_MAX_RESULTS_CAP}.", 422)

    found, missing = _lookup_courses(term, codes)

    try:
        slots, blocked = _build_slots(found, locked, prefs["allow_full"])
    except ValueError as exc:
        return json_error(str(exc), 422)

    candidates: list[dict[str, Any]] = []
    if not blocked and slots:
        assignments, ordered_slots = _search_schedules(slots)
        for assignment in assignments:
            metrics = _score_assignment(assignment, prefs)
            sections_out = [
                {"courseCode": code, "teachMethod": method, "section": _section_dict(section)}
                for (code, method, _), section in zip(ordered_slots, assignment)
            ]
            candidates.append({**metrics, "sections": sections_out})

        candidates.sort(key=lambda c: (-c["score"], c["daysOnCampus"], c["totalGapMinutes"]))
        candidates = candidates[:max_results]
        for rank, candidate in enumerate(candidates, start=1):
            candidate["rank"] = rank
            # stable field order for readability
            reordered = {
                "rank": candidate["rank"],
                "score": candidate["score"],
                "daysOnCampus": candidate["daysOnCampus"],
                "totalGapMinutes": candidate["totalGapMinutes"],
                "sections": candidate["sections"],
            }
            candidate.clear()
            candidate.update(reordered)

    return jsonify(
        {
            "term": term,
            "feasible": len(candidates) > 0,
            "missingCourses": missing,
            "blockedCourses": blocked,
            "candidates": candidates,
        }
    )
