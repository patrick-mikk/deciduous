"""Academic Calendar program/program-requirements client.

Endpoint: ``GET https://artsci.calendar.utoronto.ca/search-programs``
(server-rendered Drupal HTML; params: ``combine``, ``type``,
``field_subject_area_prog_search_value``, ``page``).

Each program is a ``div.views-row`` whose accordion header
(``h3.js-views-accordion-group-header``) reads "Program Title - CODE", e.g.
"Geographic Data Science Major: Human Systems Stream (Science Program) -
ASMAJ1305A". The row nests a second ``div.views-row`` carrying the field markup:

- ``.views-field-title .field-content``                         full title
- ``.views-field-field-section-link a``                         department name + href
- ``.views-field-field-enrolment-requirements``                 enrolment text
- ``.views-field-field-completion-requirements .field-content`` the requirement groups

Completion requirements are **grouped**, but the grouping is expressed
inconsistently across programs. A single program can mix ``<ol><li>`` lists,
``<p>`` section headers ("First Year:", "Notes:"), bold/italic group titles
("Group A: ...", "*Cluster A - ..."), numbered items ("1." "2." ... as plain
text, sometimes several concatenated in one ``<p>``), and - critically - a
header sitting **inline with its own course list** in the very same block
("Group A: Social, Political and Economic Topics (Social Science) AFR389H1,
CAS200H1, ..."), so a header cannot be recognised just because a block is
free of course codes.

`parse_completion_requirements` segments this into `RequirementGroup`s with a
two-stage, keyword + structure driven approach:

1. **Line flattening** (`_flatten_lines`): every ``<p>``/``<li>`` block is
   split on ``<br/>`` into separate "lines" (recursing through nested/
   malformed ``<ol>``/``<ul>``), so a header that sits on its own line before
   a ``<br/>``-separated course list is already isolated from that list.
2. **Leading-label extraction** (`_extract_header`): for each line, peel a
   header label off its *leading* text/markup - a leading bold/italic run, a
   leading "N." numbered marker, or a plain-text phrase (ordinal year,
   "Group X", a short Title-Case phrase before ':') - even when the
   remainder of the line still carries course codes or credit phrases. That
   remainder becomes the new group's first rule instead of disqualifying the
   whole block from being a header.

Every course code that is not itself part of a recognised label lands under
some `RequirementGroup` via `RequirementRule`; parsing is pure (no network),
`search()` is the only network entry.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from backend.data_sources.http import get_html, strip_html
from backend.data_sources.models import Program, RequirementGroup, RequirementRule

SEARCH_URL = "https://artsci.calendar.utoronto.ca/search-programs"

# Program codes: "AS" + 3-letter type prefix + 3-4 digits + optional stream letter.
_PROGRAM_CODE_RE = re.compile(r"\bAS[A-Z]{3}\d{3,4}[A-Z]?\b")

# Course codes across ALL campuses/joint depts: 3 letters, then an alphanumeric
# (digit for St George, a level-letter A-D for UTSC), 2 digits, H/Y, campus digit.
# Matches POL208H1, MAT133Y1, ANTC35H3 (UTSC), ANT418H5 (UTM), ARH306Y0 (abroad).
_COURSE_CODE_RE = re.compile(r"\b[A-Z]{3}[A-Z0-9]\d{2}[HY]\d\b")

# A credit weight anywhere in a line, e.g. "0.5 credit", "1.5 credits".
_CREDITS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*credits?")

# The program-total intro. Accepts "(14.5 credits)", "A total of 10.0
# credits...", "Total: 2.0 credits...", or a bare "3.5 credits" - the leading
# '(' and "total"/"a total of" wording are optional; only the credit number
# itself is required, anchored at the very start of the text.
_TOTAL_CREDITS_RE = re.compile(
    r"^\(?\s*(?:total\s*:?\s*)?(?:a\s+total\s+of\s*)?(\d+(?:\.\d+)?)\s*credits?\b",
    re.IGNORECASE,
)

_PROGRAM_TYPE_BY_PREFIX = {
    "ASSPE": "specialist",
    "ASMAJ": "major",
    "ASMIN": "minor",
}


def _program_type_from_code(code: str) -> str:
    """Map a program code's 5-char prefix (e.g. "ASMAJ") to a program_type."""
    return _PROGRAM_TYPE_BY_PREFIX.get(code[:5], "")


def _dedupe(items: list[str]) -> list[str]:
    """Return `items` with duplicates removed, preserving first-seen order."""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _codes_in(text: str) -> list[str]:
    """All course codes in `text`, deduped in first-seen order."""
    return _dedupe(_COURSE_CODE_RE.findall(text))


