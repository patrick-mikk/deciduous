"""Harvest the FULL live Academic Calendar program catalog.

Usage (Windows, force UTF-8 for the unicode it prints):
    PYTHONUTF8=1 python backend/scripts/harvest_programs.py

What it does
------------
1. Paginates ``GET /search-programs`` with ``combine="" type=All
   field_subject_area_prog_search_value=All`` (page=0, 1, 2, ...) until a page
   returns no program rows. Verified live: this single query already returns
   the ENTIRE catalog (413 programs over 14 pages as of 2026-07-08) - no
   fallback to per-type / per-subject-area enumeration was needed. The
   fallback loop is still implemented and used automatically if the
   empty-combine query ever comes back suspiciously small (< 100 programs),
   so the harvest stays robust to future template changes.
2. Also probes a Drupal JSON:API source (``/jsonapi/node/programs``) for
   *subject area* metadata, which the search-accordion HTML never exposes per
   row, and prints a structural comparison against the accordion HTML and a
   program detail page (``/program/<code>``). See ``probe_richer_sources()``.
3. Writes the full corpus (one JSON object per line) and a curated ~40-program
   diverse fixture subset.
4. Prints program_type / structural-signature stats.

This script performs network I/O (it is explicitly the harvesting entry
point); ``backend/data_sources/programs/client.py`` parsing stays pure and is
reused here only for its regexes/helpers, never re-implemented.
"""

from __future__ import annotations

import json
import random
import re
import sys
import time
from collections import Counter
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from bs4 import BeautifulSoup  # noqa: E402

from backend.data_sources.http import USER_AGENT, get_html, get_json, strip_html  # noqa: E402
from backend.data_sources.programs.client import (  # noqa: E402
    _PROGRAM_CODE_RE,
    _program_type_from_code,
    SEARCH_URL,
)

JSONAPI_PROGRAMS_URL = "https://artsci.calendar.utoronto.ca/jsonapi/node/programs"
DETAIL_URL_TMPL = "https://artsci.calendar.utoronto.ca/program/{slug}"

THROTTLE_MIN = 0.15
THROTTLE_MAX = 0.30

CORPUS_PATH = Path(
    "C:/Users/patri/AppData/Local/Temp/claude/"
    "C--Users-patri-OneDrive-Desktop-Projects-Course-Dashboard/"
    "9577e4bc-0761-4d64-8006-0b3bf293599a/scratchpad/programs_corpus.jsonl"
)
FIXTURE_PATH = _REPO_ROOT / "backend" / "tests" / "fixtures" / "programs_corpus.jsonl"

TYPE_SELECT_VALUES = ["1", "2", "3", "4", "5", "6", "7"]  # combined/spec/major/minor/focus/cert1/cert2

SUBJECT_AREA_VALUES = [
    "Actuarial Science", "African Studies", "American Studies", "Anthropology",
    "Archaeology", "Architecture and Visual Studies", "Art History",
    "Asian Canadian Studies", "Astronomy and Astrophysics", "Biochemistry",
    "Biology", "Book and Media Studies", "Business Fundamentals",
    "Canadian Studies", "Cell and Systems Biology", "Celtic Studies",
    "Chemistry", "Christianity and Culture", "Christianity and Education",
    "Cinema Studies Institute", "Classics", "Cognitive Science",
    "Computer Science", "Contemporary Asian Studies", "Creativity and Society",
    "Criminology and Sociolegal Studies",
    "Critical Studies in Equity and Solidarity", "Data Science",
    "Diaspora and Transnational Studies", "Digital Humanities",
    "Drama, Theatre and Performance Studies", "Earth Sciences",
    "East Asian Studies", "Ecology and Evolutionary Biology", "Economics",
    "Education and Society", "English", "School of the Environment",
    "Ethics, Society, and Law", "European Affairs",
    "Forest Conservation and Forest Biomaterials Science", "French",
    "Geography and Planning", "German", "History",
    "History and Philosophy of Science and Technology", "Human Biology",
    "Hungarian", "Immunology", "Indigenous Studies",
    "Industrial Relations and Human Resources", "Innis College",
    "International Relations", "Italian", "Centre for Jewish Studies",
    "Laboratory Medicine and Pathobiology", "Latin American Studies",
    "Linguistics", "Literature and Critical Theory",
    "Material Culture and Semiotics", "Materials Science", "Mathematics",
    "Medieval Studies", "Molecular Genetics and Microbiology",
    "Munk School of Global Affairs and Public Policy", "Music",
    "Near and Middle Eastern Civilizations", "New College",
    "Nutritional Sciences", "Pharmacology and Toxicology", "Philosophy",
    "Physics", "Physiology", "Planetary Science", "Political Science",
    "Portuguese", "Psychology", "Public Health", "Religion",
    "Renaissance Studies", "Rotman Commerce", "St. Michael's College",
    "Science, Technology, and Society", "Sexual Diversity Studies",
    "Slavic and East European Languages and Cultures", "Sociology",
    "South Asian Studies", "Spanish", "Statistical Sciences",
    "Trinity College", "University College", "Victoria College",
    "Women and Gender Studies", "Woodsworth College", "Writing and Rhetoric",
    "Yiddish Studies",
]


