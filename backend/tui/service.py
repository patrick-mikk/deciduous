"""Uniform keyword-search facade over the three data-source clients.

The TUI layer should only ever talk to `SearchService` - never import the
data clients directly - so it stays a thin view over one consistent
`SearchResult` shape regardless of which UofT data source answered.

Two source-specific realities shape this module:

- **Timetable Builder has no server-side keyword search** - its API's
  `courseCode` is an exact match and `courseTitle` is ignored. So a keyword
  search pulls the whole session once into a local SQLite cache
  (`backend/data_sources/cache.py`) and filters there (code-prefix / title
  substring). This is also where course *details* come from - the cached TTB
  `cmCourseInfo` has description/prereqs/breadth populated.
- **Session defaults to Fall** (Fall 2026 = `20269`). UofT session codes end
  in a term digit: 1=Winter, 5=Summer, 9=Fall, so the Fall session is the
  usable code ending in "9" (never hard-coded - resolved from reference-data).

Network calls here are synchronous; the UI layer runs `SearchService.search`
off the event loop so the terminal never blocks.
"""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass, replace

from backend.data_sources.cache import SqliteCache
from backend.data_sources.calendar_courses.client import CalendarCourseClient
from backend.data_sources.models import Course, Program
from backend.data_sources.programs.client import ProgramClient
from backend.data_sources.timetable.client import TTBClient

_DEFAULT_LOGGER_NAME = "planner.tui"
_TTB_DIVISION = "ARTSC"
_MAX_SECTIONS_SHOWN = 5
_FALL_TERM_DIGIT = "9"


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


class SearchError(Exception):
    """Raised when a keyword search against a data source fails.

    The message is friendly/user-facing (safe to show in the TUI status
    line); the underlying exception is logged with a traceback first, so
    details are always in the log even though the shown message is short.
    """


@dataclass
class SearchResult:
    """One search hit, normalized across calendar/timetable/programs."""

    key: str
    title: str
    detail: str


def _format_course_core(course: Course) -> list[str]:
    """Shared description/prereq/breadth lines for a `Course` (no sections)."""
    lines: list[str] = []
    if course.description:
        lines.append(course.description)
    if course.prerequisites:
        lines.append(f"Prerequisites: {course.prerequisites}")
    if course.corequisites:
        lines.append(f"Corequisites: {course.corequisites}")
    if course.exclusions:
        lines.append(f"Exclusions: {course.exclusions}")
    if course.breadth:
        lines.append(f"Breadth: {', '.join(course.breadth)}")
    if course.distribution:
        lines.append(f"Distribution: {', '.join(course.distribution)}")
    return lines


def _format_sections(course: Course, limit: int = _MAX_SECTIONS_SHOWN) -> list[str]:
    """A short section/enrolment summary, e.g. for the timetable source."""
    if not course.sections:
        return []
    lines = [f"Sections ({len(course.sections)}):"]
    for section in course.sections[:limit]:
        lines.append(
            f"  {section.name} [{section.teach_method}] "
            f"{section.current_enrol}/{section.max_enrol} enrolled, "
            f"{section.waitlist} waitlisted"
        )
    remaining = len(course.sections) - limit
    if remaining > 0:
        lines.append(f"  ... and {remaining} more")
    return lines


def _course_title(course: Course) -> str:
    return f"{course.code} — {course.title}" if course.title else course.code


def _calendar_result(course: Course) -> SearchResult:
    lines = _format_course_core(course)
    detail = "\n".join(lines) if lines else "(no details available)"
    return SearchResult(key=course.code, title=_course_title(course), detail=detail)


def _timetable_result(course: Course) -> SearchResult:
    lines = _format_course_core(course) + _format_sections(course)
    detail = "\n".join(lines) if lines else "(no details available)"
    title = _course_title(course)
    if course.section_code:
        title = f"{title} ({course.section_code})"
    return SearchResult(key=course.code, title=title, detail=detail)


