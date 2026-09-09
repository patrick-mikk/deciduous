"""Temporary local SQLite cache for pulled/parsed course & program data.

TTB has no server-side keyword/prefix search (the API's courseCode is an exact
match and courseTitle is ignored), so keyword search over the timetable is done
by pulling a whole session once and filtering locally. This module is that local
store: courses and programs are normalized (via the data-source clients), cached
here, and queried with plain SQL LIKE.

The database is a single SQLite file. By default it lives in the OS temp dir
(a genuinely *temporary* local cache); pass an explicit `path` to inspect it or
keep it around. Nested value objects (sections, requirement groups) are stored
as JSON blobs and reconstructed on read, so callers always get real
`Course`/`Program` dataclasses back - never raw rows.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
import threading
from dataclasses import asdict
from pathlib import Path

from backend.data_sources.models import (
    Course,
    Instructor,
    MeetingTime,
    Program,
    RequirementCourse,
    RequirementGroup,
    RequirementRule,
    Section,
)

DEFAULT_CACHE_PATH = Path(tempfile.gettempdir()) / "uoft_planner_cache.sqlite"

# `meta` key recording when a FULL program-catalog pull last completed (set by
# `backend/scripts/refresh_cache.py` and the cold-cache fallback in
# `backend/api/programs.py`). While unset, the cached `programs` table may be
# an incomplete handful seeded by individual keyword searches, so catalog
# browses must not trust it as the whole catalog.
PROGRAMS_CATALOG_FULL_AT = "programs_catalog_full_at"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS courses (
    session       TEXT NOT NULL,
    code          TEXT NOT NULL,
    title         TEXT,
    section_code  TEXT,
    credit        REAL,
    campus        TEXT,
    description   TEXT,
    prerequisites TEXT,
    corequisites  TEXT,
    exclusions    TEXT,
    breadth       TEXT,   -- JSON list
    distribution  TEXT,   -- JSON list
    sections      TEXT,   -- JSON list
    fetched_at    TEXT,
    PRIMARY KEY (session, code)
);
CREATE INDEX IF NOT EXISTS ix_courses_title ON courses (session, title);

CREATE TABLE IF NOT EXISTS programs (
    code                   TEXT PRIMARY KEY,
    title                  TEXT,
    program_type           TEXT,
    department             TEXT,
    department_url         TEXT,
    enrolment_requirements TEXT,
    total_credits          REAL,
    completion             TEXT,   -- JSON list of RequirementGroup
    raw_completion_text    TEXT,
    fetched_at             TEXT
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


# --------------------------------------------------------- (de)serialization
def _course_to_row(session: str, course: Course, fetched_at: str) -> tuple:
    return (
        session,
        course.code,
        course.title,
        course.section_code,
        course.credit,
        course.campus,
        course.description,
        course.prerequisites,
        course.corequisites,
        course.exclusions,
        json.dumps(course.breadth),
        json.dumps(course.distribution),
        json.dumps([asdict(s) for s in course.sections]),
        fetched_at,
    )


def _course_from_row(row: sqlite3.Row) -> Course:
    sections = [
        Section(
            name=s["name"],
            teach_method=s["teach_method"],
            section_number=s["section_number"],
            current_enrol=s["current_enrol"],
            max_enrol=s["max_enrol"],
            waitlist=s["waitlist"],
            instructors=[Instructor(**i) for i in s["instructors"]],
            meeting_times=[MeetingTime(**m) for m in s["meeting_times"]],
            delivery_modes=list(s["delivery_modes"]),
        )
        for s in json.loads(row["sections"] or "[]")
    ]
    return Course(
        code=row["code"],
        title=row["title"] or "",
        section_code=row["section_code"] or "",
        credit=row["credit"] or 0.0,
        campus=row["campus"] or "",
        description=row["description"] or "",
        prerequisites=row["prerequisites"] or "",
        corequisites=row["corequisites"] or "",
        exclusions=row["exclusions"] or "",
        breadth=json.loads(row["breadth"] or "[]"),
        distribution=json.loads(row["distribution"] or "[]"),
        sections=sections,
    )


def _program_to_row(program: Program, fetched_at: str) -> tuple:
    return (
        program.code,
        program.title,
        program.program_type,
        program.department,
        program.department_url,
        program.enrolment_requirements,
        program.total_credits,
        json.dumps([asdict(g) for g in program.completion_requirements]),
        program.raw_completion_text,
        fetched_at,
    )


def _program_from_row(row: sqlite3.Row) -> Program:
    groups = [
        RequirementGroup(
            heading=g["heading"],
            credits=g["credits"],
            is_note=g["is_note"],
            course_codes=list(g["course_codes"]),
            rules=[RequirementRule(**r) for r in g["rules"]],
            raw_text=g["raw_text"],
            notes=g.get("notes", ""),
            courses=[RequirementCourse(**c) for c in g.get("courses", [])],
        )
        for g in json.loads(row["completion"] or "[]")
    ]
    return Program(
        code=row["code"],
        title=row["title"] or "",
        program_type=row["program_type"] or "",
        department=row["department"] or "",
        department_url=row["department_url"] or "",
        enrolment_requirements=row["enrolment_requirements"] or "",
        total_credits=row["total_credits"] or 0.0,
        completion_requirements=groups,
        raw_completion_text=row["raw_completion_text"] or "",
    )


class SqliteCache:
    """A local SQLite store for normalized course/program data."""

    def __init__(self, path: str | Path | None = None) -> None:
        if path is None:
            self.path: str | Path = DEFAULT_CACHE_PATH
        elif str(path) == ":memory:":
            self.path = ":memory:"
        else:
            self.path = Path(path)

        if isinstance(self.path, Path):
            self.path.parent.mkdir(parents=True, exist_ok=True)
            conn_target = str(self.path)
        else:
            conn_target = ":memory:"

        # The TUI runs searches on a thread pool (run_in_executor), so the same
        # cache instance is touched from different threads. `check_same_thread=
        # False` allows that; a lock serialises access so cursor/commit state
        # never races.
        self._conn = sqlite3.connect(conn_target, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # ---------------------------------------------------------------- courses
    def upsert_courses(self, session: str, courses: list[Course], fetched_at: str) -> int:
        rows = [_course_to_row(session, c, fetched_at) for c in courses]
        with self._lock:
            self._conn.executemany(
                """INSERT OR REPLACE INTO courses
                   (session, code, title, section_code, credit, campus, description,
                    prerequisites, corequisites, exclusions, breadth, distribution,
                    sections, fetched_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                rows,
            )
            self._conn.commit()
        return len(rows)

    def course_count(self, session: str) -> int:
        with self._lock:
            cur = self._conn.execute(
                "SELECT COUNT(*) FROM courses WHERE session = ?", (session,)
            )
            return int(cur.fetchone()[0])

    def search_courses(self, session: str, keyword: str, limit: int = 100) -> list[Course]:
        """Courses in `session` whose code starts with, or title contains, `keyword`."""
        kw = keyword.strip()
        with self._lock:
            if not kw:
                cur = self._conn.execute(
                    "SELECT * FROM courses WHERE session = ? ORDER BY code LIMIT ?",
                    (session, limit),
                )
            else:
                # Rank code-prefix matches (e.g. "POL" -> POL208H1) ahead of
                # title-substring matches (e.g. "pol" inside "anthropology").
                cur = self._conn.execute(
                    """SELECT * FROM courses
                       WHERE session = ? AND (code LIKE ? OR title LIKE ?)
                       ORDER BY (CASE WHEN code LIKE ? THEN 0 ELSE 1 END), code
                       LIMIT ?""",
                    (session, f"{kw}%", f"%{kw}%", f"{kw}%", limit),
                )
            rows = cur.fetchall()
        return [_course_from_row(r) for r in rows]

    # --------------------------------------------------------------- programs
    def upsert_programs(self, programs: list[Program], fetched_at: str) -> int:
        rows = [_program_to_row(p, fetched_at) for p in programs]
        with self._lock:
            self._conn.executemany(
                """INSERT OR REPLACE INTO programs
                   (code, title, program_type, department, department_url,
                    enrolment_requirements, total_credits, completion,
                    raw_completion_text, fetched_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                rows,
            )
            self._conn.commit()
        return len(rows)

    def program_count(self) -> int:
        with self._lock:
            return int(self._conn.execute("SELECT COUNT(*) FROM programs").fetchone()[0])

    def get_program(self, code: str) -> Program | None:
        """Return one cached program by code, or None if not cached."""
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM programs WHERE code = ?", (code,)
            ).fetchone()
        return _program_from_row(row) if row is not None else None

    def search_programs(self, keyword: str, limit: int = 100) -> list[Program]:
        kw = keyword.strip()
        with self._lock:
            if not kw:
                cur = self._conn.execute(
                    "SELECT * FROM programs ORDER BY code LIMIT ?", (limit,)
                )
            else:
                like = f"%{kw}%"
                cur = self._conn.execute(
                    """SELECT * FROM programs
                       WHERE code LIKE ? OR title LIKE ? OR department LIKE ?
                       ORDER BY code LIMIT ?""",
                    (f"{kw}%", like, like, limit),
                )
            rows = cur.fetchall()
        return [_program_from_row(r) for r in rows]

    # ------------------------------------------------------------------- meta
    def set_meta(self, key: str, value: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, value)
            )
            self._conn.commit()

    def get_meta(self, key: str) -> str | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT value FROM meta WHERE key = ?", (key,)
            ).fetchone()
        return row["value"] if row else None

    def clear(self) -> None:
        with self._lock:
            self._conn.executescript(
                "DELETE FROM courses; DELETE FROM programs; DELETE FROM meta;"
            )
            self._conn.commit()
