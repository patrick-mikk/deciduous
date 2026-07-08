"""Parsing for UofT course codes (e.g. "POL208H1") and program codes
(e.g. "ASMAJ1305A").

Course code shape: SSSNNNCc[T] where
    SSS  3-letter subject designator ("POL")
    NNN  3-digit course number ("208") -> level = first digit * 100
    C    credit-weight letter, H (0.5) or Y (1.0)
    c    campus digit (1 = St. George, 3 = UTM, 5 = UTSC, ...)
    T    optional trailing section/term letter some sources append (F/S/Y)

Program code shape: AS + 3-letter type + 4-digit subject [+ stream letter]
    e.g. "ASMAJ1305A" -> type=major, subject="1305", stream="A"
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_COURSE_CODE_RE = re.compile(
    r"^(?P<subject>[A-Z]{3})(?P<number>\d{3})(?P<credit>[HY])(?P<campus>\d)(?P<extra>[A-Z]?)$"
)

_PROGRAM_CODE_RE = re.compile(
    r"^AS(?P<type>SPE|MAJ|MIN|FOC|CER)(?P<subject>\d{4})(?P<stream>[A-Z]?)$"
)

_PROGRAM_TYPE_BY_PREFIX = {
    "SPE": "specialist",
    "MAJ": "major",
    "MIN": "minor",
    "FOC": "focus",
    "CER": "certificate",
}


@dataclass(frozen=True)
class CourseCode:
    raw: str
    subject: str
    number: str
    credit_suffix: str
    campus: str
    extra: str = ""

    @property
    def level(self) -> int:
        """The course's level bucket: 100/200/300/400 (from the leading digit)."""
        return int(self.number[0]) * 100

    @property
    def credit_value(self) -> float:
        return 1.0 if self.credit_suffix.upper() == "Y" else 0.5


@dataclass(frozen=True)
class ProgramCode:
    raw: str
    program_type: str  # "specialist" | "major" | "minor" | "focus" | "certificate"
    subject: str  # 4-digit subject designator, e.g. "1305"
    stream: str = ""  # "A"/"B"/"C" suffix, if present


def parse_course_code(code: str) -> CourseCode | None:
    """Parse a course code like "POL208H1". Returns None if unparseable
    (e.g. free-text prerequisite fragments that aren't course codes)."""
    if not code:
        return None
    match = _COURSE_CODE_RE.match(code.strip().upper())
    if not match:
        return None
    return CourseCode(
        raw=code.strip().upper(),
        subject=match.group("subject"),
        number=match.group("number"),
        credit_suffix=match.group("credit"),
        campus=match.group("campus"),
        extra=match.group("extra") or "",
    )


def parse_program_code(code: str) -> ProgramCode | None:
    """Parse a program (POSt) code like "ASMAJ1305A". Returns None if it
    doesn't match the AS<type><subject>[stream] shape (e.g. non-ArtSci codes)."""
    if not code:
        return None
    match = _PROGRAM_CODE_RE.match(code.strip().upper())
    if not match:
        return None
    return ProgramCode(
        raw=code.strip().upper(),
        program_type=_PROGRAM_TYPE_BY_PREFIX[match.group("type")],
        subject=match.group("subject"),
        stream=match.group("stream") or "",
    )
