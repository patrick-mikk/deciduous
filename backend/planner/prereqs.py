"""Prerequisite / corequisite / exclusion satisfaction from parsed free text.

TTB's `cmCourseInfo.prerequisitesText`/`corequisitesText`/`exclusionsText` are
HTML free text with an informal boolean grammar
(`backend/docs/TTB_API_REFERENCE.md`):

    "(MAT223H1,MAT224H1)/ MAT247H1"
        -> (MAT223H1 AND MAT224H1) OR MAT247H1

Convention (consistent across this whole module):
    ","  and  ";"  and the word "and"   -> AND (all required)
    "/"  and the word "or"              -> OR  (any one required)
    "( … )"                             -> grouping
Anything else (narrative text with no recognizable course code, e.g.
"permission of the instructor") becomes a `FreeText` leaf: it can't be
verified programmatically, so it evaluates as satisfied but is reported back
so the caller can surface it as "unverified — check manually", matching the
existing convention in `backend/api/plan.py`'s `_extract_code_groups`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from backend.data_sources.http import strip_html
from backend.planner.types import CourseRecord, CourseRequirementText, Issue

# Same course-code shape as `planner.course_code`, but as a plain findall
# pattern (course codes appear embedded in running prose here).
_COURSE_CODE_RE = re.compile(r"\b[A-Z]{3}\d{3}[HY]\d\b")

_TOKEN_RE = re.compile(
    r"""
    (?P<code>[A-Z]{3}\d{3}[HY]\d)
    | (?P<lparen>\()
    | (?P<rparen>\))
    | (?P<and_sep>[,;]|\band\b)
    | (?P<or_sep>/|\bor\b)
    """,
    re.VERBOSE | re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Expression tree
# ---------------------------------------------------------------------------


class Requirement:
    """Base class for a parsed prerequisite/corequisite/exclusion expression."""


@dataclass(frozen=True)
class CourseRef(Requirement):
    code: str


@dataclass(frozen=True)
class FreeText(Requirement):
    """Narrative text with no extractable course code — can't be verified."""

    text: str


@dataclass(frozen=True)
class And(Requirement):
    children: tuple[Requirement, ...]


@dataclass(frozen=True)
class Or(Requirement):
    children: tuple[Requirement, ...]


@dataclass(frozen=True)
class Empty(Requirement):
    """No requirement at all (empty/blank source text)."""


EMPTY = Empty()


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


@dataclass
class _Token:
    kind: str  # "code" | "lparen" | "rparen" | "and" | "or" | "text"
    value: str


def _tokenize(text: str) -> list[_Token]:
    tokens: list[_Token] = []
    pos = 0
    for match in _TOKEN_RE.finditer(text):
        if match.start() > pos:
            gap = text[pos : match.start()].strip(" \t\n\r.")
            if gap:
                tokens.append(_Token("text", gap))
        if match.group("code"):
            tokens.append(_Token("code", match.group("code").upper()))
        elif match.group("lparen"):
            tokens.append(_Token("lparen", "("))
        elif match.group("rparen"):
            tokens.append(_Token("rparen", ")"))
        elif match.group("and_sep"):
            tokens.append(_Token("and", match.group("and_sep")))
        elif match.group("or_sep"):
            tokens.append(_Token("or", match.group("or_sep")))
        pos = match.end()
    tail = text[pos:].strip(" \t\n\r.")
    if tail:
        tokens.append(_Token("text", tail))
    return tokens


