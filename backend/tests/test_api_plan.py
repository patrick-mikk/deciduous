"""Exercises the plan blueprint: GET/PUT /api/plan round-trips (with note
encryption verified at the DB row level), and POST /api/plan/validate +
POST /api/plan/autoplan against a `SqliteCache` seeded directly with fixture
`Course`/`Program` rows (no network — see docs/conventions.md).
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest  # noqa: E402

from backend.app import create_app  # noqa: E402
from backend.config_app import Config  # noqa: E402
from backend.data_sources.models import Course, Program, RequirementGroup  # noqa: E402
from backend.extensions import get_course_cache, get_session  # noqa: E402
from backend.models_db import PlanItem, ProgramEnrolment, TranscriptEntry  # noqa: E402


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
def app():
    return create_app(config=_TestConfig())


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def _clear_course_cache():
    # `get_course_cache()` is a process-wide singleton (backend/extensions.py) --
    # clear it before/after each test so fixtures from one test never leak into
    # another (tests run in the same process).
    get_course_cache().clear()
    yield
    get_course_cache().clear()


def _csrf_headers(client) -> dict:
    resp = client.get("/api/auth/csrf")
    token = resp.get_json()["csrfToken"]
    return {"X-CSRF-Token": token}


def _signup(client, email="student@mail.utoronto.ca", password="correcthorsebattery") -> dict:
    headers = _csrf_headers(client)
    resp = client.post("/api/auth/signup", json={"email": email, "password": password}, headers=headers)
    assert resp.status_code == 201
    return resp.get_json()["user"]


def _course(
    code: str,
    session_code: str = "F",
    credit: float = 0.5,
    prerequisites: str = "",
    corequisites: str = "",
    exclusions: str = "",
    breadth: list[str] | None = None,
    distribution: list[str] | None = None,
) -> Course:
    return Course(
        code=code,
        title=code,
        section_code=session_code,
        credit=credit,
        campus="St. George",
        description="",
        prerequisites=prerequisites,
        corequisites=corequisites,
        exclusions=exclusions,
        breadth=breadth or [],
        distribution=distribution or [],
        sections=[],
    )


# --------------------------------------------------------------------- GET/PUT


def test_get_plan_creates_empty_primary_plan(client):
    _signup(client)
    resp = client.get("/api/plan")
    assert resp.status_code == 200
    plan = resp.get_json()["plan"]
    assert plan["isPrimary"] is True
    assert plan["items"] == []


def test_put_plan_requires_csrf_token(client):
    _signup(client)
    resp = client.put("/api/plan", json={"items": []})
    assert resp.status_code == 403


def test_put_then_get_round_trips_items_and_decrypts_notes(client, app):
    _signup(client)
    headers = _csrf_headers(client)
    payload = {
        "label": "My Degree Plan",
        "items": [
            {"courseCode": "csc148h1", "termSession": "20269", "status": "planned", "notes": "take with a friend"},
            {"courseCode": "MAT137Y1", "termSession": "20269-20271", "status": "planned"},
        ],
    }
    resp = client.put("/api/plan", json=payload, headers=headers)
    assert resp.status_code == 200
    plan = resp.get_json()["plan"]
    assert plan["label"] == "My Degree Plan"
    assert len(plan["items"]) == 2
    assert plan["items"][0]["courseCode"] == "CSC148H1"
    assert plan["items"][0]["notes"] == "take with a friend"
    assert plan["items"][1]["notes"] is None

    # The DB row itself must never hold the plaintext note.
    with app.app_context():
        db = get_session()
        row = db.query(PlanItem).filter_by(course_code="CSC148H1").one()
        assert row.notes_encrypted is not None
        assert "take with a friend" not in row.notes_encrypted

    get_resp = client.get("/api/plan")
    got = get_resp.get_json()["plan"]
    assert {i["courseCode"] for i in got["items"]} == {"CSC148H1", "MAT137Y1"}


def test_put_plan_rejects_item_missing_required_fields(client):
    _signup(client)
    headers = _csrf_headers(client)
    resp = client.put("/api/plan", json={"items": [{"courseCode": "CSC148H1"}]}, headers=headers)
    assert resp.status_code == 422


def test_put_plan_rejects_invalid_status(client):
    _signup(client)
    headers = _csrf_headers(client)
    resp = client.put(
        "/api/plan",
        json={"items": [{"courseCode": "CSC148H1", "termSession": "20269", "status": "bogus"}]},
        headers=headers,
    )
    assert resp.status_code == 422


def test_put_plan_replaces_previous_items(client):
    _signup(client)
    headers = _csrf_headers(client)
    client.put(
        "/api/plan",
        json={"items": [{"courseCode": "CSC148H1", "termSession": "20269", "status": "planned"}]},
        headers=headers,
    )
    headers = _csrf_headers(client)
    resp = client.put(
        "/api/plan",
        json={"items": [{"courseCode": "MAT137Y1", "termSession": "20269-20271", "status": "planned"}]},
        headers=headers,
    )
    plan = resp.get_json()["plan"]
    assert [i["courseCode"] for i in plan["items"]] == ["MAT137Y1"]


def test_plan_requires_auth(client):
    resp = client.get("/api/plan")
    assert resp.status_code == 401


# ------------------------------------------------------------------- validate


def test_validate_flags_unmet_prerequisite(client):
    _signup(client)
    cache = get_course_cache()
    cache.upsert_courses(
        "20269",
        [_course("CSC148H1", prerequisites="CSC108H1")],
        "now",
    )

    headers = _csrf_headers(client)
    resp = client.post(
        "/api/plan/validate",
        json={"items": [{"courseCode": "CSC148H1", "termSession": "20269", "status": "planned"}]},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.get_json()
    prereq_issues = [i for i in body["issues"] if i["type"] == "prerequisite"]
    assert len(prereq_issues) == 1
    assert prereq_issues[0]["courseCode"] == "CSC148H1"
    assert prereq_issues[0]["severity"] == "error"


def test_validate_passes_when_prerequisite_completed_earlier(client):
    _signup(client)
    cache = get_course_cache()
    cache.upsert_courses("20269", [_course("CSC148H1", prerequisites="CSC108H1")], "now")

    headers = _csrf_headers(client)
    resp = client.post(
        "/api/plan/validate",
        json={
            "items": [
                {"courseCode": "CSC108H1", "termSession": "20261", "status": "completed"},
                {"courseCode": "CSC148H1", "termSession": "20269", "status": "planned"},
            ]
        },
        headers=headers,
    )
    body = resp.get_json()
    assert not [i for i in body["issues"] if i["type"] == "prerequisite"]


def test_validate_uses_saved_transcript_for_completed_prerequisite(client):
    user = _signup(client)
    cache = get_course_cache()
    cache.upsert_courses("20269", [_course("CSC148H1", prerequisites="CSC108H1")], "now")

    # Seed a completed transcript entry directly via the DB (bypassing any
    # transcript API, which is out of scope for this blueprint).
    with client.application.app_context():
        db = get_session()
        db.add(TranscriptEntry(user_id=user["id"], code="CSC108H1", credits=0.5, status="completed"))
        db.commit()

    headers = _csrf_headers(client)
    resp = client.post(
        "/api/plan/validate",
        json={"items": [{"courseCode": "CSC148H1", "termSession": "20269", "status": "planned"}]},
        headers=headers,
    )
    body = resp.get_json()
    assert not [i for i in body["issues"] if i["type"] == "prerequisite"]


def test_validate_flags_exclusion_conflict(client):
    _signup(client)
    cache = get_course_cache()
    cache.upsert_courses(
        "20269",
        [
            _course("STA130H1", exclusions="STA220H1"),
            _course("STA220H1"),
        ],
        "now",
    )

    headers = _csrf_headers(client)
    resp = client.post(
        "/api/plan/validate",
        json={
            "items": [
                {"courseCode": "STA130H1", "termSession": "20269", "status": "planned"},
                {"courseCode": "STA220H1", "termSession": "20269", "status": "planned"},
            ]
        },
        headers=headers,
    )
    body = resp.get_json()
    exclusion_issues = [i for i in body["issues"] if i["type"] == "exclusion"]
    assert len(exclusion_issues) == 1
    assert exclusion_issues[0]["courseCode"] == "STA130H1"


def test_validate_flags_course_not_offered_in_planned_session(client):
    _signup(client)
    cache = get_course_cache()
    # Session 20269 is synced (has data) but does NOT include PHL100Y1.
    cache.upsert_courses("20269", [_course("CSC148H1")], "now")

    headers = _csrf_headers(client)
    resp = client.post(
        "/api/plan/validate",
        json={"items": [{"courseCode": "PHL100Y1", "termSession": "20269", "status": "planned"}]},
        headers=headers,
    )
    body = resp.get_json()
    offering_issues = [i for i in body["issues"] if i["type"] == "offering"]
    assert len(offering_issues) == 1
    assert offering_issues[0]["severity"] == "warning"


def test_validate_does_not_flag_offering_when_session_never_synced(client):
    _signup(client)
    # No cache.upsert_courses call at all -- the cache has nothing for 20269.
    headers = _csrf_headers(client)
    resp = client.post(
        "/api/plan/validate",
        json={"items": [{"courseCode": "PHL100Y1", "termSession": "20269", "status": "planned"}]},
        headers=headers,
    )
    body = resp.get_json()
    assert not [i for i in body["issues"] if i["type"] == "offering"]
    assert [i for i in body["issues"] if i["type"] == "unverified"]


def test_validate_summary_computes_credit_totals_and_same_subject_cap(client):
    _signup(client)
    headers = _csrf_headers(client)
    # 16 x 1.0-credit POL Y-courses (fabricated codes) -> over the 15.0 same-subject cap.
    items = [
        {"courseCode": f"POL{300 + i}Y1", "termSession": "20269-20271", "status": "planned"}
        for i in range(16)
    ]
    resp = client.post("/api/plan/validate", json={"items": items}, headers=headers)
    body = resp.get_json()
    summary = body["summary"]
    assert summary["totalCredits"] == 16.0
    assert summary["level300PlusCredits"] == 16.0
    assert summary["sameSubjectOverCap"] == [{"subject": "POL", "credits": 16.0}]


def test_validate_requirement_mapping_against_declared_program(client):
    user = _signup(client)
    cache = get_course_cache()
    cache.upsert_programs(
        [
            Program(
                code="ASMAJ1305A",
                title="Political Science Major",
                program_type="major",
                department="Political Science",
                department_url="",
                enrolment_requirements="",
                total_credits=8.0,
                completion_requirements=[
                    RequirementGroup(
                        heading="Group A",
                        credits=1.0,
                        is_note=False,
                        course_codes=["POL208H1", "POL200Y1"],
                        rules=[],
                        raw_text="",
                    )
                ],
                raw_completion_text="",
            )
        ],
        "now",
    )
    with client.application.app_context():
        db = get_session()
        db.add(
            ProgramEnrolment(
                user_id=user["id"], program_code="ASMAJ1305A", program_title="Political Science Major"
            )
        )
        db.commit()

    headers = _csrf_headers(client)
    resp = client.post(
        "/api/plan/validate",
        json={"items": [{"courseCode": "POL208H1", "termSession": "20269", "status": "planned"}]},
        headers=headers,
    )
    body = resp.get_json()
    assert len(body["programs"]) == 1
    program_out = body["programs"][0]
    assert program_out["cached"] is True
    assert program_out["groups"][0]["earnedCredits"] == 0.5
    assert program_out["groups"][0]["coveredCourses"] == ["POL208H1"]


def test_validate_flags_one_type_per_subject_violation(client):
    user = _signup(client)
    with client.application.app_context():
        db = get_session()
        db.add(
            ProgramEnrolment(
                user_id=user["id"], program_code="ASMAJ1305A", program_title="Political Science Major"
            )
        )
        db.add(
            ProgramEnrolment(
                user_id=user["id"], program_code="ASMIN1305A", program_title="Political Science Minor"
            )
        )
        db.commit()

    headers = _csrf_headers(client)
    resp = client.post("/api/plan/validate", json={"items": []}, headers=headers)
    body = resp.get_json()
    combo_issues = [i for i in body["issues"] if i["type"] == "one-type-per-subject"]
    assert len(combo_issues) == 1


def test_validate_flags_uncached_enrolled_program_as_unparsed(client):
    """Issue #4: an enrolled program with no cached data at all must not
    silently report "0 issues" -- it's not "no requirements", it's "requirements
    unknown", and the response must say so per-program."""
    user = _signup(client)
    with client.application.app_context():
        db = get_session()
        db.add(
            ProgramEnrolment(
                user_id=user["id"], program_code="ASMAJ1478", program_title="Economics Major"
            )
        )
        db.commit()

    headers = _csrf_headers(client)
    resp = client.post("/api/plan/validate", json={"items": []}, headers=headers)
    body = resp.get_json()
    unparsed = [i for i in body["issues"] if i["type"] == "requirements_unparsed"]
    assert len(unparsed) == 1
    assert unparsed[0]["severity"] == "warning"
    assert unparsed[0]["courseCode"] == "ASMAJ1478"
    assert unparsed[0]["message"] == (
        "Requirements for Economics Major haven't been parsed yet — "
        "program progress can't be checked."
    )