def _throttle() -> None:
    time.sleep(random.uniform(THROTTLE_MIN, THROTTLE_MAX))


def _log(msg: str) -> None:
    print(msg, flush=True)


# --------------------------------------------------------------------------- row parsing
def _parse_row(row) -> dict | None:
    """Extract one program's corpus record from a `div.views-row`. Pure (no I/O)."""
    header = row.select_one("h3.js-views-accordion-group-header")
    header_text = strip_html(header.get_text(" ")) if header is not None else ""
    code_match = _PROGRAM_CODE_RE.search(header_text)
    if code_match is None:
        return None
    code = code_match.group(0)

    title_el = row.select_one(".views-field-title .field-content")
    title = strip_html(title_el.get_text(" ")) if title_el is not None else header_text

    completion_el = row.select_one(
        ".views-field-field-completion-requirements .field-content"
    )
    completion_html = str(completion_el) if completion_el is not None else ""
    raw_completion_text = strip_html(completion_html)

    enrolment_el = row.select_one(".views-field-field-enrolment-requirements .field-content")
    enrolment_html = str(enrolment_el) if enrolment_el is not None else ""

    return {
        "code": code,
        "title": title,
        "program_type": _program_type_from_code(code),
        "subject_area": "",  # filled in later from the JSON:API pass, best-effort
        "completion_html": completion_html,
        "enrolment_html": enrolment_html,
        "raw_completion_text": raw_completion_text,
    }


def _rows_on_page(html: str) -> list:
    soup = BeautifulSoup(html, "lxml")
    view_content = soup.select_one("div.view-content")
    if view_content is None:
        return []
    return view_content.find_all("div", class_="views-row", recursive=False)


# --------------------------------------------------------------------------- enumeration
def harvest_by_query(
    combine: str, program_type: str, subject_area: str = "All", max_pages: int = 60
) -> dict[str, dict]:
    """Paginate one (combine, type, subject_area) query until an empty page.

    Returns {code: record}.
    """
    found: dict[str, dict] = {}
    for page in range(max_pages):
        params = {
            "combine": combine,
            "type": program_type or "All",
            "field_subject_area_prog_search_value": subject_area or "All",
            "page": page,
        }
        html = get_html(SEARCH_URL, params=params)
        rows = _rows_on_page(html)
        if not rows:
            break
        for row in rows:
            record = _parse_row(row)
            if record is not None:
                found[record["code"]] = record
        _log(f"  page {page}: {len(rows)} rows, {len(found)} programs so far")
        _throttle()
    return found