class _Parser:
    """Recursive-descent parser. Grammar (OR binds loosest):

        or_expr   := and_expr (OR and_expr)*
        and_expr  := atom (AND atom)*
        atom      := '(' or_expr ')' | CODE | TEXT

    Stray/unbalanced parens and empty groups degrade gracefully rather than
    raising — this is free text scraped from HTML, not a formal grammar.
    """

    def __init__(self, tokens: list[_Token]) -> None:
        self._tokens = tokens
        self._pos = 0

    def _peek(self) -> _Token | None:
        return self._tokens[self._pos] if self._pos < len(self._tokens) else None

    def _advance(self) -> _Token | None:
        tok = self._peek()
        if tok is not None:
            self._pos += 1
        return tok

    def parse(self) -> Requirement:
        if not self._tokens:
            return EMPTY
        expr = self._or_expr()
        return expr if expr is not None else EMPTY

    def _or_expr(self) -> Requirement | None:
        parts = [self._and_expr()]
        while self._peek() is not None and self._peek().kind == "or":
            self._advance()
            parts.append(self._and_expr())
        parts = [p for p in parts if p is not None]
        if not parts:
            return None
        return parts[0] if len(parts) == 1 else Or(tuple(parts))

    def _and_expr(self) -> Requirement | None:
        parts = [self._atom()]
        while self._peek() is not None and self._peek().kind == "and":
            self._advance()
            nxt = self._atom()
            if nxt is not None:
                parts.append(nxt)
        parts = [p for p in parts if p is not None]
        if not parts:
            return None
        return parts[0] if len(parts) == 1 else And(tuple(parts))

    def _atom(self) -> Requirement | None:
        tok = self._peek()
        if tok is None:
            return None
        if tok.kind == "lparen":
            self._advance()
            inner = self._or_expr()
            if self._peek() is not None and self._peek().kind == "rparen":
                self._advance()
            return inner
        if tok.kind == "rparen":
            # Unbalanced close paren with nothing open — stop this atom.
            return None
        if tok.kind == "code":
            self._advance()
            return CourseRef(tok.value)
        if tok.kind == "text":
            self._advance()
            return FreeText(tok.value)
        # Stray separator token where an atom was expected: skip it.
        self._advance()
        return None


def parse_requirement(text: str | None) -> Requirement:
    """Parse prerequisite/corequisite/exclusion free text (HTML or plain)
    into a `Requirement` boolean-expression tree. Returns `EMPTY` for
    blank/whitespace-only input."""
    if not text:
        return EMPTY
    plain = strip_html(text)
    if not plain:
        return EMPTY
    tokens = _tokenize(plain)
    return _Parser(tokens).parse()


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def referenced_codes(node: Requirement) -> frozenset[str]:
    """Every course code appearing anywhere in the expression, flattened."""
    if isinstance(node, CourseRef):
        return frozenset({node.code})
    if isinstance(node, (And, Or)):
        out: set[str] = set()
        for child in node.children:
            out |= referenced_codes(child)
        return frozenset(out)
    return frozenset()


def has_unverifiable_text(node: Requirement) -> bool:
    """True if any part of the expression couldn't be reduced to course
    codes (narrative conditions like "permission of the instructor")."""
    if isinstance(node, FreeText):
        return True
    if isinstance(node, (And, Or)):
        return any(has_unverifiable_text(child) for child in node.children)
    return False


def evaluate(node: Requirement, satisfied_codes: frozenset[str] | set[str]) -> bool:
    """True if `node` is satisfied given the set of course codes considered
    "held" (already completed/in-progress, or in-progress-planned for a
    corequisite, or "present in the plan" for an exclusion check).

    `FreeText` leaves and `Empty` both evaluate `True` — nothing to check
    programmatically, so they never block a course; callers that want to flag
    them for manual review should also check `has_unverifiable_text`.
    """
    if isinstance(node, Empty):
        return True
    if isinstance(node, FreeText):
        return True
    if isinstance(node, CourseRef):
        return node.code in satisfied_codes
    if isinstance(node, And):
        return all(evaluate(child, satisfied_codes) for child in node.children)
    if isinstance(node, Or):
        return any(evaluate(child, satisfied_codes) for child in node.children)
    raise TypeError(f"Unknown Requirement node: {node!r}")  # pragma: no cover


def missing_alternatives(node: Requirement, satisfied_codes: frozenset[str] | set[str]) -> list[frozenset[str]]:
    """When `evaluate(node, satisfied_codes)` is False, return the smallest
    set of course-code alternatives that *would* satisfy it — one
    `frozenset[str]` per viable option (each itself a set of codes that must
    ALL be added together). Empty list if already satisfied, or if the
    expression is empty/unverifiable-only (nothing structured to suggest)."""
    if evaluate(node, satisfied_codes):
        return []
    return _unsatisfied_options(node, satisfied_codes)


def _unsatisfied_options(node: Requirement, satisfied: frozenset[str] | set[str]) -> list[frozenset[str]]:
    if isinstance(node, (Empty, FreeText)):
        return []
    if isinstance(node, CourseRef):
        return [] if node.code in satisfied else [frozenset({node.code})]
    if isinstance(node, Or):
        options: list[frozenset[str]] = []
        for child in node.children:
            options.extend(_unsatisfied_options(child, satisfied))
        return options
    if isinstance(node, And):
        # Every unmet child must ALL be added; combine into one option set
        # (the cross-product across children, unioned per child's own
        # cheapest option — good enough for the common case of small ANDs).
        combined: set[str] = set()
        for child in node.children:
            child_options = _unsatisfied_options(child, satisfied)
            if child_options:
                combined |= min(child_options, key=len)
        return [frozenset(combined)] if combined else []
    return []  # pragma: no cover