def _first_credit(text: str) -> float:
    """The first credit weight in `text`, or 0.0 if none is stated."""
    match = _CREDITS_RE.search(text)
    return float(match.group(1)) if match else 0.0


# --------------------------------------------------------------------------
# Header taxonomy: smart-keyword regexes used to recognise a *leading* label,
# whether or not the rest of the line also carries course codes/credits.
# --------------------------------------------------------------------------

# Ordinal-year / "higher years" headers, with an optional leading "In " and
# an optional trailing "or higher"/"and higher" (e.g. "In first year or
# higher (1.0 credit):"), and comma-joined forms ("Second, third, and fourth
# years").
_YEAR_PHRASE_RE = re.compile(
    r"^(?:in\s+)?"
    r"(?:(?:first|second|third|fourth|fifth|higher|upper|lower|later)"
    r"(?:\s*,\s*(?:first|second|third|fourth|fifth))*"
    r"(?:\s+(?:and|or)\s+(?:first|second|third|fourth|fifth))?)"
    r"\s+years?\b"
    r"(?:\s+(?:or|and)\s+(?:higher|above))?",
    re.IGNORECASE,
)

# Named-group / section-label headers: "Group A", "Cluster A", "Stream 1",
# "Geographic Area a)", etc. Anchored at the start of the line so a rule that
# merely *references* a group ("1.5 credits from Group A") never matches. The
# optional short identifier right after the keyword ("A", "1", "IV") is
# consumed by the SAME match so a colon-less, unbolded header like "Group A
# (Ethics)" keeps its identifier in the label instead of truncating to the
# bare word "Group" (`_split_at_label_end` only extends past what this regex
# already matched).
_GROUP_PHRASE_RE = re.compile(
    r"^(?:group|cluster|stream|category|list|option|table)\b(?:\s+[A-Za-z0-9]{1,3}\b)?"
    r"|^geographic\s+area\b",
    re.IGNORECASE,
)

# A lettered/roman sub-item marker ("a)", "(b)", "iv)") - these are SUB-items
# of the enclosing rule, never a new group heading.
_LETTERED_MARKER_RE = re.compile(r"^\(?[a-z]\)\s+|^\(?[ivx]{1,4}\)\s+", re.IGNORECASE)

# A leading numbered marker, e.g. "1. " or "12. ".
_LEADING_NUM_RE = re.compile(r"^(\d{1,2})\.\s+")

# Any numbered item marker inside a line (needs a trailing space so it does
# not fire inside "0.5" or "4.0 credits").
_NUM_ITEM_RE = re.compile(r"(?:(?<=\s)|^)(\d{1,2})\.\s+")

# Stopwords ignored when checking whether a candidate label reads as a
# Title-Case phrase (allowed to stay lowercase mid-phrase).
_TITLE_STOPWORDS = {
    "and", "or", "of", "the", "in", "for", "to", "a", "an", "&", "at", "from",
    "with", "on", "by", "as",
}

# Common label nouns the Calendar's own authors inconsistently leave
# lowercase even in an otherwise Title-Case header ("Required courses:",
# "Introductory courses:" vs "Suggested Related Courses:"). Exempt them from
# the capitalization check the same way stopwords are exempted, so a header
# is not rejected just because its last word happens to be lowercase in the
# source; the OTHER significant word(s) still must be capitalized.
_TITLE_LOWERCASE_OK = {
    "course", "courses", "credit", "credits", "requirement", "requirements",
    "elective", "electives",
}

# Leading words that mark a colon-terminated fragment as a RULE ("From Group
# A: ...", "0.5 credit from:", "At least 1.0 credit from Group A -- ...")
# rather than a header, even when the fragment happens to be Title-Case.
_DENY_LEAD_WORDS = {
    "from", "any", "at", "up", "no", "one", "two", "three", "four", "five",
    "six", "choose", "select", "complete", "completion", "remaining",
    "students", "note", "please", "see", "this", "these", "all", "each",
    "every", "your", "you",
}

