"""Unit tests for the Program/program-requirements client.

Offline: parses saved fixtures, never hits the network. One network-guarded
live smoke test is included (skipped unless RUN_LIVE_SMOKE=1).

Runnable both as:
    python -m pytest backend/tests/test_programs.py
    python backend/tests/test_programs.py
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# Make the repo root importable (`backend.data_sources...`) regardless of how
# this file is invoked.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from bs4 import BeautifulSoup  # noqa: E402

from backend.data_sources.http import strip_html as strip_html_text  # noqa: E402
from backend.data_sources.models import (  # noqa: E402
    Program,
    RequirementGroup,
    RequirementRule,
)
from backend.data_sources.programs.client import (  # noqa: E402
    ProgramClient,
    _COURSE_CODE_RE,
    _program_type_from_code,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _codes_in_group(group: RequirementGroup) -> set[str]:
    return set(group.course_codes)


def _all_group_codes(program: Program) -> set[str]:
    codes: set[str] = set()
    for group in program.completion_requirements:
        codes |= _codes_in_group(group)
    return codes


# --------------------------------------------------------------- basic parsing
def test_parse_results_returns_three_programs() -> None:
    programs = ProgramClient().parse_results(_fixture("calendar_search_programs.html"))
    assert len(programs) == 3
    assert all(isinstance(p, Program) for p in programs)


def test_first_program_fields() -> None:
    programs = ProgramClient().parse_results(_fixture("calendar_search_programs.html"))
    first = programs[0]
    assert first.code == "ASMAJ1305A"
    assert first.program_type == "major"
    assert first.enrolment_requirements.strip() != ""
    # GGR172H1 is listed under some requirement group.
    assert "GGR172H1" in _all_group_codes(first), first.completion_requirements


def test_department_and_url_parsed() -> None:
    first = ProgramClient().parse_results(_fixture("calendar_search_programs.html"))[0]
    assert first.department == "Geography and Planning"
    assert first.department_url.startswith("https://artsci.calendar.utoronto.ca/section/")


def test_all_three_program_codes_and_types() -> None:
    programs = ProgramClient().parse_results(_fixture("calendar_search_programs.html"))
    assert {p.code for p in programs} == {"ASMAJ1305A", "ASMAJ1305B", "ASMAJ1305C"}
    assert all(p.program_type == "major" for p in programs)


# --------------------------------------------------------- program-type mapping
# design/09-uoft-degree-rules.md sec. 2 defines FIVE ArtSci POSt types. An
# unmapped prefix produces an empty `program_type`, which the frontend's
# `p.programType || "major"` badge fallback renders as "MAJOR" - the bug that
# had every ASCER certificate and ASFOC focus tagged "MAJOR" on the Browse tab.
_EXPECTED_TYPE_BY_PREFIX = {
    "ASSPE": "specialist",
    "ASMAJ": "major",
    "ASMIN": "minor",
    "ASFOC": "focus",
    "ASCER": "certificate",
}


def test_program_type_mapping_for_all_prefixes() -> None:
    for prefix, expected in _EXPECTED_TYPE_BY_PREFIX.items():
        assert _program_type_from_code(f"{prefix}1234") == expected, prefix
    # Stream-suffixed and 3-digit codes classify off the same 5-char prefix.
    assert _program_type_from_code("ASMAJ1305A") == "major"
    assert _program_type_from_code("ASMIN123") == "minor"
    assert _program_type_from_code("ASCER0552B") == "certificate"


def test_program_type_mapping_covers_every_prefix_the_calendar_emits() -> None:
    """No ArtSci POSt prefix may fall through to "" (which the UI shows as MAJOR)."""
    unmapped = [
        prefix for prefix in _EXPECTED_TYPE_BY_PREFIX
        if not _program_type_from_code(f"{prefix}0000")
    ]
    assert unmapped == [], f"prefixes with no program_type mapping: {unmapped}"


def test_reported_certificate_codes_are_certificates_not_majors() -> None:
    """The three codes reported mislabelled "MAJOR" in production."""
    reported = {
        "ASCER0120": "Certificate in French Language",
        "ASCER0338": "Certificate in Portuguese Language",
        "ASCER0552": "Certificate in Global Latin America",
    }
    for code, title in reported.items():
        assert _program_type_from_code(code, title) == "certificate", code
        # ...and still correct with no title available at all.
        assert _program_type_from_code(code) == "certificate", code


def test_unknown_prefix_falls_back_to_the_title() -> None:
    """A prefix outside the map degrades to the title's type word, never to ""."""
    assert _program_type_from_code("ASXXX0001", "Certificate in Business") == "certificate"
    assert _program_type_from_code("ASXXX0002", "Focus in Artificial Intelligence") == "focus"
    assert _program_type_from_code("ASXXX0003", "Sociology Specialist") == "specialist"
    assert _program_type_from_code("ASXXX0004", "Sociology Major") == "major"
    assert _program_type_from_code("ASXXX0005", "Sociology Minor") == "minor"
    # A mapped prefix always wins over the title.
    assert _program_type_from_code("ASMAJ0006", "Certificate in Whatever") == "major"
    # Nothing to go on -> "" (the honest "unclassified"), not a guess.
    assert _program_type_from_code("ASXXX0007", "Political Science") == ""
    assert _program_type_from_code("") == ""