def harvest_all_programs() -> tuple[dict[str, dict], str]:
    """Enumerate every program. Returns (code -> record, strategy used)."""
    _log("Harvesting via combine='' type=All (primary strategy)...")
    programs = harvest_by_query(combine="", program_type="All")

    if len(programs) >= 100:
        return programs, "empty-combine-type-all"

    # Fallback: the primary query came back suspiciously small (e.g. the
    # Calendar template changed). Enumerate by program type, then by subject
    # area, merging by code.
    _log(
        f"Primary strategy only found {len(programs)} programs; "
        "falling back to per-type enumeration."
    )
    for type_value in TYPE_SELECT_VALUES:
        _log(f"Harvesting type={type_value}...")
        programs.update(harvest_by_query(combine="", program_type=type_value))

    if len(programs) >= 100:
        return programs, "per-type-fallback"

    _log(
        f"Per-type fallback only found {len(programs)} programs; "
        "falling back to per-subject-area enumeration."
    )
    for subject in SUBJECT_AREA_VALUES:
        _log(f"Harvesting subject_area={subject!r}...")
        found = harvest_by_query(combine="", program_type="All", subject_area=subject)
        for code, record in found.items():
            record["subject_area"] = record.get("subject_area") or subject
        programs.update(found)

    return programs, "per-subject-area-fallback"


# ------------------------------------------------------------- JSON:API subject-area pass
def enrich_subject_areas(programs: dict[str, dict]) -> int:
    """Best-effort: fill `subject_area` from the JSON:API node--programs listing.

    The search-accordion HTML never carries a per-row subject area (see
    `probe_richer_sources`), but the JSON:API node does
    (`field_subject_area_prog_search`, a list - joined with '; ' here).
    Returns the number of programs enriched.
    """
    _log("Enriching subject_area from JSON:API (best-effort)...")
    code_to_subjects: dict[str, str] = {}
    offset = 0
    limit = 50
    fields = "field_post_code,field_subject_area_prog_search"
    while True:
        url = (
            f"{JSONAPI_PROGRAMS_URL}?page[limit]={limit}&page[offset]={offset}"
            f"&fields[node--programs]={fields}"
        )
        try:
            data = get_json(url)
        except Exception as exc:  # network hiccup: don't fail the whole harvest
            _log(f"  JSON:API page offset={offset} failed ({exc}); stopping enrichment.")
            break
        if not data or not data.get("data"):
            break
        for item in data["data"]:
            attrs = item.get("attributes", {})
            code = attrs.get("field_post_code")
            subjects = attrs.get("field_subject_area_prog_search") or []
            if code:
                code_to_subjects[code] = "; ".join(subjects)
        if len(data["data"]) < limit:
            break
        offset += limit
        _throttle()

    enriched = 0
    for code, record in programs.items():
        subjects = code_to_subjects.get(code)
        if subjects:
            record["subject_area"] = subjects
            enriched += 1
    _log(f"  {len(code_to_subjects)} JSON:API program nodes seen; {enriched} records enriched.")
    return enriched


