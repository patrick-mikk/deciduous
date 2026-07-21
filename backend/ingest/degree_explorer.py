"""Parse a UofT **Academic History PDF** (ACORN -> Academic History -> Print/
PDF) into a normalized `StudentRecordDraft`.

WHAT THIS ACTUALLY PARSES (read this before touching the regexes below):
UofT's "Degree Explorer" is a *live web tool* -- there is no such thing as a
downloadable "Degree Explorer PDF". The document students actually have is
the Academic History PDF exported from ACORN. This module (and its
identifiers/module name, kept as-is to avoid churning imports across
`backend/api/import_.py` and `backend/api/plan.py`) predates that
correction and still says "Degree Explorer" in a few internal places; the
parsing logic below now targets the ACORN Academic History layout.

Two independent front doors, one shared internal shape:

- `parse_pdf_bytes` / `parse_pdf_text` -- the "Upload PDF" onboarding path
  (`design/screens/01-auth-and-onboarding.md`). ACORN has no documented
  export schema either, so this is still a **heuristic, line-oriented**
  parser: it scans each line of the extracted text for a course-code token
  (`backend.planner.course_code.parse_course_code`) or a program-code token
  and pulls session/title/mark/grade context from around it, rather than
  assuming fixed table columns. On top of that, it now tracks a *running
  session* updated whenever a line looks like a bare per-session section
  heading ("2023 Fall" / "Fall 2023" -- ACORN groups course rows under one
  heading per session rather than repeating the session on every row), and
  falls back to that running session for course rows that don't carry their
  own inline session mention. `raw_text` is always attached to a low-
  confidence draft so a failed parse degrades to "review manually", never a
  silent wrong answer.
- `parse_capture` -- the bookmarklet path. The bookmarklet (browser-side,
  not built here) is expected to emit JSON already shaped close to the
  `StudentRecord` TS interface in `design/06-data-model-and-api.md`, wrapped
  in `<degree-explorer-capture>...</degree-explorer-capture>` tags for the
  user to copy/paste (`design/screens/05-transcript-settings-share.md`);
  this just unwraps + validates + normalizes it. (This tag name is a
  leftover identifier too -- the bookmarklet target is a separate, later
  concern from the PDF-import fix this module docstring is describing.)

Both paths return the same `StudentRecordDraft`; `backend/api/import_.py` is
the only caller and owns persistence (turning a draft into `TranscriptEntry`/
`ProgramEnrolment` rows) and auth. Nothing in this module touches the
network, the DB, or Flask, and it never receives real student data in tests
-- only synthetic fixtures (`backend/tests/fixtures/`,
`backend/tests/test_degree_explorer_ingest.py`).

VALIDATED AGAINST A REAL ACORN PDF (2026-07): the earlier format assumptions
have now been checked against a genuine "Complete Academic History" export,
and the parser handles the real layout, specifically:

- Session headings render as
  "2025 Fall - Bachelor's Degree Program - Trinity College" -- year-first
  label plus a " - program - college" suffix. A heading is recognised as: a
  line *starting* with a session label whose remainder holds NO second
  session label (that second-label exclusion keeps the Registration History
  range line "2024 Fall-2026 Summer: Faculty of Arts and Science" from
  hijacking the running session).
- Course rows are "CODE TITLE WGT MRK GRD CRSAVG": after the title comes the
  credit weight, the mark column (a number, or a notation like IPR/CR), the
  letter grade, then **CrsAvg -- the course-average letter grade**, and
  optionally a trailing EXT/XTR designation. Grade scanning is therefore
  (a) restricted to the text after the first digit (the weight column), so
  title words can't be mistaken for grades, and (b) leftmost-match, so the
  student's own grade wins over the CrsAvg letter to its right. An EXT/XTR
  token *after* the grade is the "Extra" designation (status "extra"), on
  top of whatever the grade itself is (e.g. "CR C+ EXT" = grade CR, extra).
- Long titles wrap onto a following continuation line ("... Justice in the"
  / "Indo-Pacific"); a bare-words line immediately after a course row is
  appended to that course's title.
- A course spanning sessions (Y courses) prints an in-progress snapshot row
  (Mrk "IPR") in each earlier term and a final row in its completing term.
  A row whose mark column is IPR is dropped when a later-session non-IPR
  row exists for the same code -- that collapses the snapshot into the one
  real registration -- while an IPR row with nothing after it (a genuinely
  in-progress course, including a fresh retake registration) is kept.
  An in-progress row for a course with an earlier *passed* attempt gets a
  warning: per design/09 ("Repeated courses / Extra"), such a retake counts
  as Extra (no credit, no GPA) once graded, and ACORN will mark it EXT.
- The GPA lines read "Sessional GPA 3.57 Annual GPA 3.50 Cumulative GPA
  3.50" (no periods); the LAST "Cumulative GPA" seen wins, which is the
  most recent session that prints one.

Still assumed, not yet contradicted by a real sample: the printed credit
weight is not read back -- credits derive from the course code
(`parse_course_code(...).credit_value`, design/06) -- and pdfplumber's
left-to-right reading order is what produces the one-line row shape above.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, replace
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
# Both orderings show up in the wild: Degree Explorer-style exports tend to
# say "Fall 2023"; ACORN's Academic History PDF headings are commonly
# "2023 Fall" (year first) -- see module docstring's ASSUMPTIONS section.
_SESSION_LABEL_RE = re.compile(
    r"\b(?:(Fall|Winter|Summer)\s+(\d{4})|(\d{4})\s+(Fall|Winter|Summer))\b",
    re.IGNORECASE,
)
_SESSION_CODE_RE = re.compile(r"\b(2\d{3}[159])\b")
_TERM_DIGIT = {"summer": "5", "fall": "9", "winter": "1"}

# A session section heading. In a real ACORN Academic History PDF these are
# "2025 Fall - Bachelor's Degree Program - Trinity College": the session
# label LEADS the line and is followed by a program/college suffix. So a
# heading is a line *starting* with the label, whose remainder contains no
# SECOND session label -- that exclusion keeps range lines like the
# Registration History's "2024 Fall-2026 Summer: Faculty of Arts and
# Science" (and any other line merely mentioning two terms) from hijacking
# the running section session for the course rows underneath.
_SESSION_HEADING_START_RE = re.compile(
    r"^\s*(?:(?:Fall|Winter|Summer)\s+\d{4}|\d{4}\s+(?:Fall|Winter|Summer))\b",
    re.IGNORECASE,
)


def normalize_session(text: str) -> str:
    """Extract/convert a session mention in `text` to TTB's 5-digit code
    (see AGENTS.md: "20265"=Summer 2026, "20269"=Fall 2026, "20271"=Winter 2027).
    Returns "" if no session is recognisable."""
    label_m = _SESSION_LABEL_RE.search(text)
    if label_m:
        if label_m.group(1):
            term, year = label_m.group(1).lower(), label_m.group(2)
        else:
            year, term = label_m.group(3), label_m.group(4).lower()
        return f"{year}{_TERM_DIGIT[term]}"
    code_m = _SESSION_CODE_RE.search(text)
    return code_m.group(1) if code_m else ""


def is_session_heading(line: str) -> bool:
    """True if `line` is an ACORN per-session section heading: it *starts*
    with a session label ("2025 Fall - Bachelor's Degree Program - ..."),
    and the rest of the line mentions no second session (which would make it
    a range line like "2024 Fall-2026 Summer: Faculty of ...", not a section
    heading)."""
    m = _SESSION_HEADING_START_RE.match(line)
    if m is None:
        return False
    return _SESSION_LABEL_RE.search(line[m.end():]) is None


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
            "That file doesn't look like a valid PDF. Try downloading it again from "
            "ACORN (Academic History -> Print/PDF)."
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


def _leftmost_grade_token(text: str) -> tuple[str, int, int] | None:
    """The LEFTMOST recognised grade token in `text` (ties broken by longest
    token), as (token, start, end).

    Leftmost matters because a real ACORN row carries TWO letter grades --
    the student's grade, then the CrsAvg course-average letter to its right
    ("0.50 85 A A-"). Scanning token-by-token in list order (the old
    behaviour) could latch onto the CrsAvg letter and silently record the
    wrong grade; leftmost-wins always takes the student's own column."""
    best: tuple[int, int, str] | None = None  # (start, -len, token)
    for token in _ALL_GRADE_TOKENS:
        m = re.search(rf"(?<![A-Za-z]){re.escape(token)}(?![A-Za-z])", text)
        if m is None:
            continue
        key = (m.start(), -len(token), token)
        if best is None or key < best:
            best = key
    if best is None:
        return None
    start, neg_len, token = best
    return token, start, start - neg_len