def test_validate_flags_cached_program_with_no_extracted_requirements_as_unparsed(client):
    """Same contract, but for a program that IS cached, just with zero
    course codes ever extracted from its completion-requirement text (the
    Gemini-parse-failed case from issue #1) -- not merely "not fetched"."""
    user = _signup(client)
    cache = get_course_cache()
    cache.upsert_programs(
        [
            Program(
                code="ASMAJ1478",
                title="Economics Major",
                program_type="major",
                department="Economics",
                department_url="",
                enrolment_requirements="",
                total_credits=8.0,
                completion_requirements=[],  # never parsed
                raw_completion_text="(8.0 credits) ECO101H1, ECO102H1, MAT133Y1 ...",
            )
        ],
        "now",
    )
    with client.application.app_context():
        db = get_session()
        db.add(
            ProgramEnrolment(
                user_id=user["id"], program_code="ASMAJ1478", program_title="Economics Major"
            )
        )
        db.commit()

    headers = _csrf_headers(client)
    resp = client.post("/api/plan/validate", json={"items": []}, headers=headers)
    body = resp.get_json()
    unparsed = [i for i in body["issues"] if i["type"] == "requirements_unparsed"]
    assert len(unparsed) == 1
    assert unparsed[0]["courseCode"] == "ASMAJ1478"
    assert "Economics Major" in unparsed[0]["message"]