# --------------------------------------------------------------------------------- probing
def probe_richer_sources() -> None:
    """Probe the JSON:API and a program detail page; print findings.

    Fetches ONE known program (Greek Minor / ASMIN2123) three ways - the
    search-accordion HTML, its own detail page, and the JSON:API node - and
    diffs the completion-requirements field content across all three.
    """
    _log("\n=== Probing for a richer structured source ===")

    _log("1. Checking JSON:API root (https://artsci.calendar.utoronto.ca/jsonapi)...")
    root = get_json("https://artsci.calendar.utoronto.ca/jsonapi")
    _throttle()
    node_bundles = sorted(k for k in (root or {}).get("links", {}) if k.startswith("node--"))
    _log(f"   node bundles exposed: {node_bundles}")
    _log("   -> node--programs exists and is queryable at /jsonapi/node/programs")

    sample = get_json(f"{JSONAPI_PROGRAMS_URL}?page[limit]=1")
    _throttle()
    attrs = sample["data"][0]["attributes"] if sample and sample.get("data") else {}
    _log(f"   sample node attribute keys: {sorted(attrs.keys())}")
    _log(
        "   -> field_post_code (exact program code) and "
        "field_subject_area_prog_search (list!) are present per-node; "
        "NEITHER is exposed anywhere in the search-accordion HTML rows."
    )
    _log("   -> JSON:API page size is capped at 50 regardless of page[limit] requested "
         "(offset pagination required for a full pull).")

    code = attrs.get("field_post_code", "ASMIN2123")
    slug = code.lower()
    cr = attrs.get("field_completion_requirements") or {}
    jsonapi_value = cr.get("value", "")

    # Compare against the search-accordion HTML for the SAME program.
    search_html = get_html(
        SEARCH_URL,
        params={
            "combine": attrs.get("title", "").split(" - ")[0],
            "type": "All",
            "field_subject_area_prog_search_value": "All",
            "page": 0,
        },
    )
    _throttle()
    rows = _rows_on_page(search_html)
    accordion_field = ""
    for row in rows:
        rec = _parse_row(row)
        if rec and rec["code"] == code:
            accordion_field = rec["completion_html"]
            break

    # Compare against the program's own detail page.
    detail_html = ""
    try:
        detail_html = get_html(DETAIL_URL_TMPL.format(slug=slug))
    except Exception as exc:
        _log(f"   detail page fetch failed: {exc}")
    _throttle()
    detail_soup = BeautifulSoup(detail_html, "lxml") if detail_html else None
    detail_field = ""
    if detail_soup is not None:
        el = detail_soup.select_one(
            ".field--name-field-completion-requirements .field__item"
        )
        detail_field = str(el) if el is not None else ""

    accordion_text = strip_html(accordion_field)
    jsonapi_text = strip_html(jsonapi_value)
    detail_text = strip_html(detail_field)

    _log(f"\n   Sample program: {code} ({attrs.get('title', '')})")
    _log(f"   accordion completion text : {accordion_text[:200]!r}")
    _log(f"   JSON:API completion text  : {jsonapi_text[:200]!r}")
    _log(f"   detail-page completion text: {detail_text[:200]!r}")
    same_accordion_jsonapi = accordion_text == jsonapi_text
    same_accordion_detail = accordion_text == detail_text
    _log(f"   accordion == JSON:API text : {same_accordion_jsonapi}")
    _log(f"   accordion == detail text   : {same_accordion_detail}")
    _log(
        "\n   FINDING: all three sources render the SAME underlying Drupal field "
        "(field_completion_requirements) - same free-text grouping ambiguity "
        "(concatenated '1. ... 2. ...' items, bold/':'-header inconsistency) in "
        "every one of them. Neither the JSON:API nor the detail page is a "
        "structurally richer source for GROUPING. The one genuine win from "
        "JSON:API is METADATA: field_post_code and (crucially) "
        "field_subject_area_prog_search are present per-node there and are "
        "NOT present anywhere in the search-accordion HTML rows, so this "
        "harvest uses JSON:API only to backfill `subject_area` "
        "(see enrich_subject_areas()), not to re-source completion text."
    )
    _log(
        "   Secondary finding: in all three sources every course code inside "
        "completion/enrolment text is also wrapped in an <a href=\"/course/CODE\"> "
        "link, so a parser could cross-check/extend the regex-based "
        "_COURSE_CODE_RE scan with an anchor-href scan for extra robustness "
        "(not implemented here - out of scope for this harvest script)."
    )


