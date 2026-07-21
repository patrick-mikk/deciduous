"""Unit tests for `backend/ingest/degree_explorer.py`'s PDF-text parsing path.

No real PDF is available in this sandbox (see that module's docstring
"ASSUMPTIONS THAT STILL NEED VALIDATION AGAINST A REAL ACORN PDF"), so these
fixtures are hand-written text meant to mirror the *layout* of a real ACORN
Academic History PDF as closely as this codebase's authors could determine
without one: a header block, "Program(s) of Study" lines, per-session
section headings ("2022 Fall" / "Fall 2022" -- both orderings are handled,
see the module docstring), course rows under each heading, and a trailing
GPA/credit summary. `extract_pdf_text` (the only function that actually
touches pdfplumber) is exercised separately and only against its error
paths, since building a real PDF isn't something this suite should need a
PDF-writing dependency for (see backend/requirements.txt: only pdfplumber
was added, no PDF-authoring library).
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest  # noqa: E402

from backend.ingest.degree_explorer import (  # noqa: E402
    DegreeExplorerParseError,
    extract_pdf_text,
    is_session_heading,
    normalize_session,
    parse_pdf_text,
)

# --------------------------------------------------------------------------
# Synthetic ACORN Academic History text, year-first headings ("2022 Fall"),
# the ordering the user-facing bug report says ACORN commonly uses.
# --------------------------------------------------------------------------
ACORN_YEAR_FIRST = """
UNIVERSITY OF TORONTO
Academic History

Name: Jordan Sample
Student Number: 1000123456

Program(s) of Study

Specialist - Computer Science ASSPE1689
Minor - Mathematics ASMIN1350

2022 Fall

CSC108H1 Introduction to Computer Programming 0.50 85 A
MAT137Y1 Calculus with Proofs 1.00 IPR

Sessional GPA: 3.70

2023 Winter

CSC148H1 Introduction to Computer Science 0.50 78 B+
STA220H1 The Practice of Statistics I 0.50 CR

Sessional GPA: 3.30

Cumulative G.P.A.: 3.52
"""

# Same content, but with the section headings in "Fall 2022" (term-first)
# order -- the ordering the *original* Degree Explorer-oriented parser's
# `_SESSION_LABEL_RE` already supported, kept working here for backward
# compatibility.
ACORN_TERM_FIRST = ACORN_YEAR_FIRST.replace("2022 Fall", "Fall 2022").replace(
    "2023 Winter", "Winter 2023"
)

# Regression fixture: the *original* heuristic's assumption -- every course
# row carries its own inline session mention, no section headings at all.
# This must keep parsing correctly since it's the "Degree Explorer-style
# export" shape the parser was originally written against.
INLINE_SESSION_STYLE = """
Specialist - Computer Science ASSPE1689

CSC108H1 Introduction to Computer Programming Fall 2022 0.50 85 A
CSC148H1 Introduction to Computer Science Winter 2023 0.50 78 B+