def test_parse_row_tags_a_certificate_as_certificate() -> None:
    """End-to-end through `parse_results`: an ASCER row must not come out "major"."""
    html = """
    <div class="view-content">
      <div class="views-row">
        <h3 class="js-views-accordion-group-header">
          Certificate in French Language - ASCER0120
        </h3>
        <div class="views-row">
          <div class="views-field-title"><span class="field-content">
            Certificate in French Language
          </span></div>
          <div class="views-field-field-completion-requirements">
            <div class="field-content"><p>(2.0 credits) FSL221H1, FSL222H1</p></div>
          </div>
        </div>
      </div>
    </div>
    """
    program = ProgramClient().parse_results(html)[0]
    assert program.code == "ASCER0120"
    assert program.program_type == "certificate"


# ------------------------------------------------------ requirement-group shape
def test_parse_returns_requirement_groups() -> None:
    first = ProgramClient().parse_results(_fixture("calendar_search_programs.html"))[0]
    groups = first.completion_requirements
    assert len(groups) > 0
    assert all(isinstance(g, RequirementGroup) for g in groups)
    assert all(isinstance(r, RequirementRule) for g in groups for r in g.rules)
    # GDS majors state a program total.
    assert first.total_credits == 7.5


def test_course_code_regex_covers_all_campuses() -> None:
    for code in ("POL208H1", "MAT133Y1", "ANTC35H3", "ANT418H5", "ARH306Y0", "JAL328H1"):
        assert _COURSE_CODE_RE.fullmatch(code), code


def test_pure_completion_parser_matches_parse_results() -> None:
    html = _fixture("calendar_search_programs.html")
    first = ProgramClient().parse_results(html)[0]
    soup = BeautifulSoup(html, "lxml")
    row = soup.select_one("div.view-content").find_all(
        "div", class_="views-row", recursive=False
    )[0]
    field = row.select_one(".views-field-field-completion-requirements .field-content")
    groups = ProgramClient().parse_completion_requirements(str(field))
    assert [g.course_codes for g in groups] == [
        g.course_codes for g in first.completion_requirements
    ]


# ---------------------------------------------- coverage across all structures
# The 30-program fixture mixes every grouping style: <ol><li> (GDS), <p> section
# headers (Accounting "First Year:"/"Higher Years:"), and bold "Group A:" titles
# (Archaeology). It is the regression guard against the old <li>-only parser,
# which parsed 17/30 programs to ZERO groups and dropped ~87% of listed courses.
def test_full_sample_every_program_has_groups() -> None:
    programs = ProgramClient().parse_results(_fixture("calendar_search_programs_full.html"))
    assert len(programs) == 30
    # Every program with completion text yields at least one group with courses.
    without_courses = [
        p.code for p in programs
        if p.raw_completion_text and not _all_group_codes(p)
    ]
    assert without_courses == [], without_courses