_EXT_DESIGNATION_RE = re.compile(r"(?<![A-Za-z])(?:EXT|XTR)(?![A-Za-z])")


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


def _parse_course_line(line: str, *, default_session: str = "") -> DraftCourse | None:
    code_m = _COURSE_CODE_TOKEN_RE.search(line)
    if code_m is None:
        return None
    cc = parse_course_code(code_m.group(0))
    if cc is None:
        return None

    before, after = line[: code_m.start()], line[code_m.end() :]
    # Inline session mention on this row wins (Degree Explorer-style export);
    # otherwise fall back to the current ACORN section heading, if any.
    session = normalize_session(before) or normalize_session(after) or default_session

    is_extra = bool(_EXTRA_FLAG_RE.search(after))
    after_clean = _EXTRA_FLAG_RE.sub("", after)

    # The title runs up to the first digit -- everything from there on is
    # the Wgt/Mrk/Grd/CrsAvg column block, e.g. "Intro to Stats 0.50 65 C+
    # B". A course title containing a literal digit ("20th Century America")
    # would get cut short here; a known heuristic limitation, not a crash.
    first_digit = re.search(r"\d", after_clean)
    title_end = first_digit.start() if first_digit else len(after_clean)

    # Grade scanning is restricted to AFTER the first digit (the credit-
    # weight column) so a title word can never be read as a grade, and takes
    # the LEFTMOST token so the student's grade wins over the CrsAvg letter
    # to its right (see _leftmost_grade_token). Rows with no digits at all
    # (no weight column printed) fall back to scanning the whole tail.
    grade_zone_offset = first_digit.start() if first_digit else 0
    grade_hit = _leftmost_grade_token(after_clean[grade_zone_offset:])
    grade = grade_hit[0] if grade_hit else ""

    if grade_hit:
        numbers_end = grade_zone_offset + grade_hit[1]
        grade_end = grade_zone_offset + grade_hit[2]
    else:
        numbers_end = grade_end = len(after_clean)
    title = after_clean[: min(title_end, numbers_end)].strip(" -–\t.,")

    # An EXT/XTR token AFTER the grade is ACORN's "Extra" designation -- an
    # attribute on top of the grade ("CR C+ EXT" = grade CR, Extra), not the
    # grade itself. (When the grade column itself is EXT/XTR, treat that as
    # Extra too.)
    if _EXT_DESIGNATION_RE.search(after_clean[grade_end:]) or grade in ("EXT", "XTR"):
        is_extra = True

    # A mark is a bare 0-100 integer between the title and the grade,
    # ignoring the decimal credit weight (e.g. "0.50") -- credit is derived
    # from the course code itself (design/06-data-model-and-api.md), not
    # this column.
    numeric_zone = _DECIMAL_NUM_RE.sub(" ", after_clean[title_end:numbers_end])
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