def test_validate_requires_items_to_be_a_list(client):
    _signup(client)
    headers = _csrf_headers(client)
    resp = client.post("/api/plan/validate", json={"items": "not-a-list"}, headers=headers)
    assert resp.status_code == 422


# ------------------------------------------------------------------- autoplan


def test_autoplan_requires_sessions(client):
    _signup(client)
    headers = _csrf_headers(client)
    resp = client.post("/api/plan/autoplan", json={"courseCodes": ["CSC148H1"]}, headers=headers)
    assert resp.status_code == 422


def test_autoplan_orders_courses_by_prerequisite_using_course_info_hints(client):
    _signup(client)
    headers = _csrf_headers(client)
    resp = client.post(
        "/api/plan/autoplan",
        json={
            "courseCodes": ["CSC148H1", "CSC108H1", "CSC207H1"],
            "sessions": ["20269", "20271", "20279"],
            "maxCreditsPerTerm": 2.5,
            "courseInfo": {
                "CSC148H1": {"prerequisites": "CSC108H1", "credit": 0.5},
                "CSC207H1": {"prerequisites": "CSC148H1", "credit": 0.5},
                "CSC108H1": {"prerequisites": "", "credit": 0.5},
            },
        },
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert not body["unplaced"]

    order = {}
    for term_idx, term in enumerate(body["terms"]):
        for item in term["items"]:
            order[item["courseCode"]] = term_idx

    assert order["CSC108H1"] < order["CSC148H1"] < order["CSC207H1"]


def test_autoplan_respects_credit_cap_per_term(client):
    _signup(client)
    headers = _csrf_headers(client)
    resp = client.post(
        "/api/plan/autoplan",
        json={
            "courseCodes": ["AAA100H1", "BBB100H1", "CCC100H1"],
            "sessions": ["20269", "20271"],
            "maxCreditsPerTerm": 1.0,
        },
        headers=headers,
    )
    body = resp.get_json()
    for term in body["terms"]:
        assert term["totalCredits"] <= 1.0 + 1e-9


def test_autoplan_flags_circular_prerequisite_as_unplaced(client):
    _signup(client)
    headers = _csrf_headers(client)
    resp = client.post(
        "/api/plan/autoplan",
        json={
            "courseCodes": ["XXX100H1", "YYY100H1"],
            "sessions": ["20269", "20271", "20279"],
            "courseInfo": {
                "XXX100H1": {"prerequisites": "YYY100H1"},
                "YYY100H1": {"prerequisites": "XXX100H1"},
            },
        },
        headers=headers,
    )
    body = resp.get_json()
    unplaced_codes = {u["courseCode"] for u in body["unplaced"]}
    assert unplaced_codes == {"XXX100H1", "YYY100H1"}
    assert all(u["reason"] == "circular prerequisite reference" for u in body["unplaced"])


def test_autoplan_flags_not_enough_terms(client):
    _signup(client)
    headers = _csrf_headers(client)
    resp = client.post(
        "/api/plan/autoplan",
        json={
            "courseCodes": ["AAA100H1", "BBB100H1"],
            "sessions": ["20269"],
            "maxCreditsPerTerm": 0.5,
        },
        headers=headers,
    )
    body = resp.get_json()
    assert len(body["terms"]) == 1
    assert len(body["unplaced"]) == 1
    assert body["unplaced"][0]["reason"] == "not enough terms provided"


def test_autoplan_defaults_to_saved_plan_and_transcript(client):
    _signup(client)
    headers = _csrf_headers(client)
    client.put(
        "/api/plan",
        json={"items": [{"courseCode": "CSC148H1", "termSession": "20269", "status": "planned"}]},
        headers=_csrf_headers(client),
    )

    headers = _csrf_headers(client)
    resp = client.post(
        "/api/plan/autoplan",
        json={"sessions": ["20271", "20279"]},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.get_json()
    placed_codes = {item["courseCode"] for term in body["terms"] for item in term["items"]}
    assert placed_codes == {"CSC148H1"}