def test_full_sample_captures_nearly_all_course_codes() -> None:
    html = _fixture("calendar_search_programs_full.html")
    programs = ProgramClient().parse_results(html)

    # Ground truth: every course-code token present anywhere in the completion
    # fields of the page.
    soup = BeautifulSoup(html, "lxml")
    present: set[str] = set()
    for row in soup.select("div.view-content > div.views-row"):
        field = row.select_one(
            ".views-field-field-completion-requirements .field-content"
        )
        if field is not None:
            present |= set(_COURSE_CODE_RE.findall(field.get_text(" ")))

    captured: set[str] = set()
    for program in programs:
        captured |= _all_group_codes(program)

    # The old parser captured 395 of ~3034; the group-aware parser should
    # recover essentially all of them.
    assert len(present) > 1000  # sanity: the fixture really is course-dense
    recovered = len(captured & present) / len(present)
    assert recovered >= 0.98, (
        f"only recovered {recovered:.1%} of {len(present)} codes "
        f"({len(captured & present)} captured)"
    )


def test_full_sample_recovers_named_groups() -> None:
    """Archaeology's bold 'Group A/B:' titles become distinct groups."""
    programs = ProgramClient().parse_results(_fixture("calendar_search_programs_full.html"))
    arch = next((p for p in programs if "Archaeology Specialist" in p.title), None)
    assert arch is not None
    headings = [g.heading for g in arch.completion_requirements]
    assert any(h.startswith("Group A") for h in headings), headings
    assert any(h.startswith("Group B") for h in headings), headings


def test_accounting_section_headers_become_groups() -> None:
    """Accounting's '<p>First Year:' / 'Higher Years:' headers become groups."""
    programs = ProgramClient().parse_results(_fixture("calendar_search_programs_full.html"))
    acct = next((p for p in programs if "Accounting Specialist" in p.title), None)
    assert acct is not None
    headings = {g.heading for g in acct.completion_requirements}
    assert "First Year" in headings, headings
    assert "Higher Years" in headings, headings
    assert acct.total_credits == 14.5


# ------------------------------------------------------- broad-catalog corpus
# `programs_corpus.jsonl` is a curated sample pulled from across the whole
# Calendar catalog (specialists/majors/minors/certificates/focuses), weighted
# towards the exact "mis-parses this" programs identified by manual analysis
# (inline header+courses in one block, <em> group labels, <br>-separated
# sub-labels, doubled <ol><ol>, credit-in-header, etc.). Each line is
# `{"code","title","program_type","subject_area","completion_html",
# "enrolment_html","raw_completion_text"}`; `completion_html` is exactly what
# `parse_completion_requirements` consumes in production.
def _load_corpus() -> list[dict]:
    path = FIXTURES / "programs_corpus.jsonl"
    if not path.exists():
        return []
    records = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


_CORPUS = _load_corpus()


def _no_corpus() -> bool:
    """True (and prints why) when the corpus fixture has not been harvested here.

    `programs_corpus.jsonl` is produced by `backend/scripts/harvest_programs.py`
    over the network and is **gitignored**, so a fresh checkout has no copy.
    Each corpus test below no-ops in that case - the same "print SKIPPED and
    return" shape `test_live_smoke_search_history` already uses - so a missing
    fixture can never take the whole module's collection (and with it the
    offline tests above) down with it.
    """
    if not _CORPUS:
        print("SKIPPED: backend/tests/fixtures/programs_corpus.jsonl not harvested")
        return True
    return False


def test_corpus_fixture_is_loaded() -> None:
    if _no_corpus():
        return
    assert len(_CORPUS) >= 40, "expected the broad-catalog corpus fixture to be populated"


def test_corpus_every_program_type_is_classified() -> None:
    """Every real catalog code in the corpus classifies, and to the right type.

    The corpus spans all five POSt types, so this is the broad-catalog guard
    against a prefix silently falling through to "" (rendered "MAJOR" by the
    UI) - exactly what happened to ASCER/ASFOC.
    """
    if _no_corpus():
        return
    unclassified = []
    mismatched = []
    for record in _CORPUS:
        code = record["code"]
        # Deliberately code-only (no title): this must guard the PREFIX map,
        # not the title fallback, which would happily rescue "Certificate
        # in ..." titles and hide an unmapped prefix.
        actual = _program_type_from_code(code)
        expected = _EXPECTED_TYPE_BY_PREFIX.get(code[:5])
        if not actual:
            unclassified.append(code)
        elif expected is not None and actual != expected:
            mismatched.append((code, actual, expected))
    assert unclassified == [], f"programs with no program_type: {unclassified}"
    assert mismatched == [], f"(code, got, want): {mismatched}"
    # The corpus really does exercise the two previously-broken types.
    prefixes = {r["code"][:5] for r in _CORPUS}
    assert "ASCER" in prefixes and "ASFOC" in prefixes, sorted(prefixes)