# A wrapped-title continuation: pure words/punctuation, no digits, no colon
# (which excludes "Status: In good standing"), no sentence-ending period
# (which excludes "This is not an official transcript.").
_TITLE_CONTINUATION_RE = re.compile(r"^[A-Za-z][A-Za-z ,&'()–-]*$")


def _session_label(code: str) -> str:
    """"20261" -> "Winter 2026" for warning text; the raw code if unknown."""
    names = {"1": "Winter", "5": "Summer", "9": "Fall"}
    if len(code) == 5 and code[4] in names:
        return f"{names[code[4]]} {code[:4]}"
    return code or "an unknown session"


# Passing letter grades/notations for the retake check below: every letter
# that isn't an outright fail, plus CR/P ("Passing grade = 50% / P / CR",
# design/09 section 1).
PASSING_LETTERS_AND_NOTATIONS: frozenset[str] = frozenset(
    {g for g in GRADE_POINTS if g not in ("F", "FL")} | {"CR", "P"}
)


def _collapse_ipr_snapshots(
    courses: list[DraftCourse], warnings: list[str]
) -> list[DraftCourse]:
    """ACORN prints a course spanning sessions (Y courses) as an IPR-marked
    snapshot row in each earlier term plus a final row in its completing
    term. Drop an IPR row whenever a LATER-session non-IPR row exists for
    the same code -- that's the same registration completing, not a second
    course. An IPR row with nothing after it is a genuinely in-progress
    registration (including a fresh retake) and is kept; if the same code
    already has an earlier PASSED attempt, warn that the retake will count
    as Extra (design/09 "Repeated courses / Extra") once graded.

    Session codes ("20249" < "20251" < "20255") order chronologically as
    strings, so plain comparison works; rows missing a session are never
    collapsed (conservative -- better a visible duplicate than silent loss).
    """
    kept: list[DraftCourse] = []
    for course in courses:
        if course.grade == "IPR" and course.session:
            completed_later = any(
                other is not course
                and other.code == course.code
                and other.grade != "IPR"
                and other.session
                and other.session > course.session
                for other in courses
            )
            if completed_later:
                continue  # in-progress snapshot of a registration that later completed

            passed_earlier = any(
                other is not course
                and other.code == course.code
                and other.status == "completed"
                and other.session
                and other.session < course.session
                and (
                    (other.grade or "").upper() in PASSING_LETTERS_AND_NOTATIONS
                    or (other.mark is not None and other.mark >= 50)
                )
                for other in courses
            )
            if passed_earlier:
                warnings.append(
                    f"{course.code} in {_session_label(course.session)} looks like a "
                    "retake of a course you already passed; per UofT's repeated-course "
                    "rule it will count as Extra (no credit, not in your GPA) once "
                    "graded."
                )
        kept.append(course)
    return kept