# ---------------------------------------------------------------------------
# Convenience wrappers matching the three concrete checks
# ---------------------------------------------------------------------------


def prerequisite_met(prerequisites_text: str | None, completed_codes: frozenset[str] | set[str]) -> bool:
    """Has the prerequisite requirement been met by already-completed (or
    in-progress, per calendar convention) courses?"""
    return evaluate(parse_requirement(prerequisites_text), completed_codes)


def corequisite_met(
    corequisites_text: str | None,
    completed_codes: frozenset[str] | set[str],
    concurrent_codes: frozenset[str] | set[str],
) -> bool:
    """Has the corequisite requirement been met by courses completed earlier
    OR being taken in the same term as the course in question?"""
    return evaluate(parse_requirement(corequisites_text), set(completed_codes) | set(concurrent_codes))


def excluded_conflict(exclusions_text: str | None, other_owned_codes: frozenset[str] | set[str]) -> frozenset[str]:
    """Which of `other_owned_codes` (every other course the student has
    completed/is taking/has planned) trip this course's exclusion text.
    Exclusion lists are simple code sets joined by separators (no real AND
    semantics in practice), so this is `referenced_codes(...) & owned`."""
    node = parse_requirement(exclusions_text)
    return referenced_codes(node) & frozenset(other_owned_codes)


# ---------------------------------------------------------------------------
# Whole-plan orchestration: check every planned CourseRecord's prereqs/
# coreqs/exclusions against the rest of the transcript + plan.
# ---------------------------------------------------------------------------


def _session_bounds(session: str) -> tuple[int, int]:
    def _to_int(value: str) -> int:
        try:
            return int(value)
        except ValueError:
            return 0

    parts = [p for p in session.split("-") if p]
    if not parts:
        return (0, 0)
    return (_to_int(parts[0]), _to_int(parts[-1]))


def session_strictly_before(a_session: str, b_session: str) -> bool:
    """True if every part of `a_session` ends before `b_session` begins —
    e.g. Fall 2026 ("20269") is strictly before Winter 2027 ("20271")."""
    _, a_end = _session_bounds(a_session)
    b_start, _ = _session_bounds(b_session)
    return a_end < b_start


def validate_plan_prerequisites(
    records: list[CourseRecord], course_texts: dict[str, CourseRequirementText]
) -> list[Issue]:
    """For every `planned` record, check its prerequisite/corequisite text
    against courses completed/in-progress or planned in an earlier term, its
    corequisite text against that set plus same-term planned courses, and
    its exclusion text against every other owned course. Courses with no
    entry in `course_texts` (not cached/known) are skipped — "can't verify"
    is not "failed", matching `backend/api/plan.py`'s existing convention.
    """
    issues: list[Issue] = []
    all_codes = {r.code_norm for r in records if r.status != "extra"}

    for record in records:
        if record.status != "planned":
            continue
        info = course_texts.get(record.code_norm)
        if info is None:
            continue

        prior_codes = {
            other.code_norm
            for other in records
            if other.code_norm != record.code_norm
            and (
                other.status in ("completed", "in_progress")
                or (
                    other.status == "planned"
                    and other.session
                    and record.session
                    and session_strictly_before(other.session, record.session)
                )
            )
        }
        concurrent_codes = {
            other.code_norm
            for other in records
            if other.code_norm != record.code_norm
            and other.status == "planned"
            and other.session
            and record.session
            and other.session == record.session
        }

        prereq_tree = parse_requirement(info.prerequisites)
        if not evaluate(prereq_tree, prior_codes):
            issues.append(
                Issue(
                    "error",
                    "prerequisite",
                    f"{record.code}: prerequisite not met.",
                    course_code=record.code,
                )
            )

        coreq_tree = parse_requirement(info.corequisites)
        if not evaluate(coreq_tree, prior_codes | concurrent_codes):
            issues.append(
                Issue(
                    "error",
                    "corequisite",
                    f"{record.code}: corequisite not met.",
                    course_code=record.code,
                )
            )

        conflicts = excluded_conflict(info.exclusions, all_codes - {record.code_norm})
        if conflicts:
            issues.append(
                Issue(
                    "error",
                    "exclusion",
                    f"{record.code} cannot be taken with {', '.join(sorted(conflicts))} (exclusion).",
                    course_code=record.code,
                )
            )

    return issues
