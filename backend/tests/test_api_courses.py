"""Exercises the courses blueprint end-to-end against an isolated in-memory
course cache, with `TTBClient`/`CalendarCourseClient` monkeypatched to fixture
data so nothing touches the network (docs/conventions.md: unit tests must not
hit the network) -- same pattern as `backend/tests/test_api_timetable.py` and
`backend/tests/test_api_programs.py`.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest  # noqa: E402

import backend.api.courses as courses_module  # noqa: E402
from backend.app import create_app  # noqa: E402
from backend.config_app import Config  # noqa: E402
from backend.data_sources.cache import SqliteCache  # noqa: E402
from backend.data_sources.models import Course, Instructor, MeetingTime, Section  # noqa: E402

FALL = "20269"
WINTER = "20271"


# --------------------------------------------------------------------- fixtures
def _section(name, teach_method, day, start_min, end_min, current=5, max_=30, waitlist=0):
    return Section(
        name=name,
        teach_method=teach_method,
        section_number=name[3:],
        current_enrol=current,
        max_enrol=max_,
        waitlist=waitlist,
        instructors=[Instructor(first="A", last="Prof")],
        meeting_times=[
            MeetingTime(day=day, start_min=start_min, end_min=end_min, building="XX", session=FALL)
        ],
        delivery_modes=["in-person"],
    )


def _course(code, title, section_code="F", credit=0.5, breadth=None, sections=None):
    return Course(
        code=code,
        title=title,
        section_code=section_code,
        credit=credit,
        campus="St. George",
        description="A course.",
        prerequisites="",
        corequisites="",
        exclusions="",
        breadth=breadth or [],
        distribution=[],
        sections=sections if sections is not None else [],
    )


_FALL_SESSION_COURSES = [
    _course(
        "POL208H1",
        "Introduction to International Relations",
        breadth=["Society and its Institutions (3)"],
        sections=[
            _section("LEC0101", "LEC", day=2, start_min=1080, end_min=1200, current=162, max_=185),
            _section("TUT0101", "TUT", day=3, start_min=540, end_min=600, current=19, max_=40),
        ],
    ),
    _course(
        "POL300H1",
        "Advanced Politics",
        breadth=["Society and its Institutions (3)"],
        sections=[_section("LEC0101", "LEC", day=1, start_min=600, end_min=660, current=30, max_=30)],
    ),
    _course(
        "AAA100H1",
        "Intro to AAA",
        breadth=["The Physical and Mathematical Universes (5)"],
        sections=[_section("LEC0101", "LEC", day=1, start_min=600, end_min=660, current=5, max_=30)],
    ),
]

# POL208H1 also offered in Winter -- used for the multi-offering detail test.
_POL208_WINTER = _course(
    "POL208H1",
    "Introduction to International Relations",
    section_code="S",
    breadth=["Society and its Institutions (3)"],
    sections=[_section("LEC5101", "LEC", day=4, start_min=600, end_min=660, current=10, max_=50)],
)


class _FakeTTBClient:
    """Stands in for `TTBClient`."""

    _REFERENCE_SESSIONS = [
        {"value": "header-2026", "header": True},
        {"value": "20265", "header": False},  # Summer
        {"value": FALL, "header": False},  # Fall
        {"value": WINTER, "header": False},  # Winter
        {"value": "20269-20271", "header": False},  # combined -- not all-digit, excluded
    ]

    def __init__(self, base_url: str = "") -> None:
        pass

    def current_sessions(self) -> list[str]:
        return [
            str(e["value"])
            for e in self._REFERENCE_SESSIONS
            if not e["header"] and str(e["value"]).isdigit()
        ]

    def search(
        self,
        session,
        division="ARTSC",
        course_code="",
        start_page=1,
        max_pages=None,
        deadline=None,
        stats=None,
    ):
        assert division == "ARTSC"
        result = list(_FALL_SESSION_COURSES) if session == FALL else []
        if stats is not None:
            # This fake never needs more than one bounded call to finish, so
            # every call reports a natural completion -- matching real
            # `TTBClient.search`'s `stats["complete"]` contract closely enough
            # for `backend/api/courses.py`'s sync-once behaviour to hold.
            stats["total"] = len(result)
            stats["complete"] = True
        return result

    def get_course(self, code):
        if code == "POL208H1":
            fall = next(c for c in _FALL_SESSION_COURSES if c.code == "POL208H1")
            return [fall, _POL208_WINTER]
        if code == "POL300H1":
            return [c for c in _FALL_SESSION_COURSES if c.code == "POL300H1"]
        return []


class _FakeCalendarClient:
    def search(self, keyword, max_pages=5):
        if keyword == "CAL100H1":
            return [_course("CAL100H1", "Calendar-only Course", section_code="")]
        return []


class _BoomTTBClient:
    """Fails the test if constructed - proves the code path never hits the network."""

    def __init__(self, *_a: Any, **_k: Any) -> None:
        raise AssertionError("TTBClient must not be constructed here")


class _TestConfig(Config):
    def __init__(self) -> None:
        super().__init__()
        self.SQLALCHEMY_DATABASE_URI = "sqlite://"
        self.IS_SQLITE_FALLBACK = True
        self.TESTING = True
        self.SECRET_KEY = "test-secret-key"
        self.DATA_KEY_PEPPER = "test-pepper"
        self.SESSION_COOKIE_SECURE = False


@pytest.fixture()
def cache() -> SqliteCache:
    return SqliteCache(":memory:")


@pytest.fixture()
def client(monkeypatch: Any, cache: SqliteCache):
    monkeypatch.setattr(courses_module, "get_course_cache", lambda: cache)
    monkeypatch.setattr(courses_module, "TTBClient", _FakeTTBClient)
    monkeypatch.setattr(courses_module, "CalendarCourseClient", _FakeCalendarClient)
    app = create_app(config=_TestConfig())
    return app.test_client()


# ---------------------------------------------------------------------------
# GET /api/sessions
# ---------------------------------------------------------------------------


def test_list_sessions_decodes_and_filters_reference_data(client):
    resp = client.get("/api/sessions")
    assert resp.status_code == 200
    body = resp.get_json()
    codes = {s["code"] for s in body["sessions"]}
    # header entry and the hyphenated combined session are excluded.
    assert codes == {"20265", FALL, WINTER}
    assert body["defaultSession"] == FALL

    fall_entry = next(s for s in body["sessions"] if s["code"] == FALL)
    assert fall_entry == {"code": FALL, "term": "F", "termName": "Fall", "year": 2026, "label": "Fall 2026"}
    winter_entry = next(s for s in body["sessions"] if s["code"] == WINTER)
    assert winter_entry["term"] == "S"
    assert winter_entry["year"] == 2027


# ---------------------------------------------------------------------------
# GET /api/courses
# ---------------------------------------------------------------------------


def test_search_courses_syncs_once_and_ranks_by_code_prefix(client, cache):
    resp = client.get("/api/courses?q=POL")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["session"] == FALL
    assert [c["code"] for c in body["courses"]] == ["POL208H1", "POL300H1"]
    assert cache.course_count(FALL) == len(_FALL_SESSION_COURSES)

    # Second request must not re-sync (TTBClient.search would still work, but
    # course_count staying put proves the cache short-circuits the sync).
    resp2 = client.get("/api/courses?q=POL")
    assert resp2.status_code == 200
    assert cache.course_count(FALL) == len(_FALL_SESSION_COURSES)


def test_search_courses_reports_catalog_complete(client):
    """`catalogComplete` should be True once `_ensure_session_synced` reports
    a finished sync (the fake TTB client here always completes in one bounded
    call -- see `_FakeTTBClient.search`'s `stats["complete"] = True`)."""
    resp = client.get("/api/courses?q=POL")
    assert resp.status_code == 200
    assert resp.get_json()["catalogComplete"] is True


def test_search_courses_ttb_failure_resolving_default_session_is_a_clean_502(
    client, monkeypatch: Any
):
    """Regression test for issue #7: `search_courses` used to call
    `TTBClient().current_sessions()` (to resolve the default session when the
    request omits `session`, exactly what the Courses page's requests do)
    with no error handling at all, so a live TTB failure surfaced as an
    unhandled 500 instead of the clean `json_error` shape every other failure
    path in this module returns."""

    class _BoomOnCurrentSessions:
        def __init__(self, *_a: Any, **_k: Any) -> None:
            pass

        def current_sessions(self) -> list[str]:
            raise RuntimeError("TTB is unreachable")

    monkeypatch.setattr(courses_module, "TTBClient", _BoomOnCurrentSessions)

    resp = client.get("/api/courses?q=POL")  # no `session` param -> hits the default-session path
    assert resp.status_code == 502
    assert "error" in resp.get_json()


def test_cached_current_sessions_reuses_ttb_result_across_requests(client, cache, monkeypatch: Any):
    """The default-session lookup must not hit TTB live on every request --
    the Courses page never sends a `session` param, so every debounced
    keystroke search used to be a live TTB round trip (issue #7). A second
    request within the cache TTL should reuse the first result."""
    call_count = 0

    class _CountingTTBClient(_FakeTTBClient):
        def current_sessions(self) -> list[str]:
            nonlocal call_count
            call_count += 1
            return super().current_sessions()

    monkeypatch.setattr(courses_module, "TTBClient", _CountingTTBClient)

    resp1 = client.get("/api/courses?q=POL")
    assert resp1.status_code == 200
    resp2 = client.get("/api/courses?q=POL")
    assert resp2.status_code == 200
    assert call_count == 1, "expected current_sessions() to be cached, not called on every search"


def test_search_courses_defaults_to_current_fall_session(client):
    resp = client.get("/api/courses")
    assert resp.status_code == 200
    assert resp.get_json()["session"] == FALL


def test_search_courses_explicit_session_param(client):
    resp = client.get(f"/api/courses?session={WINTER}")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["session"] == WINTER
    assert body["courses"] == []  # fake TTBClient returns nothing for Winter


def test_search_courses_rejects_bad_session(client):
    resp = client.get("/api/courses?session=abc")
    assert resp.status_code == 422


def test_search_courses_filters_by_level(client):
    resp = client.get("/api/courses?level=300")
    body = resp.get_json()
    assert [c["code"] for c in body["courses"]] == ["POL300H1"]


def test_search_courses_rejects_bad_level(client):
    resp = client.get("/api/courses?level=250")
    assert resp.status_code == 422


def test_search_courses_filters_by_breadth(client):
    resp = client.get("/api/courses?breadth=5")
    body = resp.get_json()
    assert [c["code"] for c in body["courses"]] == ["AAA100H1"]


def test_search_courses_rejects_bad_breadth(client):
    resp = client.get("/api/courses?breadth=9")
    assert resp.status_code == 422


def test_search_courses_filters_by_term(client):
    resp = client.get("/api/courses?term=f")
    body = resp.get_json()
    assert {c["code"] for c in body["courses"]} == {"POL208H1", "POL300H1", "AAA100H1"}

    resp2 = client.get("/api/courses?term=s")
    assert resp2.get_json()["courses"] == []


def test_search_courses_rejects_bad_term(client):
    resp = client.get("/api/courses?term=X")
    assert resp.status_code == 422


def test_search_courses_filters_by_has_seats(client):
    # POL300H1's only section is full (30/30); POL208H1 and AAA100H1 have seats.
    resp = client.get("/api/courses?hasSeats=true")
    body = resp.get_json()
    codes = {c["code"] for c in body["courses"]}
    assert codes == {"POL208H1", "AAA100H1"}
    assert all(c["hasSeats"] for c in body["courses"])


def test_search_courses_paginates(client):
    resp = client.get("/api/courses?pageSize=2&page=1")
    body = resp.get_json()
    assert body["total"] == 3
    assert body["totalPages"] == 2
    assert len(body["courses"]) == 2

    resp2 = client.get("/api/courses?pageSize=2&page=2")
    assert len(resp2.get_json()["courses"]) == 1


def test_search_courses_bad_page_param_is_422(client):
    resp = client.get("/api/courses?page=nope")
    assert resp.status_code == 422


def test_search_courses_empty_result_is_not_an_error(client):
    resp = client.get("/api/courses?q=ZZZNOPE")
    assert resp.status_code == 200
    assert resp.get_json()["courses"] == []


# ---------------------------------------------------------------------------
# GET /api/courses/:code
# ---------------------------------------------------------------------------


def test_get_course_detail_groups_multiple_ttb_offerings(client):
    resp = client.get("/api/courses/POL208H1")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == "POL208H1"
    assert body["source"] == "ttb"
    assert set(body["terms"]) == {"F", "S"}
    assert len(body["offerings"]) == 2
    fall_offering = next(o for o in body["offerings"] if o["sectionCode"] == "F")
    assert fall_offering["sections"][0]["name"] == "LEC0101"
    winter_offering = next(o for o in body["offerings"] if o["sectionCode"] == "S")
    assert winter_offering["sections"][0]["name"] == "LEC5101"


def test_get_course_detail_single_offering(client):
    resp = client.get("/api/courses/POL300H1")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["terms"] == ["F"]
    assert len(body["offerings"]) == 1
    assert body["offerings"][0]["sections"][0]["isFull"] is True


def test_get_course_detail_falls_back_to_calendar_when_ttb_has_nothing(client):
    resp = client.get("/api/courses/CAL100H1")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["source"] == "calendar"
    assert body["title"] == "Calendar-only Course"
    assert body["offerings"] == [{"sectionCode": "", "sections": []}]


def test_get_course_detail_not_found_is_404(client):
    resp = client.get("/api/courses/ZZZ999H1")
    assert resp.status_code == 404


def test_get_course_detail_lowercase_code_is_normalized(client):
    resp = client.get("/api/courses/pol300h1")
    assert resp.status_code == 200
    assert resp.get_json()["code"] == "POL300H1"