def parse_pdf_text(text: str) -> StudentRecordDraft:
    """Pure line-scan over already-extracted PDF text. See module docstring
    for the heuristic and why it's line-oriented rather than column-fixed,
    and for how a per-session ACORN section heading ("2025 Fall - ...") is
    tracked as a fallback session for the course rows underneath it."""
    if not text or not text.strip():
        raise DegreeExplorerParseError("No text to parse.")

    programs: list[DraftProgram] = []
    courses: list[DraftCourse] = []
    warnings: list[str] = []
    cgpa: float | None = None
    seen_program_codes: set[str] = set()
    current_session = ""  # last-seen ACORN session-section heading, if any
    last_was_course = False  # for wrapped-title continuation lines

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            last_was_course = False
            continue

        if is_session_heading(line):
            current_session = normalize_session(line)
            last_was_course = False
            continue

        cgpa_m = _CGPA_RE.search(line)
        if cgpa_m:
            cgpa = float(cgpa_m.group(1))
            last_was_course = False
            continue

        # A line can only be ONE of a program line or a course line -- program
        # codes (AS...) and course codes never co-occur on the same real line.
        program = _parse_program_line(line)
        if program is not None:
            if program.code not in seen_program_codes:
                seen_program_codes.add(program.code)
                programs.append(program)
            last_was_course = False
            continue

        course = _parse_course_line(line, default_session=current_session)
        if course is not None:
            courses.append(course)
            last_was_course = True
            continue

        # A bare-words line directly under a course row is that row's wrapped
        # title continuing ("...Justice in the" / "Indo-Pacific").
        if last_was_course and courses and _TITLE_CONTINUATION_RE.match(line):
            prev = courses[-1]
            courses[-1] = replace(prev, title=f"{prev.title} {line}".strip())
            continue
        last_was_course = False

    courses = _collapse_ipr_snapshots(courses, warnings)

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