def test_corpus_every_program_has_a_group_with_courses() -> None:
    """(a) Every corpus program with completion text yields >=1 group with courses."""
    if _no_corpus():
        return
    client = ProgramClient()
    failures = []
    for record in _CORPUS:
        html = record["completion_html"]
        if not strip_html_text(html):
            continue
        groups = client.parse_completion_requirements(html)
        codes = {code for g in groups for code in g.course_codes}
        if not codes and _COURSE_CODE_RE.search(html):
            failures.append(record["code"])
    assert failures == [], f"programs with no captured course codes: {failures}"


def test_corpus_captures_at_least_99_percent_of_course_codes() -> None:
    """(b) >=99% of every course code present in each field is captured."""
    if _no_corpus():
        return
    client = ProgramClient()
    total_present = 0
    total_captured = 0
    per_program_failures = []
    for record in _CORPUS:
        html = record["completion_html"]
        present = set(_COURSE_CODE_RE.findall(html))
        if not present:
            continue
        groups = client.parse_completion_requirements(html)
        captured = {code for g in groups for code in g.course_codes}
        recovered = captured & present
        total_present += len(present)
        total_captured += len(recovered)
        recall = len(recovered) / len(present)
        if recall < 0.99:
            per_program_failures.append((record["code"], recall, present - recovered))

    assert per_program_failures == [], per_program_failures
    overall_recall = total_captured / total_present
    assert overall_recall >= 0.99, (
        f"only recovered {overall_recall:.1%} of {total_present} corpus course codes"
    )


def test_corpus_headings_never_contain_a_raw_course_code() -> None:
    """Robustness invariant: a header split boundary never leaves a code in it."""
    if _no_corpus():
        return
    client = ProgramClient()
    bad = []
    for record in _CORPUS:
        groups = client.parse_completion_requirements(record["completion_html"])
        for g in groups:
            if _COURSE_CODE_RE.search(g.heading):
                bad.append((record["code"], g.heading))
    assert bad == [], bad


# (c) Specific failure_example programs from the analysis, now in the corpus,
# segment into the distinct groups the raw HTML actually describes instead of
# collapsing into one blank-heading blob.
def test_corpus_biodiversity_year_headers_become_separate_groups() -> None:
    """ASMAJ0110: inline 'First Year (1.0 credit): BIO120H1...' + 'Higher Years:'."""
    if _no_corpus():
        return
    record = next(r for r in _CORPUS if r["code"] == "ASMAJ0110")
    groups = ProgramClient().parse_completion_requirements(record["completion_html"])
    headings = [g.heading for g in groups]
    assert any(h.startswith("First Year") for h in headings), headings
    assert any(h.startswith("Higher Years") for h in headings), headings
    first_year = next(g for g in groups if g.heading.startswith("First Year"))
    assert "BIO120H1" in first_year.course_codes


def test_corpus_asian_studies_em_group_labels_become_separate_groups() -> None:
    """ASMAJ0235: <em>Group A/B/C:</em> labels sitting inline with their course lists."""
    if _no_corpus():
        return
    record = next(r for r in _CORPUS if r["code"] == "ASMAJ0235")
    groups = ProgramClient().parse_completion_requirements(record["completion_html"])
    headings = [g.heading for g in groups]
    assert any(h.startswith("Group A") for h in headings), headings
    assert any(h.startswith("Group B") for h in headings), headings
    assert any(h.startswith("Group C") for h in headings), headings