def _program_result(program: Program) -> SearchResult:
    lines: list[str] = []
    if program.program_type:
        lines.append(f"Type: {program.program_type}")
    if program.department:
        lines.append(f"Department: {program.department}")
    if program.total_credits:
        lines.append(f"Total credits: {program.total_credits}")
    if program.enrolment_requirements:
        lines.append(f"Enrolment requirements: {program.enrolment_requirements}")
    if program.completion_requirements:
        lines.append("Completion requirements:")
        for group in program.completion_requirements:
            heading = group.heading or "(general)"
            credits = f" [{group.credits} credit]" if group.credits else ""
            note = " (note)" if group.is_note else ""
            lines.append(f"  {heading}{credits}{note}")
            if group.notes:
                lines.append(f"    note: {group.notes}")
            if group.courses:
                lines.append(
                    "    " + ", ".join(f"{c.code} ({c.credits})" for c in group.courses)
                )
            elif group.course_codes:
                lines.append(f"    {', '.join(group.course_codes)}")
    elif program.raw_completion_text:
        lines.append(f"Completion requirements: {program.raw_completion_text}")
    detail = "\n".join(lines) if lines else "(no details available)"
    title = f"{program.code} — {program.title}" if program.title else program.code
    return SearchResult(key=program.code, title=title, detail=detail)


