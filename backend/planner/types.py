"""Shared pure dataclasses for the planner engine.

Everything here is a plain, frozen, no-I/O value object — the shapes
`validators.py`, `prereqs.py`, and `gpa.py` operate on. Callers (the Flask API
layer) build these from `TranscriptEntry`/`PlanItem` rows (decrypted) and
`data_sources.models.Course`/`Program` objects; nothing in `planner/` touches
the DB, the cache, or the network.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.planner.course_code import parse_course_code, parse_program_code

# Statuses mirror `design/06-data-model-and-api.md`'s `TranscriptCourse.status`
# and `backend/models_db.py`'s `TranscriptEntry.status`/`PlanItem.status`.
COURSE_STATUSES = frozenset({"completed", "in_progress", "planned", "extra"})


@dataclass(frozen=True)
class CourseRecord:
    """One course on a student's transcript or plan.

    `grade` holds either a standard letter grade ("A+", "B-", ...) or a grade
    notation code ("CR", "NCR", "EXT", "XTR", "AEG", "GWR", "IPR", "LWD",
    "WDR", "SDF", "P", "FL") — see `gpa.py`. `mark` is the raw percentage
    (0-100) when known; either/both may be `None` for ungraded courses.

    `breadth_categories` are the 1-5 Breadth-Requirement category numbers
    (`design/09-uoft-degree-rules.md` §4) this course is tagged with — 0, 1,
    or 2 entries (a Y-course can split across two). `is_transfer_credit` /
    `is_uoft_exchange` feed the 300+ transfer-credit cap (§1).
    """

    code: str
    credits: float
    status: str = "completed"
    session: str | None = None  # e.g. "20269"; "20269-20271" for a Y course
    distribution: tuple[str, ...] = ()  # "Arts" / "Science", from Course.distribution
    breadth_categories: tuple[int, ...] = ()
    grade: str | None = None
    mark: float | None = None
    is_transfer_credit: bool = False
    is_uoft_exchange: bool = False

    def __post_init__(self) -> None:
        if self.status not in COURSE_STATUSES:
            raise ValueError(f"CourseRecord.status must be one of {sorted(COURSE_STATUSES)}, got {self.status!r}")

    @property
    def code_norm(self) -> str:
        return self.code.strip().upper()

    @property
    def subject(self) -> str | None:
        parsed = parse_course_code(self.code)
        return parsed.subject if parsed else None

    @property
    def level(self) -> int | None:
        parsed = parse_course_code(self.code)
        return parsed.level if parsed else None

    @property
    def is_artsci(self) -> bool:
        """THE single ArtSci classification rule for a course record -- every
        consumer (`validators.degree_credit_summary`, `backend.api._audit`'s
        `TranscriptRow` via `backend.api.me._transcript_rows`) reads this
        property rather than re-deriving its own answer, so the same course
        can never be counted as ArtSci in one place and non-ArtSci in
        another (the "dual-engine" bug class this codebase has been burned
        by before -- CGPA, program completion).

        1. Real Calendar/cache data wins: if `distribution` was populated
           (the course was found in the course cache with a non-empty
           `Course.distribution`), trust it -- "Arts" or "Science" means
           ArtSci, anything else (e.g. an Engineering/APSC distribution)
           means not.
        2. No data available (`distribution` empty -- the common case for an
           imported ACORN transcript row nothing has looked up in the cache
           yet, or a past session the cache doesn't carry): fall back to the
           course-code campus digit. This app is scoped to the ARTSC
           division (AGENTS.md), and a St. George Arts & Science course code
           ends its subject+number+credit-letter run in the campus digit
           "1" (e.g. "ECO101H1", "POL208H1"). A transcript row shaped like
           that defaults to ArtSci=True; anything else (unparseable code, or
           a parseable non-"1" campus digit -- UTM/UTSC/professional
           faculties) defaults to False. This is an honest default, not a
           verified fact: a real `distribution` lookup always overrides it.
        """
        if self.distribution:
            return any(d.strip().lower() in ("arts", "science") for d in self.distribution)
        parsed = parse_course_code(self.code)
        return parsed is not None and parsed.campus == "1"


@dataclass(frozen=True)
class Issue:
    """One structured finding from a validator. `severity` is "error" (a rule
    is actively violated), "warning" (a soft rule / risk), or "info"
    (progress not yet complete — not a violation)."""

    severity: str  # "error" | "warning" | "info"
    code: str  # short machine key, e.g. "same-subject-cap"
    message: str
    course_code: str | None = None


@dataclass(frozen=True)
class CourseRequirementText:
    """The three free-text fields `prereqs.py` parses, for one course code."""

    code: str
    prerequisites: str | None = None
    corequisites: str | None = None
    exclusions: str | None = None

    @classmethod
    def from_course(cls, course) -> "CourseRequirementText":
        """Adapt a `data_sources.models.Course`."""
        return cls(
            code=course.code.strip().upper(),
            prerequisites=course.prerequisites,
            corequisites=course.corequisites,
            exclusions=course.exclusions,
        )


@dataclass(frozen=True)
class ProgramRequirement:
    """The slice of a `Program` (data_sources.models) a combination/progress
    check needs: its type, subject, credit target, and the flat set of course
    codes that count toward it (union of its `RequirementGroup.course_codes`).

    `requirements_parsed` is `False` when the source program had completion-
    requirement text but no course codes were ever extracted from it (neither
    the deterministic heuristic parse nor a Gemini reparse succeeded) — i.e.
    `course_codes` is empty because parsing never completed, not because the
    program genuinely requires zero courses. Combination checks
    (`validators.evaluate_program_combination`) must treat this differently
    from "zero credits required": exclude the program from credit-counting
    math and say so, rather than silently letting it contribute 0.
    """

    code: str  # "ASMAJ1305A"
    program_type: str  # "specialist" | "major" | "minor" | "focus" | "certificate"
    subject: str  # 4-digit subject designator, e.g. "1305"
    total_credits: float
    course_codes: frozenset[str] = field(default_factory=frozenset)
    title: str = ""
    requirements_parsed: bool = True

    @classmethod
    def from_program(cls, program, code: str | None = None) -> "ProgramRequirement | None":
        """Adapt a `data_sources.models.Program` into a `ProgramRequirement`.
        Returns `None` if `program.code` (or the given `code`) doesn't parse
        as a POSt code (e.g. a non-ArtSci or malformed code)."""
        raw_code = code or program.code
        parsed = parse_program_code(raw_code)
        if parsed is None:
            return None
        codes: set[str] = set()
        for group in program.completion_requirements:
            codes.update(c.strip().upper() for c in group.course_codes)
        raw_text = (getattr(program, "raw_completion_text", "") or "").strip()
        # Nothing to parse (no completion-requirement text at all) isn't a
        # parsing failure; text present but zero codes captured is.
        requirements_parsed = bool(codes) or not raw_text
        return cls(
            code=parsed.raw,
            program_type=parsed.program_type,
            subject=parsed.subject,
            total_credits=program.total_credits,
            course_codes=frozenset(codes),
            title=getattr(program, "title", "") or "",
            requirements_parsed=requirements_parsed,
        )