# Extra lead words denied ONLY for a colon-LESS candidate reached through
# `_plain_header_label`'s `allow_no_colon_titlecase` fallback (numbered items
# with no colon at all). A bare "N. 1.5 credits from Group A" is a rule that
# merely REFERENCES a pool defined elsewhere, not a header defining one - it
# must stay a plain numbered rule alongside its sibling numbered rules ("N.
# 1.0 credit from CAS100H1...", "N. CAS400H1"). This is intentionally NOT
# folded into `_DENY_LEAD_WORDS` itself: a colon-having header like "1.5
# credits from Methods Courses:" (candidate ends right before its own colon,
# with the actual course list as the body) is a legitimate, common heading
# shape across the catalog and must keep working.
_DENY_LEAD_WORDS_NO_COLON = _DENY_LEAD_WORDS | {"credit", "credits"}

# Inline tags treated as bold/heading markers - <em> is used interchangeably
# with <strong>/<b> for group/note labels across the Calendar.
_BOLD_TAGS = ("strong", "b", "em")
_CONNECTOR_ONLY = {"or", "and", "or/and", "and/or", "&"}
_BARE_NUM_RE = re.compile(r"^\d{1,2}\.?$")


def _is_titlecase_phrase(phrase: str) -> bool:
    """True if every non-stopword "word" in `phrase` starts with a capital.

    Tokenizes on whitespace (not letter-runs) so a hyphenated compound like
    "Fourth-year" is judged as ONE unit by its leading segment ("Fourth"),
    matching the Calendar's own convention of capitalizing only the first
    half of such a compound - splitting on the old letters-only regex would
    otherwise see "Fourth" and a bare lowercase "year" as two separate
    words and wrongly fail the phrase.
    """
    raw_words = phrase.split()
    words = [re.sub(r"^[^A-Za-z]+|[^A-Za-z']+$", "", w) for w in raw_words]
    words = [w for w in words if w]
    if not words or len(words) > 12:
        return False

    def lead(word: str) -> str:
        return word.split("-", 1)[0]

    significant = [
        w for w in words
        if lead(w).lower() not in _TITLE_STOPWORDS and lead(w).lower() not in _TITLE_LOWERCASE_OK
    ]
    if not significant:
        return False
    return all(lead(w)[0].isupper() for w in significant)


def _looks_like_label_text(candidate: str, deny_words: frozenset[str] = frozenset()) -> bool:
    """True if `candidate` reads like an ad hoc department/category label.

    Positive signal: short, Title-Case, not a course code, and not led by a
    rule-verb ("from", "any", "at least", ...) or a lettered sub-marker.
    `deny_words` adds extra context-specific lead words to reject (see
    `_DENY_LEAD_WORDS_NO_COLON`) on top of the always-denied `_DENY_LEAD_WORDS`.
    """
    stripped = candidate.strip()
    if not stripped or len(stripped) > 90:
        return False
    if _LETTERED_MARKER_RE.match(stripped):
        return False
    if _COURSE_CODE_RE.search(stripped):
        return False
    words = re.findall(r"[A-Za-z][A-Za-z']*", stripped)
    if not words or words[0].lower() in _DENY_LEAD_WORDS or words[0].lower() in deny_words:
        return False
    return _is_titlecase_phrase(stripped)


def _split_at_label_end(stripped: str, phrase_end: int) -> tuple[str, str]:
    """Extend a matched header phrase to its natural end and split there.

    Absorbs an immediately-following parenthetical ("First Year (1.0
    credit):"), then cuts at the nearest colon within a short window; if
    there is none nearby, the label is just the matched phrase (+
    parenthetical) and everything else is the body.
    """
    rest = stripped[phrase_end:]
    paren_m = re.match(r"\s*\([^)]*\)", rest)
    end = phrase_end + (paren_m.end() if paren_m else 0)
    tail = stripped[end:end + 80]
    colon_pos = tail.find(":")
    if colon_pos != -1:
        label_end = end + colon_pos
        return stripped[:label_end].strip(), stripped[label_end + 1:].strip()
    return stripped[:end].strip(), stripped[end:].strip()