class SearchService:
    """Keyword search over calendar/timetable/programs, one uniform shape."""

    SOURCES = ["calendar", "timetable", "programs"]

    def __init__(
        self,
        logger: logging.Logger | None = None,
        cache: SqliteCache | None = None,
        prefer_term_digit: str = _FALL_TERM_DIGIT,
        use_llm_grouping: bool = True,
    ) -> None:
        self._logger = logger or logging.getLogger(_DEFAULT_LOGGER_NAME)
        self._prefer_term_digit = prefer_term_digit
        self._ttb_session: str | None = None
        self._cache_arg = cache
        self._cache_obj: SqliteCache | None = None
        self._use_llm_grouping = use_llm_grouping
        self._grouper_obj = None  # lazily-constructed GeminiGrouper

    # ------------------------------------------------------------------ cache
    def _cache(self) -> SqliteCache:
        """Lazily open the SQLite cache (only sources that need it open it)."""
        if self._cache_obj is None:
            self._cache_obj = self._cache_arg or SqliteCache()
            self._logger.info("Using local cache at %s", self._cache_obj.path)
        return self._cache_obj

    # ---------------------------------------------------------------- session
    def session(self) -> str:
        """The TTB session used for timetable data (Fall by default), cached.

        Picks the usable session code ending in the preferred term digit
        (9=Fall) from reference-data; falls back to the first usable code.
        """
        if self._ttb_session is None:
            sessions = TTBClient().current_sessions()
            if not sessions:
                raise SearchError(
                    "Timetable Builder has no current sessions available right now."
                )
            preferred = [s for s in sessions if s.endswith(self._prefer_term_digit)]
            self._ttb_session = preferred[0] if preferred else sessions[0]
            self._logger.info("Timetable session set to %s", self._ttb_session)
        return self._ttb_session

    # ----------------------------------------------------------------- search
    def search(self, source: str, keyword: str) -> list[SearchResult]:
        """Run a keyword search against `source`.

        Always returns a list of `SearchResult` (empty if nothing matched).
        Raises `SearchError` with a friendly message on any client/network
        failure; the underlying exception is logged first.
        """
        if source not in self.SOURCES:
            raise SearchError(
                f"Unknown search source {source!r}; expected one of {self.SOURCES}"
            )
        keyword = keyword.strip()
        try:
            if source == "calendar":
                return self._search_calendar(keyword)
            if source == "timetable":
                return self._search_timetable(keyword)
            return self._search_programs(keyword)
        except SearchError:
            raise
        except Exception as exc:  # noqa: BLE001 - deliberately broad, see docstring
            self._logger.exception("Search failed (source=%s, keyword=%r)", source, keyword)
            raise SearchError(f"{source} search failed: {exc}") from exc

    def _search_calendar(self, keyword: str) -> list[SearchResult]:
        courses = CalendarCourseClient().search(keyword)
        return [_calendar_result(c) for c in courses]

    def _search_timetable(self, keyword: str) -> list[SearchResult]:
        session = self.session()
        self._ensure_courses_synced(session)
        courses = self._cache().search_courses(session, keyword)
        return [_timetable_result(c) for c in courses]

    def _search_programs(self, keyword: str) -> list[SearchResult]:
        """Fast path: return heuristic requirement groups and cache them.

        Gemini is NOT called here - it runs only on demand via
        `load_requirements` (the TUI's "Load requirements" button), so a search
        stays fast. A program already Gemini-enriched earlier is reused from
        the cache.
        """
        programs = ProgramClient().search(keyword)
        out: list[SearchResult] = []
        for program in programs:
            cached = self._cache().get_program(program.code)
            if cached is not None and any(g.courses for g in cached.completion_requirements):
                program = cached  # reuse a prior on-demand Gemini enrichment
            else:
                self._cache().upsert_programs([program], _now_iso())  # cache heuristic groups
            out.append(_program_result(program))
        return out

    def load_requirements(self, code: str) -> SearchResult | None:
        """On demand: Gemini-segment ONE program's requirements and cache them.

        Backs the TUI's "Load requirements" button. Returns the enriched card,
        or None if `code` isn't in the cache (search it first). Raises
        `SearchError` if Gemini grouping is unavailable or fails.
        """
        program = self._cache().get_program(code)
        if program is None:
            return None
        if any(g.courses for g in program.completion_requirements):
            return _program_result(program)  # already enriched earlier

        grouper = self._grouper()
        if grouper is None:
            raise SearchError("Gemini grouping is disabled (set GEMINI_API_KEY to enable it).")
        if not program.raw_completion_text:
            return _program_result(program)

        try:
            result = grouper.group(program.raw_completion_text)
        except Exception as exc:  # noqa: BLE001 - surface a friendly message
            self._logger.exception("Gemini grouping failed for %s", code)
            raise SearchError(f"Loading requirements for {code} failed: {exc}") from exc

        program = replace(
            program,
            completion_requirements=result.groups,
            total_credits=result.total_credits or program.total_credits,
        )
        self._cache().upsert_programs([program], _now_iso())
        self._logger.info(
            "Loaded requirements for %s: %d groups (%.0f%% capture)",
            code, len(result.groups), result.report.get("capture_pct", 0.0),
        )
        return _program_result(program)

    def _grouper(self):
        """Lazily build the Gemini grouper; None if LLM grouping is disabled."""
        if not self._use_llm_grouping:
            return None
        if self._grouper_obj is None:
            from backend.config import load_env
            from backend.data_sources.llm_grouper import GeminiGrouper

            load_env()  # make GEMINI_API_KEY from .env available
            self._grouper_obj = GeminiGrouper()
        return self._grouper_obj

    # ------------------------------------------------------------------ sync
    def _ensure_courses_synced(self, session: str) -> None:
        """Pull the full ARTSC session from TTB into the cache once.

        TTB can't keyword-search, so we cache the whole session (~1,600
        courses) the first time it's needed and filter locally thereafter.
        """
        cache = self._cache()
        if cache.course_count(session) > 0:
            return
        self._logger.info("Syncing timetable courses for session %s from TTB...", session)
        courses = TTBClient().search(session, division=_TTB_DIVISION, course_code="")
        count = cache.upsert_courses(session, courses, _now_iso())
        cache.set_meta(f"synced:courses:{session}", _now_iso())
        self._logger.info("Cached %d courses for session %s", count, session)
