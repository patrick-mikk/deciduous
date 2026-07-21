"""Exercises `backend/api/me.py`'s `/api/me` and `/api/me/transcript` routes,
focused on the CGPA/"Cum" mismatch + "?" session-rendering bug fix:

- The backend GPA engine (`backend/planner/gpa.py`) resolves grade points
  letter-FIRST, falling back to the numeric mark only when there's no
  recognised letter -- a stale pre-5bbe9ae import can have a letter grade
  that disagrees with its mark (the ACORN parser bug captured the CrsAvg
  column instead of the student's own grade), which silently drags the CGPA
  away from what the mark alone would suggest.
- `/api/me/transcript` must expose a per-session running cumulative GPA
  (`cumGpa`) computed with that SAME engine, and its chronologically-last
  session's `cumGpa` must be identical to the response's top-level `cgpa` --
  not by coincidence, but because both numbers come from the exact same
  accumulated-course computation.
- A completed course whose letter and mark disagree by more than one grade
  step surfaces a re-import nudge in `warnings`.
- A legacy, pre-normalization session string ("2026 Winter") must come back
  as a normalized 5-digit code, never verbatim gibberish that would render
  as "?" in the frontend's `formatSession`.
- A stale, never-collapsed ACORN "in progress" snapshot row for a course
  that later completed (or was superseded by a later registration) must be
  dropped entirely from both `/api/me`'s flat `transcript` and
  `/api/me/transcript`'s per-session groups -- not just hidden client-side.

Seeds transcript rows through the real `POST /api/import/capture` endpoint
(which persists through the normal encrypt-at-rest path) rather than poking
`TranscriptEntry` rows directly, so these tests exercise the same code path
a real import would.
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
from backend.extensions import get_course_cache  # noqa: E402


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


def _import_transcript(client, courses: list[dict]) -> dict:
    """Persist `courses` (bookmarklet-capture-shaped dicts) via the real
    import endpoint, so grades/marks flow through the normal encrypt-at-rest
    path exactly like a real import."""
    headers = _csrf_headers(client)
    resp = client.post(
        "/api/import/capture",
        json={"transcript": courses},
        headers=headers,
    )
    assert resp.status_code == 200, resp.get_data(as_text=True)
    return resp.get_json()


# --------------------------------------------------------- letter-vs-mark CGPA


def test_transcript_cgpa_uses_letter_precedence_over_mark(client):
    """A stale pre-5bbe9ae import: MAT137Y1's letter ("B") disagrees with its
    mark (92, which implies "A+") -- the engine must use the LETTER (3.0),
    not what the mark alone implies (4.0), matching `grade_points()`'s
    documented precedence."""
    _signup(client)
    _import_transcript(
        client,
        [
            {
                "code": "CSC148H1",
                "credits": 0.5,
                "mark": 78,
                "grade": "B+",
                "session": "20239",
                "status": "completed",
            },
            {
                "code": "MAT137Y1",
                "credits": 1.0,
                "mark": 92,
                "grade": "B",
                "session": "20249-20251",
                "status": "completed",
            },
        ],
    )

    resp = client.get("/api/me/transcript")
    assert resp.status_code == 200
    body = resp.get_json()

    # Letter-first: (0.5*3.3 + 1.0*3.0) / 1.5 = 3.1, NOT the mark-implied
    # (0.5*3.3 + 1.0*4.0) / 1.5 = 3.7667 a mark-only engine would produce.
    expected_cgpa = (0.5 * 3.3 + 1.0 * 3.0) / 1.5
    mark_only_cgpa = (0.5 * 3.3 + 1.0 * 4.0) / 1.5
    assert body["cgpa"] == pytest.approx(expected_cgpa, abs=1e-6)
    assert body["cgpa"] != pytest.approx(mark_only_cgpa, abs=0.01)

    # The mismatch (grade "B" vs mark 92 -> "A+", 4 steps apart) must surface
    # as a re-import nudge.
    assert any("re-import" in w.lower() for w in body["warnings"])


def test_transcript_cum_gpa_matches_top_level_cgpa_by_construction(client):
    """The chronologically-LAST session's `cumGpa` must be bit-identical to
    the response's top-level `cgpa` -- both are `cgpa()` over the exact same
    accumulated course list, not independently-computed numbers that happen
    to agree."""
    _signup(client)
    _import_transcript(
        client,
        [
            {
                "code": "CSC148H1",
                "credits": 0.5,
                "mark": 78,
                "grade": "B+",
                "session": "20239",
                "status": "completed",
            },
            {
                "code": "MAT137Y1",
                "credits": 1.0,
                "mark": 92,
                "grade": "B",
                "session": "20249-20251",
                "status": "completed",
            },
        ],
    )

    body = client.get("/api/me/transcript").get_json()
    sessions = body["sessions"]
    # Newest first.
    assert [s["session"] for s in sessions] == ["20249-20251", "20239"]
    assert sessions[0]["cumGpa"] == body["cgpa"]
    # The earlier (oldest) session's cumGpa is just its own sgpa (only one
    # course counted so far).
    assert sessions[1]["cumGpa"] == pytest.approx(3.3, abs=1e-6)
    assert sessions[1]["sgpa"] == pytest.approx(3.3, abs=1e-6)

    # The top-card CGPA (GET /api/me) must trace to the exact same engine.
    me_body = client.get("/api/me").get_json()
    assert me_body["cgpa"] == pytest.approx(body["cgpa"], abs=1e-6)


def test_transcript_no_warning_when_grades_are_consistent(client):
    _signup(client)
    _import_transcript(
        client,
        [
            {"code": "CSC148H1", "credits": 0.5, "mark": 78, "grade": "B+", "session": "20239", "status": "completed"},
        ],
    )
    body = client.get("/api/me/transcript").get_json()
    assert body["warnings"] == []


# --------------------------------------------------------------- session labels


def test_transcript_normalizes_legacy_session_label(client):
    """A pre-normalization DB row holding a human-format session ("2026
    Winter") must come back as a proper 5-digit code ("20261") -- never
    verbatim gibberish a naive frontend formatter would render as "?"."""
    _signup(client)
    _import_transcript(
        client,
        [
            {
                "code": "POL208H1",
                "credits": 0.5,
                "mark": 80,
                "grade": "A-",
                "session": "2026 Winter",
                "status": "completed",
            },
        ],
    )

    transcript_body = client.get("/api/me/transcript").get_json()
    assert [s["session"] for s in transcript_body["sessions"]] == ["20261"]

    me_body = client.get("/api/me").get_json()
    assert me_body["transcript"][0]["session"] == "20261"


def test_transcript_normalizes_alternate_legacy_ordering(client):
    _signup(client)
    _import_transcript(
        client,
        [
            {
                "code": "POL208H1",
                "credits": 0.5,
                "mark": 80,
                "grade": "A-",
                "session": "Fall 2025",
                "status": "completed",
            },
        ],
    )
    body = client.get("/api/me/transcript").get_json()
    assert body["sessions"][0]["session"] == "20259"


def test_transcript_keeps_unrecognisable_session_verbatim(client):
    """Something neither a code nor a recognised legacy label falls back to
    the raw text -- never dropped, never crashes chronological sorting."""
    _signup(client)
    _import_transcript(
        client,
        [
            {
                "code": "POL208H1",
                "credits": 0.5,
                "mark": 80,
                "grade": "A-",
                "session": "some weird note",
                "status": "completed",
            },
        ],
    )
    resp = client.get("/api/me/transcript")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["sessions"][0]["session"] == "some weird note"


# ---------------------------------------------------- stale IPR-snapshot rows


def test_collapses_stale_ipr_snapshot_when_later_row_completes(client):
    """MAT133Y1: an uncollapsed pre-5bbe9ae-style DB holds BOTH a stale
    Fall-2024 in-progress snapshot row (no grade yet) and the real
    Summer-2025 completed row. Only the completed row should survive."""
    _signup(client)
    _import_transcript(
        client,
        [
            {"code": "MAT133Y1", "credits": 1.0, "session": "20249-20251", "status": "in_progress", "grade": "IPR"},
            {"code": "MAT133Y1", "credits": 1.0, "mark": 76, "grade": "B", "session": "20255", "status": "completed"},
        ],
    )

    me_body = client.get("/api/me").get_json()
    mat_rows = [c for c in me_body["transcript"] if c["code"] == "MAT133Y1"]
    assert len(mat_rows) == 1
    assert mat_rows[0]["status"] == "completed"
    assert mat_rows[0]["session"] == "20255"


def test_collapses_stale_ipr_snapshot_superseded_by_later_in_progress_retake(client):
    """ECO200Y1: a stale Fall-2025 IPR snapshot PLUS a genuine, currently
    in-progress Summer-2026 retake. You can't be concurrently, genuinely "in
    progress" in the same course code twice -- the later row (even though
    it's also in-progress) proves the earlier one is stale and superseded,
    so only the Summer-2026 retake should survive."""
    _signup(client)
    _import_transcript(
        client,
        [
            {"code": "ECO200Y1", "credits": 1.0, "session": "20259", "status": "in_progress", "grade": "IPR"},
            {"code": "ECO200Y1", "credits": 1.0, "session": "20265", "status": "in_progress", "grade": "IPR"},
        ],
    )

    me_body = client.get("/api/me").get_json()
    eco_rows = [c for c in me_body["transcript"] if c["code"] == "ECO200Y1"]
    assert len(eco_rows) == 1
    assert eco_rows[0]["session"] == "20265"
    assert eco_rows[0]["status"] == "in_progress"


def test_projector_candidate_rows_after_collapse_match_expected_scenario(client):
    """The exact user-reported scenario: MAT133Y1 (completed), ECO202Y1 and
    ECO220Y1 (both completed, Winter 2026, with stale Fall-2025 IPR
    snapshots), and ECO200Y1 (a genuine Summer-2026 retake, plus a stale
    Fall-2025 IPR snapshot). After collapsing, only ECO200Y1 should look
    like an "in-progress or planned" course -- the same simple status filter
    the frontend GPA projector applies (Transcript.tsx `plannedCourses`)
    becomes correct once it's fed these canonical, collapsed rows."""
    _signup(client)
    _import_transcript(
        client,
        [
            {"code": "MAT133Y1", "credits": 1.0, "session": "20249-20251", "status": "in_progress", "grade": "IPR"},
            {"code": "MAT133Y1", "credits": 1.0, "mark": 76, "grade": "B", "session": "20255", "status": "completed"},
            {"code": "ECO202Y1", "credits": 1.0, "session": "20259", "status": "in_progress", "grade": "IPR"},
            {"code": "ECO202Y1", "credits": 1.0, "mark": 82, "grade": "A-", "session": "20261", "status": "completed"},
            {"code": "ECO220Y1", "credits": 1.0, "session": "20259", "status": "in_progress", "grade": "IPR"},
            {"code": "ECO220Y1", "credits": 1.0, "mark": 74, "grade": "B", "session": "20261", "status": "completed"},
            {"code": "ECO200Y1", "credits": 1.0, "session": "20259", "status": "in_progress", "grade": "IPR"},
            {"code": "ECO200Y1", "credits": 1.0, "session": "20265", "status": "in_progress", "grade": "IPR"},
        ],
    )

    me_body = client.get("/api/me").get_json()
    transcript = me_body["transcript"]
    assert len(transcript) == 4  # one canonical row per course code

    planned_or_in_progress = {
        c["code"] for c in transcript if c["status"] in ("planned", "in_progress")
    }
    assert planned_or_in_progress == {"ECO200Y1"}

    eco200 = next(c for c in transcript if c["code"] == "ECO200Y1")
    assert eco200["session"] == "20265"


def test_collapse_never_touches_completed_retake_rows(client):
    """Two genuinely completed attempts at the same code (a real retake,
    both graded) are never collapsed -- collapsing only ever applies to
    in-progress/IPR snapshot rows."""
    _signup(client)
    _import_transcript(
        client,
        [
            {"code": "STA220H1", "credits": 0.5, "mark": 45, "grade": "F", "session": "20239", "status": "completed"},
            {
                "code": "STA220H1",
                "credits": 0.5,
                "mark": 80,
                "grade": "A-",
                "session": "20249",
                "status": "extra",
            },
        ],
    )
    me_body = client.get("/api/me").get_json()
    sta_rows = [c for c in me_body["transcript"] if c["code"] == "STA220H1"]
    assert len(sta_rows) == 2