def _plain_header_label(
    text: str, allow_no_colon_titlecase: bool = False
) -> tuple[str, str] | None:
    """Peel a plain-text header label (year/group phrase or Title-Case:) off `text`."""
    stripped = text.strip()
    if not stripped or _LETTERED_MARKER_RE.match(stripped):
        return None

    m = _YEAR_PHRASE_RE.match(stripped) or _GROUP_PHRASE_RE.match(stripped)
    if m is not None:
        return _split_at_label_end(stripped, m.end())

    colon_idx = stripped.find(":")
    if 0 <= colon_idx <= 80:
        candidate = stripped[:colon_idx]
        # A trailing parenthetical ("Year 1 (2.0 credits)", "First Year (1.0
        # credit)") legitimately contains lowercase words ("credits") that
        # would fail the Title-Case check; judge the phrase on the part
        # BEFORE the parenthetical, but keep the whole thing as the label.
        core = candidate
        paren_m = re.search(r"\s*\([^)]*\)\s*$", candidate)
        if paren_m:
            core = candidate[:paren_m.start()]
        if _looks_like_label_text(core):
            return candidate.strip(), stripped[colon_idx + 1:].strip()
        # The text BEFORE the colon already failed as a label (e.g. "2.5
        # credits from" - a pool-credit rule, not a header). Do NOT fall
        # through to the colon-less fallback below and re-scan the WHOLE
        # string INCLUDING the colon and whatever follows it ("2.5 credits
        # from: Group A") - that re-scan sees "Group A" as trailing
        # Title-Case words and wrongly manufactures a header out of a rule
        # that merely references a pool defined elsewhere.
        return None

    if allow_no_colon_titlecase and _looks_like_label_text(
        stripped, deny_words=_DENY_LEAD_WORDS_NO_COLON
    ):
        return stripped.strip(), ""

    return None


def _numbered_header_label(stripped: str) -> tuple[str, str] | None:
    """"2. Second year: PHL271H1..." -> ("2. Second year", "PHL271H1...").

    Only fires when the text *after* the number itself reads as a header
    (year/group phrase, or a short Title-Case label before ':'); a plain
    numbered requirement line ("1. 1.0 credit from CAS100H1...") is left
    alone so it stays a rule, matching the source's own distinction between
    numbered *sections* and numbered *requirement items*.
    """
    m = _LEADING_NUM_RE.match(stripped)
    if not m:
        return None
    inner = stripped[m.end():]
    result = _plain_header_label(inner, allow_no_colon_titlecase=True)
    if result is None:
        return None
    inner_label, body = result
    if not inner_label:
        return None
    return f"{m.group(1)}. {inner_label}", body


def _match_note_prefix(stripped: str) -> tuple[str, str] | None:
    """Recognise a note/footnote lead ("*", "Note 1:", "N.B.", "Please note...").

    Fires on the WHOLE line regardless of whether a course code appears
    later in the same text (a note legitimately citing a course code must
    not be disqualified from note detection).
    """
    m = re.match(r"^(\*+)\s*", stripped)
    if m:
        rest = stripped[m.end():]
        m2 = re.match(r"(notes?)\b\s*(\d*)\s*[:.]?\s*", rest, re.IGNORECASE)
        if m2:
            tag = m2.group(1).capitalize() + (f" {m2.group(2)}" if m2.group(2) else "")
            return f"* {tag}".strip(), rest[m2.end():].strip()
        return "*", rest.strip()

    m = re.match(r"^(notes?)\b\s*(\d*)\s*[:.]?\s*(.*)$", stripped, re.IGNORECASE | re.DOTALL)
    if m:
        label = m.group(1).capitalize() + (f" {m.group(2)}" if m.group(2) else "")
        return label.strip(), m.group(3).strip()

    m = re.match(r"^(n\.b\.)\s*:?\s*(.*)$", stripped, re.IGNORECASE | re.DOTALL)
    if m:
        return "N.B.", m.group(2).strip()

    m = re.match(r"^please\s+note\b[:,]?\s*(.*)$", stripped, re.IGNORECASE | re.DOTALL)
    if m:
        return "Note", m.group(1).strip()

    # Only a BARE "Recommended:"/"Suggested:"/"Optional:" (the keyword is the
    # entire label, colon immediately after it) is a note-style flag. A
    # multi-word title that merely *starts* with one of these words
    # ("Recommended Sequence of Courses:", "Suggested Related Courses:") is a
    # genuine section header, not a note - it must fall through to the
    # bold/plain-header checks below so the WHOLE phrase becomes one label
    # instead of being torn in two at the keyword.
    m = re.match(r"^(suggested|recommended|optional)\s*:\s*(.*)$", stripped, re.IGNORECASE | re.DOTALL)
    if m:
        return m.group(1).capitalize(), m.group(2).strip()

    return None


def _is_note(label: str) -> bool:
    low = label.strip().lower()
    return (
        low.startswith("note") or low.startswith("*") or low.startswith("n.b")
        or low.startswith("suggested") or low.startswith("recommended")
        or low.startswith("optional")
    )


