"""Client for the UofT Timetable Builder (TTB) undocumented public JSON API.

See backend/docs/TTB_API_REFERENCE.md for the full, verified contract this
module implements. Two things make this client non-trivial:

- TTB caps the actual page size at ~20 regardless of the requested
  `pageSize`, so `search()` paginates by watching the running count of
  courses collected against `payload.pageableCourse.total`, not by trusting
  the requested page size.
- A search with zero matches returns HTTP 404 with `payload: null` (see
  `backend/data_sources/http.py::get_json`/`post_json`, which surface that
  as `None`). This client treats that as "empty result", never an error.

All I/O goes through `backend.data_sources.http`; this module never talks to
`requests` directly. `normalize_course` (and its private helpers) are pure
functions with no I/O, so they are unit-testable against the saved fixture
with no network - see backend/tests/test_timetable.py.
"""

from __future__ import annotations

from typing import Any

from backend.data_sources.http import get_json, post_json, strip_html, throttle
from backend.data_sources.models import Course, Instructor, MeetingTime, Section

BASE_URL = "https://api.easi.utoronto.ca/ttb"

# TTB ignores a larger requested pageSize and returns ~20 rows per page
# anyway; this is just the value we request, not something we rely on.
_REQUESTED_PAGE_SIZE = 20
# Safety cap on pagination loops so a misbehaving/unexpected `total` value
# (e.g. 0 with non-empty pages) can never spin forever.
_MAX_PAGES = 500


def _normalize_instructor(raw: dict[str, Any]) -> Instructor:
    return Instructor(first=raw.get("firstName") or "", last=raw.get("lastName") or "")


def _normalize_meeting_time(raw: dict[str, Any]) -> MeetingTime:
    start = raw.get("start") or {}
    end = raw.get("end") or {}
    building = raw.get("building") or {}
    return MeetingTime.from_millis(
        day=int(start.get("day") or 0),
        start_millis=int(start.get("millisofday") or 0),
        end_millis=int(end.get("millisofday") or 0),
        building=building.get("buildingCode") or "",
        session=raw.get("sessionCode") or "",
    )


def _normalize_section(raw: dict[str, Any]) -> Section:
    return Section(
        name=raw.get("name") or "",
        teach_method=raw.get("teachMethod") or "",
        section_number=raw.get("sectionNumber") or "",
        current_enrol=int(raw.get("currentEnrolment") or 0),
        max_enrol=int(raw.get("maxEnrolment") or 0),
        waitlist=int(raw.get("currentWaitlist") or 0),
        instructors=[_normalize_instructor(i) for i in raw.get("instructors") or []],
        meeting_times=[_normalize_meeting_time(mt) for mt in raw.get("meetingTimes") or []],
        delivery_modes=[dm.get("mode") or "" for dm in raw.get("deliveryModes") or []],
    )


def normalize_course(raw: dict[str, Any]) -> Course:
    """Map one raw TTB course object into the shared `Course` model.

    `raw` is one entry of `payload.pageableCourse.courses[]` from either
    `getPageableCourses` or `getCoursesByCodeAndSectionCode`. Pure function,
    no I/O - see TTB_API_REFERENCE.md for the raw field-by-field shape.
    """
    cm = raw.get("cmCourseInfo") or {}
    return Course(
        code=raw.get("code") or "",
        title=raw.get("name") or "",
        section_code=raw.get("sectionCode") or "",
        credit=float(raw.get("maxCredit") or 0.0),
        campus=raw.get("campus") or "",
        description=strip_html(cm.get("description")),
        prerequisites=strip_html(cm.get("prerequisitesText")),
        corequisites=strip_html(cm.get("corequisitesText")),
        exclusions=strip_html(cm.get("exclusionsText")),
        breadth=list(cm.get("breadthRequirements") or []),
        distribution=list(cm.get("distributionRequirements") or []),
        sections=[_normalize_section(s) for s in raw.get("sections") or []],
    )