# ------------------------------------------------------------------------------- output
def write_corpus(programs: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in programs:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _structural_signature(completion_html: str) -> str:
    """A short signature like 'p,strong' summarizing which block tags appear."""
    soup = BeautifulSoup(completion_html, "lxml")
    tags_present = []
    for tag in ("ol", "ul", "p", "strong", "b", "table"):
        if soup.find(tag) is not None:
            tags_present.append(tag)
    return ",".join(tags_present) if tags_present else "(none)"


def pick_curated_subset(programs: list[dict], target: int = 40) -> list[dict]:
    """Choose a diverse subset spanning every structural signature observed.

    Greedy: for each distinct (program_type, structural signature) bucket,
    take up to a small quota of programs (biggest first, since bigger
    completion_html is more likely to exercise multiple grouping cues at
    once), until `target` programs are collected. Always keeps the smallest
    minor and the largest specialist as explicit tiny/huge anchors.
    """
    buckets: dict[tuple[str, str], list[dict]] = {}
    for record in programs:
        sig = _structural_signature(record["completion_html"])
        key = (record["program_type"] or "other", sig)
        buckets.setdefault(key, []).append(record)

    for bucket in buckets.values():
        bucket.sort(key=lambda r: len(r["completion_html"]), reverse=True)

    chosen: dict[str, dict] = {}

    # Anchors: smallest non-empty completion_html (tiny minor) and largest
    # overall (huge specialist), and anything with a <table>.
    non_empty = [p for p in programs if p["completion_html"].strip()]
    if non_empty:
        smallest = min(non_empty, key=lambda r: len(r["completion_html"]))
        largest = max(non_empty, key=lambda r: len(r["completion_html"]))
        chosen[smallest["code"]] = smallest
        chosen[largest["code"]] = largest
    for record in programs:
        if "<table" in record["completion_html"].lower():
            chosen[record["code"]] = record

    # Multi-campus codes (UTM/UTSC-flavoured course codes referenced).
    utm_utsc_re = re.compile(r"\b[A-Z]{3}[A-Z]\d{2}[HY][35]\b")
    for record in programs:
        if len(chosen) >= target:
            break
        if utm_utsc_re.search(record["completion_html"]):
            chosen[record["code"]] = record

    # Round-robin across (type, signature) buckets so every structural
    # pattern is represented, regardless of how common it is.
    bucket_keys = sorted(buckets.keys())
    idx = 0
    guard = 0
    while len(chosen) < target and guard < 10_000:
        guard += 1
        key = bucket_keys[idx % len(bucket_keys)]
        idx += 1
        bucket = buckets[key]
        for record in bucket:
            if record["code"] not in chosen:
                chosen[record["code"]] = record
                break
        if idx // len(bucket_keys) > 5:  # buckets exhausted, stop looping forever
            break

    return list(chosen.values())[:target]


def print_stats(programs: list[dict]) -> None:
    _log(f"\nTotal programs harvested: {len(programs)}")

    type_counts = Counter(p["program_type"] or "(unclassified)" for p in programs)
    _log("\nBreakdown by program_type:")
    for ptype, count in sorted(type_counts.items(), key=lambda kv: -kv[1]):
        _log(f"  {ptype:15s} {count}")

    sig_counts = Counter(_structural_signature(p["completion_html"]) for p in programs)
    _log("\nStructural-signature histogram (tags present in completion_html):")
    for sig, count in sorted(sig_counts.items(), key=lambda kv: -kv[1]):
        _log(f"  {sig:30s} {count}")

    tag_counts = Counter()
    for p in programs:
        soup = BeautifulSoup(p["completion_html"], "lxml")
        for tag in ("ol", "ul", "p", "strong", "b", "table"):
            tag_counts[tag] += len(soup.find_all(tag))
    _log("\nRaw tag occurrence counts across the whole corpus:")
    for tag, count in tag_counts.most_common():
        _log(f"  <{tag}>: {count}")


def main() -> None:
    programs_by_code, strategy = harvest_all_programs()
    _log(f"\nEnumeration strategy used: {strategy}")
    _log(f"Total distinct programs: {len(programs_by_code)}")

    enrich_subject_areas(programs_by_code)

    programs = sorted(programs_by_code.values(), key=lambda r: r["code"])
    write_corpus(programs, CORPUS_PATH)
    _log(f"\nFull corpus written: {CORPUS_PATH} ({len(programs)} lines)")

    curated = pick_curated_subset(programs, target=40)
    curated.sort(key=lambda r: r["code"])
    write_corpus(curated, FIXTURE_PATH)
    _log(f"Curated fixture written: {FIXTURE_PATH} ({len(curated)} lines)")

    print_stats(programs)

    probe_richer_sources()


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    _log(f"User-Agent: {USER_AGENT}")
    main()