def _leading_bold_label(html_fragment: str, stripped_text: str) -> tuple[str, str] | None:
    """If `html_fragment`'s FIRST node is a <strong>/<b>/<em> run, peel it off.

    Unlike the old "whole block must be bold" check, this only needs the
    *leading* run to be bold/italic; trailing plain text (which may itself
    carry course codes) becomes the body instead of disqualifying the block.
    """
    if "<" not in html_fragment:
        return None
    frag_soup = BeautifulSoup(html_fragment, "html.parser")
    container = frag_soup.body or frag_soup
    nodes = list(container.children)

    idx = 0
    while idx < len(nodes):
        node = nodes[idx]
        if getattr(node, "name", None) is None and not str(node).strip():
            idx += 1
            continue
        break
    if idx >= len(nodes):
        return None

    lead = nodes[idx]
    if getattr(lead, "name", None) not in _BOLD_TAGS:
        return None

    bold_text = strip_html(str(lead))
    if not bold_text:
        return None

    remainder_html = "".join(str(n) for n in nodes[idx + 1:])
    remainder_text = strip_html(remainder_html)
    whole_line = not remainder_text

    if bold_text.rstrip().endswith(":"):
        return bold_text.rstrip(":").strip(), remainder_text

    candidate = bold_text.strip()
    low = candidate.lower()
    if low in _CONNECTOR_ONLY:
        return None

    if _YEAR_PHRASE_RE.match(candidate) or _GROUP_PHRASE_RE.match(candidate):
        return candidate, remainder_text

    if _BARE_NUM_RE.match(candidate):
        # A bare bolded numeral ("<strong>4.</strong> more text...") is a
        # deliberate section break in the source - unlike a PLAIN numbered
        # item (no bold at all), which stays a rule (see
        # `_split_numbered_items`).
        return candidate.rstrip("."), remainder_text

    if whole_line and len(candidate) <= 120 and not _COURSE_CODE_RE.search(candidate):
        # A short, standalone bold/italic paragraph with no course codes and
        # no colon reads as a header regardless of exact wording ("Group 1 -
        # Psychology Courses", "Foundations", "Temporal Requirement",
        # "Equivalent Courses", "(Sub-group: Africa)", ...).
        return candidate, remainder_text

    return None


def _extract_header(text: str, html_fragment: str) -> tuple[str, str, bool] | None:
    """Try to peel a header label off the front of `text`/`html_fragment`.

    Returns (label, body, is_note) or None. Checked in priority order: notes
    first (so a note citing a course code is never lost as an ordinary
    rule), then a leading bold/italic run, then a numbered "N. Label:"
    marker, then a plain-text phrase prefix.
    """
    stripped = text.strip()
    if not stripped:
        return None

    note = _match_note_prefix(stripped)
    if note is not None:
        return note[0], note[1], True

    bold = _leading_bold_label(html_fragment, stripped)
    if bold is not None:
        return bold[0], bold[1], _is_note(bold[0])

    numbered = _numbered_header_label(stripped)
    if numbered is not None:
        return numbered[0], numbered[1], _is_note(numbered[0])

    plain = _plain_header_label(stripped)
    if plain is not None:
        return plain[0], plain[1], _is_note(plain[0])

    return None


def _split_numbered_items(text: str) -> list[str]:
    """Split text with >=2 numbered markers into per-item chunks.

    "1. A 2. B" -> ["1. A", "2. B"]; any text before the first marker is
    folded into the first item so nothing is dropped. Returns [] when there
    are fewer than 2 markers (nothing meaningful to split).
    """
    matches = list(_NUM_ITEM_RE.finditer(text))
    if len(matches) < 2:
        return []
    items: list[str] = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        items.append(text[start:end].strip())
    prefix = text[: matches[0].start()].strip()
    if prefix:
        items[0] = f"{prefix} {items[0]}"
    return items