def test_corpus_drama_minor_groups_not_absorbed_into_note() -> None:
    """ASMIN2148: Foundations/Group A/B/C must not cascade-merge into a Note group."""
    if _no_corpus():
        return
    record = next(r for r in _CORPUS if r["code"] == "ASMIN2148")
    groups = ProgramClient().parse_completion_requirements(record["completion_html"])
    by_heading = {g.heading: g for g in groups}
    assert "Foundations" in by_heading
    assert any(h.startswith("Group A") for h in by_heading), by_heading.keys()
    assert any(h.startswith("Group B") for h in by_heading), by_heading.keys()
    note_groups = [g for g in groups if g.is_note]
    assert all(len(g.course_codes) < 5 for g in note_groups), note_groups


def test_corpus_history_temporal_requirement_is_its_own_group() -> None:
    """ASSPE0652: '2. Temporal Requirement:' must not glue onto the prior group."""
    if _no_corpus():
        return
    record = next(r for r in _CORPUS if r["code"] == "ASSPE0652")
    groups = ProgramClient().parse_completion_requirements(record["completion_html"])
    headings = [g.heading for g in groups]
    assert any("Temporal Requirement" in h for h in headings), headings
    assert any(h.startswith("1. Geographic Distribution") for h in headings), headings


def test_corpus_certificate_credit_in_header_is_preserved() -> None:
    """ASCER1160: headers state their own credit weight ('...(1.0 credit):')."""
    if _no_corpus():
        return
    record = next(r for r in _CORPUS if r["code"] == "ASCER1160")
    groups = ProgramClient().parse_completion_requirements(record["completion_html"])
    first_year = next(g for g in groups if "first year" in g.heading.lower())
    second_year = next(g for g in groups if "second year" in g.heading.lower())
    assert first_year.credits == 1.0, first_year
    assert second_year.credits == 2.0, second_year


def test_corpus_lowercase_label_noun_still_forms_a_header() -> None:
    """ASFOC1689G: '<p>Required courses:</p>' (lowercase 'courses') must still
    become its own heading, matching the capitalized 'Required Courses:'
    spelling used by sibling foci - the Calendar is inconsistent about
    capitalizing common label nouns ("courses", "credits", ...) even within
    an otherwise Title-Case header."""
    if _no_corpus():
        return
    record = next(r for r in _CORPUS if r["code"] == "ASFOC1689G")
    groups = ProgramClient().parse_completion_requirements(record["completion_html"])
    by_heading = {g.heading: g for g in groups}
    assert "Required courses" in by_heading, by_heading.keys()
    assert by_heading["Required courses"].course_codes
    assert "Suggested Related Courses" in by_heading, by_heading.keys()


def test_corpus_recommended_prefixed_title_not_torn_at_the_keyword() -> None:
    """ASMAJ0135: '<strong>Recommended Sequence of Courses:</strong>' is a
    genuine section title, not a bare note flag - the whole phrase must stay
    one heading instead of being split into "Recommended" (mis-flagged as a
    note) + "Sequence of Courses"."""
    if _no_corpus():
        return
    record = next(r for r in _CORPUS if r["code"] == "ASMAJ0135")
    groups = ProgramClient().parse_completion_requirements(record["completion_html"])
    headings = [g.heading for g in groups]
    assert any(h.startswith("Recommended Sequence of Courses") for h in headings), headings
    assert not any(h == "Recommended" for h in headings), headings


def test_corpus_black_studies_certificate_department_pools_separated() -> None:
    """ASCER0828: each department's course pool is its own group, not one blob."""
    if _no_corpus():
        return
    record = next(r for r in _CORPUS if r["code"] == "ASCER0828")
    groups = ProgramClient().parse_completion_requirements(record["completion_html"])
    headings = {g.heading for g in groups}
    for expected in ("History", "Sociology", "Anthropology"):
        assert expected in headings, headings


# ----------------------------------------------------------------- live smoke
def test_live_smoke_search_history() -> None:
    """Network-guarded live smoke test; skipped by default."""
    if os.environ.get("RUN_LIVE_SMOKE") != "1":
        print("SKIPPED: set RUN_LIVE_SMOKE=1 to run the live smoke test")
        return
    results = ProgramClient().search("history")
    assert isinstance(results, list) and len(results) > 0
    assert all(isinstance(p, Program) for p in results)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK - {name}")
    print("OK - all test_programs assertions passed")
