"""Parse a UofT Degree Explorer export into a normalized `StudentRecordDraft`.

Two independent front doors, one shared internal shape:

- `parse_pdf_bytes` / `parse_pdf_text` -- the "Upload PDF" onboarding path
  (`design/screens/01-auth-and-onboarding.md`). Degree Explorer has no
  documented export schema, so this is a **heuristic, line-oriented** parser:
  it scans each line of the extracted text for a course-code token
  (`backend.planner.course_code.parse_course_code`) or a program-code token
  and pulls session/title/mark/grade context from around it, rather than
  assuming fixed table columns. `raw_text` is always attached to a low-
  confidence draft so a failed parse degrades to "review manually", never a
  silent wrong answer.
- `parse_capture` -- the bookmarklet path. The bookmarklet (browser-side,
  not built here) is expected to emit JSON already shaped close to the
  `StudentRecord` TS interface in `design/06-data-model-and-api.md`, wrapped
  in `<degree-explorer-capture>...</degree-explorer-capture>` tags for the
  user to copy/paste (`design/screens/05-transcript-settings-share.md`);
  this just unwraps + validates + normalizes it.

Both paths return the same `StudentRecordDraft`; `backend/api/import_.py` is
the only caller and owns persistence (turning a draft into `TranscriptEntry`/
`ProgramEnrolment` rows) and auth. Nothing in this module touches the
network, the DB, or Flask, and it never receives real student data in tests
-- only synthetic fixtures (`backend/tests/fixtures/`).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from backend.planner.course_code import parse_course_code, parse_program_code

# --------------------------------------------------------------------------- errors
class DegreeExplorerParseError(ValueError):
    """Raised when input can't be turned into a `StudentRecordDraft` at all
    (e.g. not a PDF, not JSON, missing the capture tags). Callers map this to
    a clean 422 -- never a stack trace (docs/conventions.md)."""


# --------------------------------------------------------------------- grade scale
# design/09-uoft-degree-rules.md section 6. Keys are upper-cased letter grades.
GRADE_POINTS: dict[str, float] = {
    "A+": 4.0, "A": 4.0, "A-": 3.7,
    "B+": 3.3, "B": 3.0, "B-": 2.7,
    "C+": 2.3, "C": 2.0, "C-": 1.7,
    "D+": 1.3, "D": 1.0, "D-": 0.7,
    "F": 0.0, "FL": 0.0,
}

# Percent breakpoints -> letter, highest first (design/09 section 6 table).
_MARK_BREAKPOINTS: list[tuple[int, str]] = [
    (90, "A+"), (85, "A"), (80, "A-"),
    (77, "B+"), (73, "B"), (70, "B-"),
    (67, "C+"), (63, "C"), (60, "C-"),
    (57, "D+"), (53, "D"), (50, "D-"),
    (0, "F"),
]

# Grade notations excluded from GPA (design/09 section 6) -- NOT letter grades,
# so they're kept out of GRADE_POINTS; "F"/"FL" are real failing grades and DO
# count (0.0 GP), so they stay in GRADE_POINTS above, not here.
NOTATIONS_EXCLUDED_FROM_GPA: frozenset[str] = frozenset(
    {"AEG", "CR", "NCR", "EXT", "XTR", "GWR", "IPR", "LWD", "WDR", "SDF", "P"}
)

# Every token this parser recognises as "a grade", for line-scanning.
_ALL_GRADE_TOKENS = sorted(
    set(GRADE_POINTS) | NOTATIONS_EXCLUDED_FROM_GPA, key=len, reverse=True
)

_VALID_STATUSES = {"completed", "in_progress", "planned", "extra"}


def mark_to_letter(mark: float) -> str:
    """Map a numeric mark (0-100) to a letter grade via the design/09 scale."""
    mark_int = round(mark)
    for floor, letter in _MARK_BREAKPOINTS:
        if mark_int >= floor:
            return letter
    return "F"


# ------------------------------------------------------------------------- shapes
@dataclass(frozen=True)
class DraftProgram:
    code: str
    title: str = ""
    start_session: str = ""


@dataclass(frozen=True)
class DraftCourse:
    code: str
    title: str = ""
    credits: float = 0.5
    mark: float | None = None
    grade: str = ""
    session: str = ""
    status: str = "completed"  # completed | in_progress | planned | extra


@dataclass(frozen=True)
class StudentRecordDraft:
    """Everything extracted from one import, ready for `import_.py` to persist.

    `warnings` surfaces lines/fields the parser couldn't confidently place
    (e.g. an unrecognised program line) so the ImportPreview step (`design/
    screens/01-auth-and-onboarding.md`) can show "looks right?" instead of
    silently dropping data.
    """

    programs: list[DraftProgram] = field(default_factory=list)
    courses: list[DraftCourse] = field(default_factory=list)
    cgpa: float | None = None
    warnings: list[str] = field(default_factory=list)


# ------------------------------------------------------------------ session codes
_SESSION_LABEL_RE = re.compile(r"\b(Fall|Winter|Summer)\s+(\d{4})\b", re.IGNORECASE)
_SESSION_CODE_RE = re.compile(r"\b(2\d{3}[159])\b")
_TERM_DIGIT = {"summer": "5", "fall": "9", "winter": "1"}


def normalize_session(text: str) -> str:
    """Extract/convert a session mention in `text` to TTB's 5-digit code
    (see AGENTS.md: "20265"=Summer 2026, "20269"=Fall 2026, "20271"=Winter 2027).
    Returns "" if no session is recognisable."""
    label_m = _SESSION_LABEL_RE.search(text)
    if label_m:
        term, year = label_m.group(1).lower(), label_m.group(2)
        return f"{year}{_TERM_DIGIT[term]}"
    code_m = _SESSION_CODE_RE.search(text)
    return code_m.group(1) if code_m else ""


# -------------------------------------------------------------------- PDF parsing
def extract_pdf_text(data: bytes) -> str:
    """Extract raw text from a PDF's pages, joined with blank lines.

    Isolated from `parse_pdf_text` so the pure line-parsing logic below is
    unit-testable without a real PDF file (see `backend/tests/
    test_degree_explorer_ingest.py`); only this function touches pdfplumber.
    """
    try:
        import pdfplumber  # local import: keep it optional at module load time
    except ImportError as exc:  # pragma: no cover - dependency is pinned in requirements.txt
        raise DegreeExplorerParseError(
            "PDF import is unavailable on the server (pdfplumber not installed)."
        ) from exc

    import io

    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
    except Exception as exc:  # noqa: BLE001 - pdfplumber raises assorted exceptions for bad input
        raise DegreeExplorerParseError(
            "That file doesn't look like a valid PDF. Try re-exporting it from Degree Explorer."
        ) from exc

    text = "\n".join(pages).strip()
    if not text:
        raise DegreeExplorerParseError(
            "No text could be read from that PDF (it may be a scanned image)."
        )
    return text


_PROGRAM_CODE_TOKEN_RE = re.compile(r"\bAS(?:SPE|MAJ|MIN|FOC|CER)\d{3,4}[A-Z]?\b")
_COURSE_CODE_TOKEN_RE = re.compile(r"\b[A-Z]{3}[A-Z0-9]\d{2}[HY]\d\b")
_PROGRAM_TYPE_PREFIX_RE = re.compile(
    r"^\s*(specialist|major|minor|focus|certificate)\s*[-:–]\s*", re.IGNORECASE
)
_EXTRA_FLAG_RE = re.compile(r"\(\s*extra\s*\)", re.IGNORECASE)
_CGPA_RE = re.compile(
    r"cumulative\s*g\.?p\.?a\.?\s*[:\-]?\s*(\d(?:\.\d+)?)", re.IGNORECASE
)
_DECIMAL_NUM_RE = re.compile(r"\d+\.\d+")
_INT_NUM_RE = re.compile(r"(?<!\d)(\d{1,3})(?!\d)")


def _grade_token(text: str) -> tuple[str, int, int] | None:
    """The first recognised grade token in `text`, as (token, start, end)."""
    for token in _ALL_GRADE_TOKENS:
        m = re.search(rf"(?<![A-Za-z]){re.escape(token)}(?![A-Za-z])", text)
        if m:
            return token, m.start(), m.end()
    return None


def _parse_program_line(line: str) -> DraftProgram | None:
    code_m = _PROGRAM_CODE_TOKEN_RE.search(line)
    if code_m is None:
        return None
    pc = parse_program_code(code_m.group(0))
    if pc is None:
        return None

    before = line[: code_m.start()]
    title = _PROGRAM_TYPE_PREFIX_RE.sub("", before).strip(" -–\t")
    # Drop a trailing bare "(" left behind by "Title (CODE)".
    title = title.rstrip("(").strip()

    start_session = normalize_session(line)
    return DraftProgram(code=pc.raw, title=title, start_session=start_session)


def _parse_course_line(line: str) -> DraftCourse | None:
    code_m = _COURSE_CODE_TOKEN_RE.search(line)
    if code_m is None:
        return None
    cc = parse_course_code(code_m.group(0))
    if cc is None:
        return None

    before, after = line[: code_m.start()], line[code_m.end() :]
    session = normalize_session(before) or normalize_session(after)

    is_extra = bool(_EXTRA_FLAG_RE.search(after))
    after_clean = _EXTRA_FLAG_RE.sub("", after)

    grade_hit = _grade_token(after_clean)
    grade = grade_hit[0] if grade_hit else ""
    tail_for_title_end = grade_hit[1] if grade_hit else len(after_clean)
    search_zone = after_clean[:tail_for_title_end]

    # The title runs up to the first digit -- everything from there on is
    # the credit/mark column, e.g. "Intro to Stats    0.5    65    C+". A
    # course title containing a literal digit ("20th Century America") would
    # get cut short here; a known heuristic limitation, not a crash.
    digit_m = re.search(r"\d", search_zone)
    title_end = digit_m.start() if digit_m else len(search_zone)
    title = search_zone[:title_end].strip(" -–\t.,")

    # A mark is a bare 0-100 integer in the numeric tail, ignoring the
    # decimal credit weight (e.g. "0.5") -- credit is derived from the
    # course code itself (design/06-data-model-and-api.md), not this column.
    numeric_zone = _DECIMAL_NUM_RE.sub(" ", search_zone[title_end:])
    mark: float | None = None
    for int_m in _INT_NUM_RE.finditer(numeric_zone):
        value = int(int_m.group(1))
        if 0 <= value <= 100:
            mark = float(value)  # last match wins -- closest to the grade

    if is_extra:
        status = "extra"
    elif grade == "IPR":
        status = "in_progress"
    elif grade == "" and mark is None:
        status = "planned"
    else:
        status = "completed"

    return DraftCourse(
        code=cc.raw,
        title=title,
        credits=cc.credit_value,
        mark=mark,
        grade=grade,
        session=session,
        status=status,
    )


def parse_pdf_text(text: str) -> StudentRecordDraft:
    """Pure line-scan over already-extracted PDF text. See module docstring
    for the heuristic and why it's line-oriented rather than column-fixed."""
    if not text or not text.strip():
        raise DegreeExplorerParseError("No text to parse.")

    programs: list[DraftProgram] = []
    courses: list[DraftCourse] = []
    warnings: list[str] = []
    cgpa: float | None = None
    seen_program_codes: set[str] = set()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        cgpa_m = _CGPA_RE.search(line)
        if cgpa_m:
            cgpa = float(cgpa_m.group(1))
            continue

        # A line can only be ONE of a program line or a course line -- program
        # codes (AS...) and course codes never co-occur on the same real line.
        program = _parse_program_line(line)
        if program is not None:
            if program.code not in seen_program_codes:
                seen_program_codes.add(program.code)
                programs.append(program)
            continue

        course = _parse_course_line(line)
        if course is not None:
            courses.append(course)

    if not programs and not courses:
        warnings.append(
            "Couldn't find any recognisable program or course lines in this PDF. "
            "You can still add courses/programs manually."
        )

    return StudentRecordDraft(programs=programs, courses=courses, cgpa=cgpa, warnings=warnings)


