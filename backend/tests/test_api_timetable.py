"""Exercises the timetable blueprint end-to-end against an isolated in-memory
DB, with `TTBClient`/`get_course_cache` monkeypatched to a fixture course
catalog so nothing touches the network (docs/conventions.md: unit tests must
not hit the network).

Fixture catalog (`_FAKE_COURSES`):

- AAA100H1: LEC0101 (Mon 10:00-11:00) or LEC0201 (Mon 14:00-15:00); TUT0101
  (Wed 09:00-10:00). LEC0101 conflicts with BBB200H1's LEC0101.
- BBB200H1: LEC0101 (Mon 10:30-11:30, conflicts with AAA100H1 LEC0101) or
  LEC0201 (Tue 09:00-10:00, conflict-free); TUT0101 (Thu 09:00-10:00).
- CCC300H1: LEC0101, full (10/10 enrolled) -- exercises `allowFull`.

So AAA100H1 x BBB200H1 has exactly 3 conflict-free complete schedules (every
combination except AAA LEC0101 + BBB LEC0101).
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest  # noqa: E402

import backend.api.timetable as timetable  # noqa: E402
from backend.app import create_app  # noqa: E402
from backend.config_app import Config  # noqa: E402
from backend.data_sources.cache import SqliteCache  # noqa: E402
from backend.data_sources.models import Course, Instructor, MeetingTime, Section  # noqa: E402
from backend.extensions import get_session  # noqa: E402
from backend.models_db import Plan, PlanItem  # noqa: E402

TERM = "20269"


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
            MeetingTime(day=day, start_min=start_min, end_min=end_min, building="XX", session=TERM)
        ],
        delivery_modes=["in-person"],
    )


def _course(code, sections):
    return Course(
        code=code,
        title=f"Title of {code}",
        section_code="F",
        credit=0.5,
        campus="St. George",
        description="",
        prerequisites="",
        corequisites="",
        exclusions="",
        breadth=[],
        distribution=[],
        sections=sections,
    )


_FAKE_COURSES = {
    "AAA100H1": _course(
        "AAA100H1",
        [
            _section("LEC0101", "LEC", day=1, start_min=600, end_min=660),
            _section("LEC0201", "LEC", day=1, start_min=840, end_min=900),
            _section("TUT0101", "TUT", day=3, start_min=540, end_min=600),
        ],
    ),
    "BBB200H1": _course(
        "BBB200H1",
        [
            _section("LEC0101", "LEC", day=1, start_min=630, end_min=690),
            _section("LEC0201", "LEC", day=2, start_min=540, end_min=600),
            _section("TUT0101", "TUT", day=4, start_min=540, end_min=600),
        ],
    ),
    "CCC300H1": _course(
        "CCC300H1",
        [_section("LEC0101", "LEC", day=5, start_min=540, end_min=600, current=10, max_=10)],
    ),
}


class _FakeTTBClient:
    """Stands in for `TTBClient`: exact-code search against `_FAKE_COURSES`."""

    def __init__(self, base_url: str = "") -> None:
        pass

    def search(self, session, division="ARTSC", course_code=""):
        course = _FAKE_COURSES.get(course_code)
        return [course] if course is not None else []


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
def app(monkeypatch):
    application = create_app(config=_TestConfig())
    fake_cache = SqliteCache(":memory:")
    monkeypatch.setattr(timetable, "get_course_cache", lambda: fake_cache)
    monkeypatch.setattr(timetable, "TTBClient", _FakeTTBClient)
    return application


@pytest.fixture()
def client(app):
    return app.test_client()


def _csrf_headers(client) -> dict:
    resp = client.get("/api/auth/csrf")
    token = resp.get_json()["csrfToken"]
    return {"X-CSRF-Token": token}


def _signed_in_client(client):
    headers = _csrf_headers(client)
    resp = client.post(
        "/api/auth/signup",
        json={"email": "student@mail.utoronto.ca", "password": "correcthorsebattery"},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.get_json()["user"]["id"]


def _create_plan_item(app, user_id, course_code, term_session=TERM, is_primary=True, position=0):
    with app.app_context():
        db = get_session()
        plan = db.query(Plan).filter_by(user_id=user_id, is_primary=is_primary).first()
        if plan is None:
            plan = Plan(user_id=user_id, label="My Plan", is_primary=is_primary)
            db.add(plan)
            db.commit()
        db.add(
            PlanItem(
                plan_id=plan.id,
                course_code=course_code,
                term_session=term_session,
                status="planned",
                position=position,
            )
        )
        db.commit()
        return plan.id


# --------------------------------------------------------------------- GET


def test_plan_sections_requires_auth(client):
    resp = client.get(f"/api/plan/{TERM}/sections")
    assert resp.status_code == 401


def test_plan_sections_rejects_bad_term(client):
    _signed_in_client(client)
    resp = client.get("/api/plan/not-a-term/sections")
    assert resp.status_code == 422


def test_plan_sections_empty_when_no_plan(client):
    _signed_in_client(client)
    resp = client.get(f"/api/plan/{TERM}/sections")
    assert resp.status_code == 200
    assert resp.get_json() == {"term": TERM, "courses": [], "missing": []}


def test_plan_sections_resolves_planned_courses_to_ttb_sections(app, client):
    user_id = _signed_in_client(client)
    _create_plan_item(app, user_id, "AAA100H1")

    resp = client.get(f"/api/plan/{TERM}/sections")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["term"] == TERM
    assert body["missing"] == []
    assert len(body["courses"]) == 1
    course = body["courses"][0]
    assert course["code"] == "AAA100H1"
    section_names = {s["name"] for s in course["sections"]}
    assert section_names == {"LEC0101", "LEC0201", "TUT0101"}
    # camelCase per design/06-data-model-and-api.md
    lec = next(s for s in course["sections"] if s["name"] == "LEC0101")
    assert lec["teachMethod"] == "LEC"
    assert lec["meetingTimes"][0] == {
        "day": 1, "startMin": 600, "endMin": 660, "building": "XX", "session": TERM,
    }


def test_plan_sections_reports_courses_not_offered_as_missing(app, client):
    user_id = _signed_in_client(client)
    _create_plan_item(app, user_id, "ZZZ999H1")

    resp = client.get(f"/api/plan/{TERM}/sections")
    body = resp.get_json()
    assert body["courses"] == []
    assert body["missing"] == ["ZZZ999H1"]


# --------------------------------------------------------------- POST optimize


def _optimize(client, **body):
    headers = _csrf_headers(client)
    return client.post("/api/timetable/optimize", json=body, headers=headers)


def test_optimize_requires_auth(client):
    # CSRF is enforced globally before the route's own @require_auth check, so
    # a signed-out caller needs a valid CSRF pair to even reach the 401.
    headers = _csrf_headers(client)
    resp = client.post(
        "/api/timetable/optimize", json={"term": TERM, "courses": ["AAA100H1"]}, headers=headers
    )
    assert resp.status_code == 401


def test_optimize_requires_csrf(client):
    _signed_in_client(client)
    resp = client.post("/api/timetable/optimize", json={"term": TERM, "courses": ["AAA100H1"]})
    assert resp.status_code == 403


def test_optimize_rejects_missing_or_empty_courses(client):
    _signed_in_client(client)
    resp = _optimize(client, term=TERM, courses=[])
    assert resp.status_code == 422


def test_optimize_rejects_bad_term(client):
    _signed_in_client(client)
    resp = _optimize(client, term="bogus", courses=["AAA100H1"])
    assert resp.status_code == 422


def test_optimize_rejects_too_many_courses(client):
    _signed_in_client(client)
    resp = _optimize(client, term=TERM, courses=[f"C{i}00H1" for i in range(20)])
    assert resp.status_code == 422


def test_optimize_rejects_bad_preferences_time_format(client):
    _signed_in_client(client)
    resp = _optimize(
        client, term=TERM, courses=["AAA100H1"], preferences={"earliestStart": "9am"}
    )
    assert resp.status_code == 422


def test_optimize_rejects_locked_course_not_in_courses(client):
    _signed_in_client(client)
    resp = _optimize(
        client, term=TERM, courses=["AAA100H1"], locked={"BBB200H1": {"LEC": "LEC0101"}}
    )
    assert resp.status_code == 422


def test_optimize_rejects_locked_section_that_does_not_exist(client):
    _signed_in_client(client)
    resp = _optimize(
        client, term=TERM, courses=["AAA100H1"], locked={"AAA100H1": {"LEC": "LEC9999"}}
    )
    assert resp.status_code == 422


def test_optimize_finds_all_conflict_free_schedules(client):
    _signed_in_client(client)
    resp = _optimize(client, term=TERM, courses=["AAA100H1", "BBB200H1"], maxResults=10)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["feasible"] is True
    assert body["missingCourses"] == []
    assert body["blockedCourses"] == []
    # exactly 3 valid combinations (see module docstring); AAA LEC0101 + BBB
    # LEC0101 always excluded because their meetings overlap Monday.
    assert len(body["candidates"]) == 3
    # explicit conflict check: no candidate double-books any overlapping interval
    for candidate in body["candidates"]:
        meetings = [
            (s["section"]["meetingTimes"][0]["day"], s["section"]["meetingTimes"][0]["startMin"],
             s["section"]["meetingTimes"][0]["endMin"])
            for s in candidate["sections"]
        ]
        for i in range(len(meetings)):
            for j in range(i + 1, len(meetings)):
                d1, s1, e1 = meetings[i]
                d2, s2, e2 = meetings[j]
                if d1 == d2:
                    assert not (s1 < e2 and s2 < e1)
    # ranked, best score first
    scores = [c["score"] for c in body["candidates"]]
    assert scores == sorted(scores, reverse=True)
    assert [c["rank"] for c in body["candidates"]] == [1, 2, 3]


def test_optimize_honours_locked_section(client):
    _signed_in_client(client)
    resp = _optimize(
        client,
        term=TERM,
        courses=["AAA100H1", "BBB200H1"],
        locked={"AAA100H1": {"LEC": "LEC0201"}},
        maxResults=10,
    )
    body = resp.get_json()
    assert body["feasible"] is True
    for candidate in body["candidates"]:
        aaa_lec = next(
            s["section"]["name"]
            for s in candidate["sections"]
            if s["courseCode"] == "AAA100H1" and s["teachMethod"] == "LEC"
        )
        assert aaa_lec == "LEC0201"


def test_optimize_reports_missing_course_but_still_schedules_the_rest(client):
    _signed_in_client(client)
    resp = _optimize(client, term=TERM, courses=["AAA100H1", "ZZZ999H1"], maxResults=10)
    body = resp.get_json()
    assert body["missingCourses"] == ["ZZZ999H1"]
    assert body["feasible"] is True
    for candidate in body["candidates"]:
        codes = {s["courseCode"] for s in candidate["sections"]}
        assert codes == {"AAA100H1"}


def test_optimize_full_section_is_blocked_unless_allow_full(client):
    _signed_in_client(client)
    resp = _optimize(client, term=TERM, courses=["CCC300H1"])
    body = resp.get_json()
    assert body["feasible"] is False
    assert body["blockedCourses"] == [{"courseCode": "CCC300H1", "teachMethod": "LEC"}]
    assert body["candidates"] == []

    resp2 = _optimize(
        client, term=TERM, courses=["CCC300H1"], preferences={"allowFull": True}
    )
    body2 = resp2.get_json()
    assert body2["feasible"] is True
    assert body2["blockedCourses"] == []
    assert len(body2["candidates"]) == 1


def test_optimize_respects_max_results_cap(client):
    _signed_in_client(client)
    resp = _optimize(client, term=TERM, courses=["AAA100H1", "BBB200H1"], maxResults=1)
    body = resp.get_json()
    assert len(body["candidates"]) == 1
    assert body["candidates"][0]["rank"] == 1


def test_optimize_rejects_out_of_range_max_results(client):
    _signed_in_client(client)
    resp = _optimize(client, term=TERM, courses=["AAA100H1"], maxResults=99)
    assert resp.status_code == 422