def _build_search_payload(
    course_code: str,
    sessions: list[str],
    divisions: list[str],
    page: int,
    page_size: int,
) -> dict[str, Any]:
    """Build the `getPageableCourses` request body (matches the TTB Angular client)."""
    return {
        "courseCodeAndTitleProps": {
            "courseCode": course_code,
            "courseTitle": "",
            "courseSectionCode": "",
            "searchCourseDescription": False,
        },
        "departmentProps": [],
        "campuses": [],
        "requirementProps": [],
        "instructorProps": [],
        "courseLevels": [],
        "deliveryModes": [],
        "dayPreferences": [],
        "timePreferences": [],
        "creditWeights": [],
        "sessions": sessions,
        "divisions": divisions,
        "availableSpace": False,
        "waitListable": False,
        "page": page,
        "pageSize": page_size,
        "direction": "asc",
    }


class TTBClient:
    """Thin client over the Timetable Builder API.

    Returns only the shared, source-agnostic models from
    `backend/data_sources/models.py` - callers never see raw TTB JSON.
    """

    def __init__(self, base_url: str = BASE_URL) -> None:
        self._base_url = base_url.rstrip("/")

    def get_reference_data(self) -> dict[str, Any]:
        """GET /reference-data -> the `payload` dict driving TTB's dropdowns
        (currentSessions, divisions, campuses, requirements, courseLevels,
        deliveryModes). Returns `{}` if TTB has nothing to say (404)."""
        response = get_json(f"{self._base_url}/reference-data")
        if response is None:
            return {}
        return response.get("payload") or {}

    def current_sessions(self) -> list[str]:
        """Usable full-session codes from `/reference-data`.

        `currentSessions[]` mixes UI group-headers (`header: true`) with
        selectable options; only numeric, non-header `value`s are real
        session codes (see TTB_API_REFERENCE.md#session-codes). Never
        hard-code these - always fetch them.
        """
        payload = self.get_reference_data()
        sessions = payload.get("currentSessions") or []
        return [
            str(entry["value"])
            for entry in sessions
            if not entry.get("header") and str(entry.get("value", "")).isdigit()
        ]

    def search(self, session: str, division: str = "ARTSC", course_code: str = "") -> list[Course]:
        """POST /getPageableCourses, paginated to completion.

        A no-match search returns HTTP 404 (surfaced by `post_json` as
        `None`), which is treated as an empty result, not an error.

        Paces successive page requests with `throttle()` (AGENTS.md:
        "throttle bulk pulls") - a division-wide pull (`course_code=""`, as
        `refresh_cache.py` and the courses API's session-sync both do) can
        run to 100+ pages.
        """
        courses: list[Course] = []
        total: int | None = None
        page = 1
        while page <= _MAX_PAGES:
            body = _build_search_payload(
                course_code=course_code,
                sessions=[session],
                divisions=[division],
                page=page,
                page_size=_REQUESTED_PAGE_SIZE,
            )
            response = post_json(f"{self._base_url}/getPageableCourses", body)
            if response is None:  # TTB's "no results" 404 quirk
                break
            payload = response.get("payload") or {}
            pageable = payload.get("pageableCourse") or {}
            raw_courses = pageable.get("courses") or []
            if not raw_courses:
                break
            if total is None:
                total = pageable.get("total", len(raw_courses))
            courses.extend(normalize_course(raw) for raw in raw_courses)
            if total is not None and len(courses) >= total:
                break
            throttle()
            page += 1
        return courses

    def get_course(self, code: str) -> list[Course]:
        """GET /getCoursesByCodeAndSectionCode/<code> -> all term offerings.

        Without a session filter this endpoint may return multiple term
        offerings (F/S/Y) for the same course code.
        """
        response = get_json(f"{self._base_url}/getCoursesByCodeAndSectionCode/{code}")
        if response is None:
            return []
        payload = response.get("payload") or {}
        pageable = payload.get("pageableCourse") or {}
        raw_courses = pageable.get("courses") or []
        return [normalize_course(raw) for raw in raw_courses]