class _GroupAcc:
    """Mutable accumulator for a group; frozen into a RequirementGroup at the end."""

    def __init__(self, heading: str = "", is_note: bool = False, sticky: bool = True) -> None:
        self.heading = heading
        self.is_note = is_note
        # `sticky` = this heading may keep absorbing rules from LATER,
        # unrelated top-level <li>/<p> blocks (e.g. "First Year:" as the sole
        # content of its own block, with the actual course list living in
        # the NEXT block). A heading extracted INLINE alongside its own
        # course codes on the SAME originating line (e.g. "Second year
        # courses: RLG205H1, ...") is a complete, self-contained item and is
        # NOT sticky - it must not keep absorbing sibling blocks that carry
        # no header of their own. Fixed once at creation (see
        # `_RequirementAccumulator.process`'s `line_has_codes`).
        self.sticky = sticky
        self.codes: list[str] = []
        self.rules: list[RequirementRule] = []
        self.raw_parts: list[str] = []
        # A credit weight stated in the header itself is authoritative.
        self._header_credits = _first_credit(heading) if heading else 0.0
        self._rule_credits: set[float] = set()
        # The number of the most recent PLAIN numbered rule ("N. ...", not a
        # header) added to this group, used to stop a later number in the
        # SAME sequence from being misdetected as a new section header.
        self.last_numbered_rule: int | None = None

    def add_rule(self, text: str) -> None:
        text = text.strip()
        if not text:
            return
        credits = _first_credit(text)
        codes = _codes_in(text)
        self.rules.append(RequirementRule(credits=credits, description=text, course_codes=codes))
        self.codes.extend(codes)
        self.raw_parts.append(text)
        if credits:
            self._rule_credits.add(credits)
        num_m = _LEADING_NUM_RE.match(text)
        if num_m:
            self.last_numbered_rule = int(num_m.group(1))

    def is_empty(self) -> bool:
        return not self.heading and not self.rules and not self.codes

    def has_no_content(self) -> bool:
        """True if nothing has been accumulated yet (heading aside)."""
        return not self.rules and not self.codes

    @property
    def credits(self) -> float:
        if self._header_credits:
            return self._header_credits
        # Multiple *different* rule-level credit figures usually describe
        # independent alternatives, not an additive total - only trust a
        # single, unambiguous value; RequirementRule.credits still carries
        # the fine-grained per-rule numbers either way.
        if len(self._rule_credits) == 1:
            return next(iter(self._rule_credits))
        return 0.0

    def freeze(self) -> RequirementGroup:
        return RequirementGroup(
            heading=self.heading,
            credits=self.credits,
            is_note=self.is_note,
            course_codes=_dedupe(self.codes),
            rules=self.rules,
            raw_text=" ".join(self.raw_parts).strip(),
        )


_MAX_RECURSION_DEPTH = 8


class _RequirementAccumulator:
    """Runs the header/rule state machine over an ordered sequence of lines.

    Two pieces of state, threaded through `process`, prevent a header from
    "sticking" past where the source actually scopes it:

    - `block_id` (from `_flatten_lines`) identifies which top-level
      `<li>`/`<p>` a line came from. A heading opened INLINE - alongside its
      own course codes on the very same originating line, e.g. "Second year
      courses: RLG205H1, ..." - is marked non-`sticky` and, once we reach the
      NEXT block, is reverted to the last sticky heading (or "") before that
      block's content is added, so an unrelated sibling `<li>` with no
      header of its own is never folded into it.
    - `last_numbered_rule` (on `_GroupAcc`) stops a numbered item from being
      misdetected as a new section header when it is simply the next number
      in a plain numbered-rule sequence already running in the current group
      (e.g. items 1-3, 5-7 are plain rules -> item 4 must stay one too,
      instead of being read as "4. <Title-Case-looking label>:").
    """

    def __init__(self) -> None:
        self.groups: list[_GroupAcc] = []
        self.current = _GroupAcc()
        self._last_block_id: int | None = None
        self._sticky_heading: str = ""
        self._sticky_is_note: bool = False
        self._pending_block_revert: bool = False

    def _open_group(self, heading: str, is_note: bool, sticky: bool = True) -> None:
        heading = heading.strip()
        if self.current.heading and self.current.has_no_content():
            # The previous group was a header with no content of its own
            # (e.g. "Group 1 - Psychology Courses" immediately followed by
            # "Cluster A - ..."): fold it into the new heading instead of
            # emitting a data-free orphan group.
            heading = f"{self.current.heading} - {heading}" if heading else self.current.heading
            is_note = is_note or self.current.is_note
            sticky = sticky and self.current.sticky
        elif not self.current.is_empty():
            self.groups.append(self.current)
        self.current = _GroupAcc(heading=heading, is_note=is_note, sticky=sticky)
        if sticky:
            self._sticky_heading = heading
            self._sticky_is_note = is_note

    def _revert_to_sticky(self) -> None:
        """Close out a non-sticky, block-scoped group at a block boundary."""
        if not self.current.is_empty():
            self.groups.append(self.current)
        self.current = _GroupAcc(heading=self._sticky_heading, is_note=self._sticky_is_note)

    def process(
        self,
        text: str,
        html_fragment: str,
        depth: int = 0,
        block_id: int | None = None,
        line_has_codes: bool = False,
    ) -> None:
        stripped = text.strip()
        if not stripped:
            return

        if depth == 0:
            line_has_codes = bool(_COURSE_CODE_RE.search(stripped))
            if block_id is not None:
                if (
                    self._last_block_id is not None
                    and block_id != self._last_block_id
                    and not self.current.sticky
                ):
                    self._pending_block_revert = True
                self._last_block_id = block_id

        num_m = _LEADING_NUM_RE.match(stripped) if depth < _MAX_RECURSION_DEPTH else None
        # A pending block revert means "current" belongs to the PREVIOUS
        # block and its numbered-rule state does not describe this new one.
        current_last_numbered = None if self._pending_block_revert else self.current.last_numbered_rule
        suppress_numbered = (
            num_m is not None
            and current_last_numbered is not None
            and int(num_m.group(1)) == current_last_numbered + 1
        )

        header = (
            _extract_header(stripped, html_fragment)
            if depth < _MAX_RECURSION_DEPTH and not suppress_numbered
            else None
        )
        if header is not None:
            self._pending_block_revert = False
            label, body, is_note = header
            self._open_group(label, is_note, sticky=not line_has_codes)
            body = body.strip()
            if body and len(body) < len(stripped):
                self.process(body, body, depth + 1, block_id, line_has_codes)
            elif body:
                self.current.add_rule(body)
            return

        items = _split_numbered_items(stripped) if depth < _MAX_RECURSION_DEPTH else []
        if len(items) > 1:
            self._pending_block_revert = False
            for item in items:
                if item and len(item) < len(stripped):
                    self.process(item, item, depth + 1, block_id, line_has_codes)
                elif item:
                    self.current.add_rule(item)
            return

        if self._pending_block_revert:
            self._revert_to_sticky()
            self._pending_block_revert = False
        self.current.add_rule(stripped)

    def finish(self) -> list[RequirementGroup]:
        if not self.current.is_empty():
            self.groups.append(self.current)
        return [group.freeze() for group in self.groups]