def parse_pdf_bytes(data: bytes) -> StudentRecordDraft:
    """`extract_pdf_text` + `parse_pdf_text`. The only entry point that touches pdfplumber."""
    text = extract_pdf_text(data)
    return parse_pdf_text(text)


# ---------------------------------------------------------------- capture (JSON)
_CAPTURE_TAG_RE = re.compile(
    r"<degree-explorer-capture>(.*)</degree-explorer-capture>", re.IGNORECASE | re.DOTALL
)


def _unwrap_capture_text(raw: str) -> str:
    m = _CAPTURE_TAG_RE.search(raw)
    return m.group(1).strip() if m else raw.strip()


def _coerce_status(value: Any, *, has_grade_or_mark: bool) -> str:
    if value is None or value == "":
        return "completed" if has_grade_or_mark else "planned"
    status = str(value).strip().lower()
    if status not in _VALID_STATUSES:
        raise DegreeExplorerParseError(f"Unrecognised transcript status: {value!r}")
    return status


def _draft_program_from_dict(raw: dict[str, Any]) -> DraftProgram:
    code = str(raw.get("code") or "").strip().upper()
    if not code:
        raise DegreeExplorerParseError("A captured program is missing its code.")
    title = str(raw.get("title") or raw.get("name") or "").strip()
    start_session = str(raw.get("startSession") or raw.get("start_session") or "").strip()
    return DraftProgram(code=code, title=title, start_session=start_session)