Cumulative G.P.A.: 3.60
"""


def test_acorn_year_first_headings_apply_to_courses_under_them():
    draft = parse_pdf_text(ACORN_YEAR_FIRST)

    by_code = {c.code: c for c in draft.courses}
    assert set(by_code) == {"CSC108H1", "MAT137Y1", "CSC148H1", "STA220H1"}

    assert by_code["CSC108H1"].session == "20229"  # 2022 Fall
    assert by_code["MAT137Y1"].session == "20229"
    assert by_code["CSC148H1"].session == "20231"  # 2023 Winter
    assert by_code["STA220H1"].session == "20231"


def test_acorn_year_first_extracts_title_mark_grade_status():
    draft = parse_pdf_text(ACORN_YEAR_FIRST)
    by_code = {c.code: c for c in draft.courses}

    csc108 = by_code["CSC108H1"]
    assert csc108.title == "Introduction to Computer Programming"
    assert csc108.mark == 85.0
    assert csc108.grade == "A"
    assert csc108.status == "completed"
    assert csc108.credits == 0.5  # derived from the course code, not the "0.50" text

    mat137 = by_code["MAT137Y1"]
    assert mat137.grade == "IPR"
    assert mat137.status == "in_progress"
    assert mat137.mark is None
    assert mat137.credits == 1.0

    sta220 = by_code["STA220H1"]
    assert sta220.title == "The Practice of Statistics I"
    assert sta220.grade == "CR"
    assert sta220.mark is None
    assert sta220.status == "completed"


def test_acorn_year_first_extracts_programs_and_cgpa():
    draft = parse_pdf_text(ACORN_YEAR_FIRST)

    codes = {p.code for p in draft.programs}
    assert codes == {"ASSPE1689", "ASMIN1350"}
    titles = {p.code: p.title for p in draft.programs}
    assert titles["ASSPE1689"] == "Computer Science"
    assert titles["ASMIN1350"] == "Mathematics"

    assert draft.cgpa == 3.52
    assert draft.warnings == []


def test_acorn_term_first_headings_also_work():
    """"Fall 2022" ordering (term-first) parses identically to "2022 Fall"."""
    draft_year_first = parse_pdf_text(ACORN_YEAR_FIRST)
    draft_term_first = parse_pdf_text(ACORN_TERM_FIRST)

    sessions_year_first = {c.code: c.session for c in draft_year_first.courses}
    sessions_term_first = {c.code: c.session for c in draft_term_first.courses}
    assert sessions_year_first == sessions_term_first


def test_inline_session_per_course_row_still_works():
    """Backward compatibility: a course row that mentions its own session
    inline (no section heading above it) still gets that session -- this is
    the original Degree Explorer-oriented heuristic's assumption."""
    draft = parse_pdf_text(INLINE_SESSION_STYLE)
    by_code = {c.code: c for c in draft.courses}

    assert by_code["CSC108H1"].session == "20229"
    assert by_code["CSC148H1"].session == "20231"
    assert draft.cgpa == 3.60


def test_course_without_any_session_falls_back_to_empty_string():
    text = "CSC108H1 Introduction to Computer Programming 0.50 85 A"
    draft = parse_pdf_text(text)
    assert len(draft.courses) == 1
    assert draft.courses[0].session == ""


# --------------------------------------------------------------------------
# normalize_session / is_session_heading -- both orderings, and negatives.
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "text,expected",
    [
        ("Fall 2022", "20229"),
        ("2022 Fall", "20229"),
        ("Winter 2023", "20231"),
        ("2023 Winter", "20231"),
        ("Summer 2024", "20245"),
        ("2024 Summer", "20245"),
        ("no session mentioned here", ""),
    ],
)
def test_normalize_session_both_orderings(text, expected):
    assert normalize_session(text) == expected


@pytest.mark.parametrize(
    "line",
    [
        "2022 Fall",
        "Fall 2022",
        "2022 Fall Session",
        "Fall 2022 Term",
        "2022 Fall:",
        "  Winter 2023  ",
    ],
)
def test_is_session_heading_true_for_bare_heading_lines(line):
    assert is_session_heading(line) is True


@pytest.mark.parametrize(
    "line",
    [
        "CSC108H1 Introduction to Computer Programming 0.50 85 A",
        "Sessional GPA: 3.70 for Fall 2022",
        "Cumulative G.P.A.: 3.52",
        "Specialist - Computer Science ASSPE1689",
        "",
    ],
)
def test_is_session_heading_false_for_non_heading_lines(line):
    assert is_session_heading(line) is False


# --------------------------------------------------------------------------
# Error paths -- empty input, and the pdfplumber-facing `extract_pdf_text`.
# --------------------------------------------------------------------------
def test_parse_pdf_text_rejects_empty_input():
    with pytest.raises(DegreeExplorerParseError):
        parse_pdf_text("")
    with pytest.raises(DegreeExplorerParseError):
        parse_pdf_text("   \n\n  ")


def test_parse_pdf_text_with_no_recognisable_lines_warns_instead_of_erroring():
    draft = parse_pdf_text("This PDF has no course or program lines in it at all.")
    assert draft.courses == []
    assert draft.programs == []
    assert draft.warnings  # non-empty: "couldn't find any recognisable..."


def test_extract_pdf_text_rejects_non_pdf_bytes():
    """A missing/corrupt PDF must raise `DegreeExplorerParseError` (which
    `backend/api/import_.py` maps to a clean 422 JSON error), never let a
    pdfplumber exception escape as a 500."""
    with pytest.raises(DegreeExplorerParseError):
        extract_pdf_text(b"this is not a pdf file at all")


def test_extract_pdf_text_rejects_empty_bytes():
    with pytest.raises(DegreeExplorerParseError):
        extract_pdf_text(b"")
