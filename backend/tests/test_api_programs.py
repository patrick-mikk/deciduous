"""Exercises the programs blueprint end-to-end against an isolated in-memory
DB + in-memory course cache.

`ProgramClient` and the Gemini grouper (`_grouper`) are monkeypatched at the
`backend.api.programs` module level - per docs/conventions.md ("Unit tests
must not hit the network"), same pattern as `backend/tests/test_tui_service.py`.
`get_course_cache` is also monkeypatched to a fresh `SqliteCache(":memory:")`
per test so tests never share state through the process-wide singleton cache.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest  # noqa: E402

import backend.api.programs as programs_module  # noqa: E402
from backend.app import create_app  # noqa: E402
from backend.config_app import Config  # noqa: E402
from backend.data_sources.cache import PROGRAMS_CATALOG_FULL_AT, SqliteCache  # noqa: E402
from backend.data_sources.llm_grouper import GroupingResult, LLMGroupingError  # noqa: E402
from backend.data_sources.models import (  # noqa: E402
    Program,
    RequirementCourse,
    RequirementGroup,
    RequirementRule,
)


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
    monkeypatch.setattr(programs_module, "get_course_cache", lambda: cache)
    app = create_app(config=_TestConfig())
    return app.test_client()


def _csrf_headers(client) -> dict:
    resp = client.get("/api/auth/csrf")
    token = resp.get_json()["csrfToken"]
    return {"X-CSRF-Token": token}


def _signup(client, email: str = "student@mail.utoronto.ca") -> None:
    headers = _csrf_headers(client)
    resp = client.post(
        "/api/auth/signup",
        json={"email": email, "password": "correcthorsebattery"},
        headers=headers,
    )
    assert resp.status_code == 201


class _BoomProgramClient:
    """Fails the test if constructed - proves a code path never hits the network."""

    def __init__(self, *_a: Any, **_k: Any) -> None:
        raise AssertionError("ProgramClient must not be constructed here")


def _mark_catalog_full(cache: SqliteCache) -> None:
    """Pretend a full catalog pull already ran (what refresh_cache.py records),
    so empty-q "browse" requests trust the seeded cache instead of self-healing
    with a live pull."""
    cache.set_meta(PROGRAMS_CATALOG_FULL_AT, "2026-07-08T00:00:00")


def _program(
    code: str = "ASMAJ1305A",
    title: str = "Geographic Data Science Major",
    program_type: str = "major",
    groups: list[RequirementGroup] | None = None,
    raw_completion_text: str = "(8.0 credits) First Year: GGR112H1",
) -> Program:
    if groups is None:
        groups = [
            RequirementGroup(
                heading="First Year",
                credits=0.5,
                is_note=False,
                course_codes=["GGR112H1"],
                rules=[RequirementRule(credits=0.5, description="GGR112H1", course_codes=["GGR112H1"])],
                raw_text="First Year: GGR112H1",
            )
        ]
    return Program(
        code=code,
        title=title,
        program_type=program_type,
        department="Geography",
        department_url="https://geography.utoronto.ca",
        enrolment_requirements="Completion of 4.0 credits.",
        total_credits=8.0,
        completion_requirements=groups,
        raw_completion_text=raw_completion_text,
    )


# ---------------------------------------------------------------------------
# GET /api/programs (search)
# ---------------------------------------------------------------------------


def test_search_programs_serves_from_cache_without_hitting_network(client, cache, monkeypatch):
    cache.upsert_programs([_program()], "2026-07-08T00:00:00")
    monkeypatch.setattr(programs_module, "ProgramClient", _BoomProgramClient)

    resp = client.get("/api/programs?q=Geographic")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["total"] == 1
    assert body["programs"][0]["code"] == "ASMAJ1305A"
    assert body["programs"][0]["programType"] == "major"


def test_search_programs_falls_back_to_live_search_and_caches(client, cache, monkeypatch):
    class _FakeProgramClient:
        def search(self, keyword: str, program_type: str = "", max_pages: int = 5):
            assert keyword == "Geographic"
            return [_program()]

    monkeypatch.setattr(programs_module, "ProgramClient", _FakeProgramClient)

    resp = client.get("/api/programs?q=Geographic")
    assert resp.status_code == 200
    assert resp.get_json()["total"] == 1
    assert cache.get_program("ASMAJ1305A") is not None  # seeded for next time


def test_search_programs_filters_by_type_and_subject(client, cache, monkeypatch):
    cache.upsert_programs(
        [
            _program(code="ASMAJ1305A", program_type="major"),
            _program(code="ASMIN1305B", title="Geography Minor", program_type="minor"),
            _program(code="ASSPE0608", title="Sociology Specialist", program_type="specialist"),
        ],
        "2026-07-08T00:00:00",
    )
    _mark_catalog_full(cache)  # the ?subject= call below is an empty-q browse
    monkeypatch.setattr(programs_module, "ProgramClient", _BoomProgramClient)

    resp = client.get("/api/programs?type=minor")
    body = resp.get_json()
    assert [p["code"] for p in body["programs"]] == ["ASMIN1305B"]

    resp = client.get("/api/programs?subject=1305")
    body = resp.get_json()
    codes = {p["code"] for p in body["programs"]}
    assert codes == {"ASMAJ1305A", "ASMIN1305B"}


def test_search_programs_paginates(client, cache, monkeypatch):
    cache.upsert_programs(
        [_program(code=f"ASMAJ{i:04d}", title=f"Program {i}") for i in range(25)],
        "2026-07-08T00:00:00",
    )
    _mark_catalog_full(cache)  # empty-q browse must not self-heal here
    monkeypatch.setattr(programs_module, "ProgramClient", _BoomProgramClient)

    resp = client.get("/api/programs?pageSize=10&page=2")
    body = resp.get_json()
    assert body["total"] == 25
    assert body["totalPages"] == 3
    assert len(body["programs"]) == 10


def test_search_programs_bad_page_param_is_422(client, monkeypatch):
    monkeypatch.setattr(programs_module, "ProgramClient", _BoomProgramClient)
    resp = client.get("/api/programs?page=nope")
    assert resp.status_code == 422


def test_browse_self_heals_full_catalog_once(client, cache, monkeypatch):
    """Empty-q browse on a never-bulk-loaded cache pulls the FULL catalog once
    (even over a partial cache seeded by keyword searches), records the meta
    flag, and never pulls again."""
    # Partial cache: one program seeded by an earlier keyword search.
    cache.upsert_programs([_program()], "2026-07-08T00:00:00")

    calls: list[dict] = []

    class _FullCatalogClient:
        def search(self, keyword: str = "", program_type: str = "", max_pages: int = 5):
            calls.append({"keyword": keyword, "type": program_type, "max_pages": max_pages})
            return [
                _program(),
                _program(code="ASSPE0608", title="Sociology Specialist", program_type="specialist"),
                _program(code="ASMIN2222", title="History Minor", program_type="minor"),
            ]

    monkeypatch.setattr(programs_module, "ProgramClient", _FullCatalogClient)

    resp = client.get("/api/programs")
    assert resp.status_code == 200
    assert resp.get_json()["total"] == 3  # full catalog, not the 1-program partial cache
    assert len(calls) == 1
    assert calls[0]["keyword"] == "" and calls[0]["max_pages"] > 5  # full pull, not keyword-scoped
    assert cache.get_meta(PROGRAMS_CATALOG_FULL_AT) is not None

    # Second browse serves the cache; a network hit would now blow up.
    monkeypatch.setattr(programs_module, "ProgramClient", _BoomProgramClient)
    resp = client.get("/api/programs")
    assert resp.status_code == 200
    assert resp.get_json()["total"] == 3


def test_browse_pull_failure_serves_partial_cache(client, cache, monkeypatch):
    cache.upsert_programs([_program()], "2026-07-08T00:00:00")

    class _DownProgramClient:
        def search(self, *_a: Any, **_k: Any):
            raise RuntimeError("calendar unreachable")

    monkeypatch.setattr(programs_module, "ProgramClient", _DownProgramClient)

    resp = client.get("/api/programs")
    assert resp.status_code == 200  # degrade to the partial cache, not a 502
    assert resp.get_json()["total"] == 1
    assert cache.get_meta(PROGRAMS_CATALOG_FULL_AT) is None  # still incomplete -> retried next browse


def test_browse_pull_failure_with_empty_cache_is_502(client, monkeypatch):
    class _DownProgramClient:
        def search(self, *_a: Any, **_k: Any):
            raise RuntimeError("calendar unreachable")

    monkeypatch.setattr(programs_module, "ProgramClient", _DownProgramClient)

    resp = client.get("/api/programs")
    assert resp.status_code == 502
    assert "Program search failed" in resp.get_json()["error"]


# ---------------------------------------------------------------------------
# GET /api/programs/:code, /:code/requirements
# ---------------------------------------------------------------------------


def test_get_program_detail_from_cache(client, cache):
    cache.upsert_programs([_program()], "2026-07-08T00:00:00")
    resp = client.get("/api/programs/ASMAJ1305A")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == "ASMAJ1305A"
    assert body["requirementsLoaded"] is False
    assert body["completionRequirements"][0]["heading"] == "First Year"


def test_get_program_not_found_is_404(client, monkeypatch):
    class _EmptyProgramClient:
        def search(self, keyword: str, program_type: str = "", max_pages: int = 5):
            return []

    monkeypatch.setattr(programs_module, "ProgramClient", _EmptyProgramClient)
    resp = client.get("/api/programs/ASZZZ9999")
    assert resp.status_code == 404


def test_get_requirements_returns_heuristic_groups(client, cache):
    cache.upsert_programs([_program()], "2026-07-08T00:00:00")
    resp = client.get("/api/programs/ASMAJ1305A/requirements")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["requirementsLoaded"] is False
    assert body["completionRequirements"][0]["courseCodes"] == ["GGR112H1"]


# ---------------------------------------------------------------------------
# POST /api/programs/:code/requirements/reparse
# ---------------------------------------------------------------------------


def test_reparse_requirements_enriches_and_caches(client, cache, monkeypatch):
    cache.upsert_programs([_program()], "2026-07-08T00:00:00")

    class _FakeGrouper:
        def group(self, text: str) -> GroupingResult:
            group = RequirementGroup(
                heading="Group A",
                credits=1.0,
                is_note=False,
                course_codes=["GGR112H1"],
                rules=[],
                raw_text="",
                notes="pick two departments",
                courses=[RequirementCourse(code="GGR112H1", credits=0.5, notes="required")],
            )
            return GroupingResult(groups=[group], total_credits=10.0, report={"capture_pct": 100.0})

    monkeypatch.setattr(programs_module, "_grouper", lambda: _FakeGrouper())

    headers = _csrf_headers(client)
    resp = client.post("/api/programs/ASMAJ1305A/requirements/reparse", headers=headers)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["requirementsLoaded"] is True
    assert body["completionRequirements"][0]["courses"][0]["code"] == "GGR112H1"
    assert body["totalCredits"] == 10.0
    assert body["parseReport"]["capture_pct"] == 100.0

    # Re-fetching returns the now-cached, enriched program.
    detail = client.get("/api/programs/ASMAJ1305A")
    assert detail.get_json()["requirementsLoaded"] is True


def test_reparse_requirements_is_cache_first_and_skips_grouper_when_already_enriched(
    client, cache, monkeypatch
):
    enriched = _program(
        groups=[
            RequirementGroup(
                heading="Group A", credits=1.0, is_note=False, course_codes=["GGR112H1"],
                rules=[], raw_text="", courses=[RequirementCourse(code="GGR112H1", credits=0.5)],
            )
        ]
    )
    cache.upsert_programs([enriched], "2026-07-08T00:00:00")

    def _boom():
        raise AssertionError("Gemini must not be called when already enriched")

    monkeypatch.setattr(programs_module, "_grouper", _boom)

    headers = _csrf_headers(client)
    resp = client.post("/api/programs/ASMAJ1305A/requirements/reparse", headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()["parseReport"] == {"cached": True}


def test_reparse_requirements_llm_failure_is_502(client, cache, monkeypatch):
    cache.upsert_programs([_program()], "2026-07-08T00:00:00")

    class _FailingGrouper:
        def group(self, text: str) -> GroupingResult:
            raise LLMGroupingError("GEMINI_API_KEY is not set.")

    monkeypatch.setattr(programs_module, "_grouper", lambda: _FailingGrouper())

    headers = _csrf_headers(client)
    resp = client.post("/api/programs/ASMAJ1305A/requirements/reparse", headers=headers)
    assert resp.status_code == 502
    assert "error" in resp.get_json()


# ---------------------------------------------------------------------------
# /api/me/programs
# ---------------------------------------------------------------------------


def test_me_programs_requires_auth(client):
    resp = client.get("/api/me/programs")
    assert resp.status_code == 401


def test_add_program_then_list_shows_incomplete_combination(client):
    _signup(client)
    headers = _csrf_headers(client)
    resp = client.post("/api/me/programs", json={"code": "asmaj1305a"}, headers=headers)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["program"]["code"] == "ASMAJ1305A"
    assert body["program"]["programType"] == "major"
    assert body["combination"]["combinationType"] == "incomplete"
    assert body["combination"]["valid"] is False

    listed = client.get("/api/me/programs")
    assert listed.status_code == 200
    listed_body = listed.get_json()
    assert len(listed_body["programs"]) == 1
    assert listed_body["combination"]["majorCount"] == 1


def test_add_program_rejects_duplicate(client):
    _signup(client)
    headers = _csrf_headers(client)
    client.post("/api/me/programs", json={"code": "ASMAJ1305A"}, headers=headers)
    headers = _csrf_headers(client)
    resp = client.post("/api/me/programs", json={"code": "ASMAJ1305A"}, headers=headers)
    assert resp.status_code == 409


def test_add_program_rejects_one_type_per_subject_conflict(client):
    _signup(client)
    headers = _csrf_headers(client)
    client.post("/api/me/programs", json={"code": "ASMAJ1305A"}, headers=headers)
    headers = _csrf_headers(client)
    resp = client.post("/api/me/programs", json={"code": "ASMIN1305B"}, headers=headers)
    assert resp.status_code == 409
    assert "one program type per subject" in resp.get_json()["error"]


def test_add_program_rejects_unrecognized_code(client):
    _signup(client)
    headers = _csrf_headers(client)
    resp = client.post("/api/me/programs", json={"code": "NOTAREALCODE"}, headers=headers)
    assert resp.status_code == 422


def test_two_distinct_majors_form_a_valid_combination(client):
    _signup(client)
    headers = _csrf_headers(client)
    client.post("/api/me/programs", json={"code": "ASMAJ1305A"}, headers=headers)
    headers = _csrf_headers(client)
    resp = client.post("/api/me/programs", json={"code": "ASMAJ0608A"}, headers=headers)
    assert resp.status_code == 201
    combo = resp.get_json()["combination"]
    assert combo["combinationType"] == "major+major"
    assert combo["valid"] is True
    assert combo["warnings"] == []


def test_delete_program_removes_it_and_updates_combination(client):
    _signup(client)
    headers = _csrf_headers(client)
    client.post("/api/me/programs", json={"code": "ASMAJ1305A"}, headers=headers)

    headers = _csrf_headers(client)
    resp = client.delete("/api/me/programs/ASMAJ1305A", headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()["combination"]["combinationType"] == "none"

    listed = client.get("/api/me/programs")
    assert listed.get_json()["programs"] == []


def test_delete_program_not_enrolled_is_404(client):
    _signup(client)
    headers = _csrf_headers(client)
    resp = client.delete("/api/me/programs/ASMAJ9999A", headers=headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# /api/me/programs/order
# ---------------------------------------------------------------------------


def test_reorder_programs_persists_across_list_calls(client):
    _signup(client)
    for code in ("ASMAJ1305A", "ASMAJ0608A", "ASMIN0301A"):
        headers = _csrf_headers(client)
        resp = client.post("/api/me/programs", json={"code": code}, headers=headers)
        assert resp.status_code == 201

    listed = client.get("/api/me/programs")
    assert [p["code"] for p in listed.get_json()["programs"]] == [
        "ASMAJ1305A",
        "ASMAJ0608A",
        "ASMIN0301A",
    ]

    headers = _csrf_headers(client)
    resp = client.put(
        "/api/me/programs/order",
        json={"codes": ["ASMIN0301A", "ASMAJ1305A", "ASMAJ0608A"]},
        headers=headers,
    )
    assert resp.status_code == 200
    assert [p["code"] for p in resp.get_json()["programs"]] == [
        "ASMIN0301A",
        "ASMAJ1305A",
        "ASMAJ0608A",
    ]

    # The new order survives a fresh GET, i.e. it's persisted, not request-local.
    listed = client.get("/api/me/programs")
    assert [p["code"] for p in listed.get_json()["programs"]] == [
        "ASMIN0301A",
        "ASMAJ1305A",
        "ASMAJ0608A",
    ]


def test_reorder_programs_rejects_mismatched_code_set(client):
    _signup(client)
    headers = _csrf_headers(client)
    client.post("/api/me/programs", json={"code": "ASMAJ1305A"}, headers=headers)
    headers = _csrf_headers(client)
    client.post("/api/me/programs", json={"code": "ASMAJ0608A"}, headers=headers)

    headers = _csrf_headers(client)
    missing = client.put("/api/me/programs/order", json={"codes": ["ASMAJ1305A"]}, headers=headers)
    assert missing.status_code == 422

    headers = _csrf_headers(client)
    unknown = client.put(
        "/api/me/programs/order",
        json={"codes": ["ASMAJ1305A", "ASMAJ0608A", "ASMAJ9999A"]},
        headers=headers,
    )
    assert unknown.status_code == 422

    headers = _csrf_headers(client)
    duplicate = client.put(
        "/api/me/programs/order",
        json={"codes": ["ASMAJ1305A", "ASMAJ1305A"]},
        headers=headers,
    )
    assert duplicate.status_code == 422


def test_reorder_programs_requires_auth(client):
    resp = client.put("/api/me/programs/order", json={"codes": []})
    assert resp.status_code in (401, 403)