def _draft_course_from_dict(raw: dict[str, Any]) -> DraftCourse:
    code = str(raw.get("code") or "").strip().upper()
    if not code:
        raise DegreeExplorerParseError("A captured transcript row is missing its code.")
    cc = parse_course_code(code)
    default_credits = cc.credit_value if cc is not None else 0.5

    credits_raw = raw.get("credits")
    try:
        credits = float(credits_raw) if credits_raw not in (None, "") else default_credits
    except (TypeError, ValueError):
        credits = default_credits

    mark_raw = raw.get("mark")
    try:
        mark = float(mark_raw) if mark_raw not in (None, "") else None
    except (TypeError, ValueError):
        mark = None

    grade = str(raw.get("grade") or "").strip().upper()
    session = str(raw.get("session") or "").strip()
    status = _coerce_status(raw.get("status"), has_grade_or_mark=bool(grade or mark is not None))

    return DraftCourse(
        code=code,
        title=str(raw.get("title") or "").strip(),
        credits=credits,
        mark=mark,
        grade=grade,
        session=session,
        status=status,
    )


def parse_capture(payload: Any) -> StudentRecordDraft:
    """Normalize a bookmarklet capture into a `StudentRecordDraft`.

    Accepts three shapes so the client doesn't have to unwrap anything:
    - a `dict` already shaped like `StudentRecord` (`design/06-data-model-
      and-api.md`): `{"programs": [...], "transcript": [...], "cgpa": ...}`
    - a `dict` with a `"raw"` string field holding the pasted
      `<degree-explorer-capture>...</degree-explorer-capture>` text
    - a bare `str` of that same pasted text (with or without the tags)
    """
    if isinstance(payload, str):
        payload = _unwrap_capture_text(payload)
    elif isinstance(payload, dict) and isinstance(payload.get("raw"), str):
        payload = _unwrap_capture_text(payload["raw"])

    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise DegreeExplorerParseError("That capture doesn't contain valid JSON.") from exc

    if not isinstance(payload, dict):
        raise DegreeExplorerParseError("Capture payload must be a JSON object.")

    programs_raw = payload.get("programs") or []
    transcript_raw = payload.get("transcript") or payload.get("courses") or []
    if not isinstance(programs_raw, list) or not isinstance(transcript_raw, list):
        raise DegreeExplorerParseError("Capture 'programs'/'transcript' must be lists.")

    programs = [_draft_program_from_dict(p) for p in programs_raw if isinstance(p, dict)]
    courses = [_draft_course_from_dict(c) for c in transcript_raw if isinstance(c, dict)]

    cgpa_raw = payload.get("cgpa")
    try:
        cgpa = float(cgpa_raw) if cgpa_raw not in (None, "") else None
    except (TypeError, ValueError):
        cgpa = None

    warnings: list[str] = []
    if not programs and not courses:
        warnings.append("This capture had no programs or transcript rows.")

    return StudentRecordDraft(programs=programs, courses=courses, cgpa=cgpa, warnings=warnings)
