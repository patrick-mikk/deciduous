"""Academic Calendar course-search client.

Wraps the Drupal-rendered `search-courses` endpoint on
`artsci.calendar.utoronto.ca`. This is an undocumented public read-only
service (see docs/conventions.md) - a descriptive User-Agent and default
timeout come from `backend/data_sources/http.py`; we never write to it.

The HTML parsing (`parse_results`) is pure and network-free so it can run
against the saved fixture in unit tests; `search` adds the HTTP/pagination
layer on top.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup
from bs4.element import Tag

from backend.data_sources.http import get_html, strip_html
from backend.data_sources.models import Course

SEARCH_URL = "https://artsci.calendar.utoronto.ca/search-courses"

# Matches the H/Y credit-weight letter followed by the trailing campus digit,
# e.g. "POL208H1" -> "H1", "ABP100Y1" -> "Y1". See AGENTS.md domain glossary.
_CREDIT_SUFFIX_RE = re.compile(r"([HY])\d$")
_CREDIT_BY_LETTER = {"H": 0.5, "Y": 1.0}


def _credit_from_code(code: str) -> float:
    """Derive the credit weight (0.5 / 1.0) from the trailing H/Y in a course code.

    Returns 0.0 if the code doesn't match the expected pattern (defensive -
    should not happen for real Calendar data).
    """
    match = _CREDIT_SUFFIX_RE.search(code)
    if not match:
        return 0.0
    return _CREDIT_BY_LETTER[match.group(1)]


def _field_text(container: Tag | None, field_class: str) -> str:
    """Extract and clean the `.field-content` text of a `.views-field-*` element.

    Looks up `field_class` (e.g. "views-field-field-prerequisite") within
    `container`, then reads its `.field-content` child so the `.views-label`
    prefix (e.g. "Prerequisite: ") is excluded. Falls back to the field
    element itself if there's no distinct `.field-content` wrapper. Returns
    "" if `container` or the field isn't present - Calendar entries don't
    always have every field.
    """
    if container is None:
        return ""
    field = container.find(class_=field_class)
    if field is None:
        return ""
    content = field.find(class_="field-content")
    target = content if content is not None else field
    return strip_html(target.decode_contents())


def _parse_breadth(breadth_text: str) -> list[str]:
    """Split a "Category (1), Category (3)" breadth string into a list."""
    if not breadth_text:
        return []
    return [item.strip() for item in breadth_text.split(",") if item.strip()]


def _parse_course_row(row: Tag) -> Course | None:
    """Parse one outer `div.views-row` (course + accordion header) into a Course.

    Returns None if the row doesn't have the expected header - defends
    against unrelated `.views-row` elements elsewhere on the page ( the
    accordion content itself is wrapped in a nested `div.views-row` with no
    header, which this filters out).
    """
    header = row.find("h3", class_="js-views-accordion-group-header", recursive=False)
    if header is None:
        return None
    header_text = strip_html(header.decode_contents())
    code, sep, title = header_text.partition(" - ")
    code = code.strip()
    title = title.strip() if sep else ""
    if not code:
        return None

    # The accordion body holds the detail fields. In a browser-rendered page
    # jQuery-UI wraps it in `.ui-accordion-content`; in the raw server HTML
    # (what we fetch) there is no such class - the body is just a nested
    # `div.views-row`. Fall back to the row itself so fields resolve either way.
    content = (
        row.find(class_="ui-accordion-content")
        or row.find("div", class_="views-row")
        or row
    )

    prerequisites = _field_text(content, "views-field-field-prerequisite")
    recommended = _field_text(content, "views-field-field-recommended")
    if recommended:
        prefix = "Recommended Preparation: "
        prerequisites = (
            f"{prerequisites} {prefix}{recommended}" if prerequisites else f"{prefix}{recommended}"
        )

    breadth_text = _field_text(content, "views-field-field-breadth-requirements")

    return Course(
        code=code,
        title=title,
        section_code="",
        credit=_credit_from_code(code),
        campus="",
        description=_field_text(content, "views-field-body"),
        prerequisites=prerequisites,
        corequisites=_field_text(content, "views-field-field-corequisite"),
        exclusions=_field_text(content, "views-field-field-exclusion"),
        breadth=_parse_breadth(breadth_text),
        distribution=[],
        sections=[],
    )


def parse_results(html: str) -> list[Course]:
    """Parse a `search-courses` result page into a list of `Course` objects.

    Pure / network-free - the unit test drives this against the saved
    fixture. Each course is an outer `div.views-row` whose
    `h3.js-views-accordion-group-header` holds "CODE - Title"; fields not
    present on the Academic Calendar (section/timetable data) are left
    empty, matching `Course`'s TTB-sourced fields.
    """
    soup = BeautifulSoup(html, "lxml")
    courses: list[Course] = []
    for row in soup.find_all("div", class_="views-row"):
        course = _parse_course_row(row)
        if course is not None:
            courses.append(course)
    return courses


class CalendarCourseClient:
    """Client for the Academic Calendar's course-search endpoint."""

    def search(self, keyword: str, max_pages: int = 5) -> list[Course]:
        """Search courses by keyword, paginating until a page has no results.

        Stops when a page yields zero courses or `max_pages` is reached
        (0-based `page` query param, ~30 courses per page per the Calendar's
        Drupal view).
        """
        courses: list[Course] = []
        for page in range(max_pages):
            html = get_html(SEARCH_URL, params={"course_keyword": keyword, "page": page})
            page_courses = parse_results(html)
            if not page_courses:
                break
            courses.extend(page_courses)
        return courses