# A trailing/leading <br/> nested INSIDE an inline em/strong/b tag (a source
# formatting artifact, e.g. "<em>Accepted Language Courses<br/></em>") is
# moved just outside the tag so line-splitting on <br/> is uniform.
_TRAILING_BR_IN_INLINE_RE = re.compile(r"<br\s*/?>\s*(</(?:em|strong|b)>)", re.IGNORECASE)
_LEADING_BR_IN_INLINE_RE = re.compile(r"(<(?:em|strong|b)>)\s*<br\s*/?>", re.IGNORECASE)


def _normalize_inline_br(field_html: str) -> str:
    field_html = _TRAILING_BR_IN_INLINE_RE.sub(r"\1<br/>", field_html)
    field_html = _LEADING_BR_IN_INLINE_RE.sub(r"<br/>\1", field_html)
    return field_html


class ProgramClient:
    """Client for the Academic Calendar program/program-requirements search."""

    def parse_results(self, html: str) -> list[Program]:
        """Parse a search-programs results page into `Program` objects. Pure."""
        soup = BeautifulSoup(html, "lxml")
        view_content = soup.select_one("div.view-content")
        if view_content is not None:
            rows = view_content.find_all("div", class_="views-row", recursive=False)
        else:
            rows = soup.select("div.views-row")

        programs: list[Program] = []
        for row in rows:
            program = self._parse_row(row)
            if program is not None:
                programs.append(program)
        return programs

    def _parse_row(self, row) -> Program | None:
        header = row.select_one("h3.js-views-accordion-group-header")
        header_text = strip_html(header.get_text(" ")) if header is not None else ""
        code_match = _PROGRAM_CODE_RE.search(header_text)
        if code_match is None:
            return None
        code = code_match.group(0)

        title_el = row.select_one(".views-field-title .field-content")
        title = strip_html(title_el.get_text(" ")) if title_el is not None else header_text

        dept_link = row.select_one(".views-field-field-section-link a")
        department = strip_html(dept_link.get_text(" ")) if dept_link is not None else ""
        department_url = dept_link.get("href", "") if dept_link is not None else ""

        enrolment_el = row.select_one(
            ".views-field-field-enrolment-requirements .field-content"
        )
        enrolment_requirements = (
            strip_html(str(enrolment_el)) if enrolment_el is not None else ""
        )

        completion_el = row.select_one(
            ".views-field-field-completion-requirements .field-content"
        )
        if completion_el is not None:
            completion_field_html = str(completion_el)
            raw_completion_text = strip_html(completion_field_html)
            groups = self.parse_completion_requirements(completion_field_html)
        else:
            raw_completion_text = ""
            groups = []

        total_match = _TOTAL_CREDITS_RE.match(raw_completion_text.strip())
        total_credits = float(total_match.group(1)) if total_match else 0.0

        return Program(
            code=code,
            title=title,
            program_type=_program_type_from_code(code),
            department=department,
            department_url=department_url,
            enrolment_requirements=enrolment_requirements,
            total_credits=total_credits,
            completion_requirements=groups,
            raw_completion_text=raw_completion_text,
        )

    def _flatten_lines(self, root) -> list[tuple[str, int]]:
        """Flatten `root`'s children into an ordered list of (line-HTML, block_id).

        `<ol>`/`<ul>` expand into their `<li>` children (recursing through a
        malformed doubly-nested `<ol><ol>...` with no direct `<li>`); within
        a `<p>`/`<li>`, `<br/>` splits the block into separate lines, and a
        nested `<ol>`/`<ul>` encountered mid-block flushes the accumulated
        text as one line, recurses into the nested list, then keeps
        accumulating any trailing content as further lines.

        `block_id` identifies which TOP-LEVEL `<li>`/`<p>` a line came from -
        every direct child of `root` and every `<li>` (top-level or nested)
        gets its own id, shared by all `<br/>`-split lines within it. This
        lets `_RequirementAccumulator` tell a header that sits alone in its
        own block (may keep applying to later blocks) apart from one
        extracted inline next to its own content on the SAME line (must not
        keep absorbing an unrelated sibling block with no header of its own).
        """
        lines: list[tuple[str, int]] = []
        next_id = [0]

        def emit(nodes: list, block_id: int) -> None:
            html_str = "".join(str(n) for n in nodes)
            if strip_html(html_str):
                lines.append((html_str, block_id))

        def walk_list(list_tag) -> None:
            items = list_tag.find_all("li", recursive=False)
            if items:
                for li in items:
                    walk_block(li)
            else:
                for child in list_tag.find_all(["ol", "ul"], recursive=False):
                    walk_list(child)

        def walk_block(block) -> None:
            block_id = next_id[0]
            next_id[0] += 1
            buffer: list = []
            for node in block.children:
                name = getattr(node, "name", None)
                if name == "br":
                    if buffer:
                        emit(buffer, block_id)
                        buffer = []
                elif name in ("ol", "ul"):
                    if buffer:
                        emit(buffer, block_id)
                        buffer = []
                    walk_list(node)
                else:
                    buffer.append(node)
            if buffer:
                emit(buffer, block_id)

        for child in root.children:
            name = getattr(child, "name", None)
            if name in ("ol", "ul"):
                walk_list(child)
            elif name is not None:
                walk_block(child)

        return lines

    def parse_completion_requirements(self, field_html: str) -> list[RequirementGroup]:
        """Parse a completion-requirements field into ordered `RequirementGroup`s.

        Pure (no network). See the module docstring for the segmentation
        approach: line-flattening on `<br/>` followed by leading-label
        extraction, so a header can sit inline with its own course list.
        """
        field_html = _normalize_inline_br(field_html)
        soup = BeautifulSoup(field_html, "lxml")
        root = soup.select_one(".field-content") or soup.body or soup

        lines = self._flatten_lines(root)
        acc = _RequirementAccumulator()

        for i, (line_html, block_id) in enumerate(lines):
            text = strip_html(line_html)
            if not text:
                continue

            # The leading "(X credits ...)" / "A total of X credits..." intro
            # is the program total, not a requirement; skip it - unless it is
            # the ONLY line in the field, in which case keeping it as a rule
            # beats yielding zero groups for a program with completion text.
            if (
                i == 0
                and len(lines) > 1
                and _TOTAL_CREDITS_RE.match(text)
                and not _COURSE_CODE_RE.search(text)
            ):
                continue

            acc.process(text, line_html, block_id=block_id)

        return acc.finish()

    def search(self, keyword: str = "", program_type: str = "", max_pages: int = 5) -> list[Program]:
        """Search programs by keyword/type, paging until a page comes back empty.

        Network entry point; parsing itself (`parse_results`) stays pure.
        """
        programs: list[Program] = []
        for page in range(max_pages):
            params = {
                "combine": keyword,
                "type": program_type or "All",
                "field_subject_area_prog_search_value": "All",
                "page": page,
            }
            html = get_html(SEARCH_URL, params=params)
            page_programs = self.parse_results(html)
            if not page_programs:
                break
            programs.extend(page_programs)
        return programs
