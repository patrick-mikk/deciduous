"""LLM-assisted segmentation of program completion requirements (Google Gemini).

Some UofT program requirement blocks are too irregular for deterministic
heuristics to segment reliably. This module uses an LLM to decide the *grouping*
(First Year / Group A / Electives / ...) while a regex guarantees *completeness*:

    LLM decides structure  ->  regex guarantees every course code is preserved

Design principles:
- **Offline batch, not a runtime dependency.** Program requirements change ~yearly;
  parse once, cache the structured result, and the app never calls an LLM at request
  time (no API key on the hot path, works on cPanel).
- **Public data only.** Program requirements are public, so sending them to an
  external API is fine. NEVER send student/transcript data here (see ADR-0005).
- **Provider-pluggable.** `Grouper` is the interface; `GeminiGrouper` is the first
  implementation. A Cohere/Claude grouper can be dropped in without changing callers.
- **Validated output.** `_validate_and_repair` drops any course code the model
  invented (not in the source) and sweeps any code the model missed into a
  recovered "Unclassified" group, so capture is always 100% regardless of the LLM.

Config (environment variables, never committed):
    GEMINI_API_KEY   required to make live calls (get one at aistudio.google.com)
    GEMINI_MODEL     optional, default "gemini-flash-latest" (a Google-managed rolling
                     alias for the current stable Flash release, so this module never
                     pins a dated model ID that Google later retires)
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Protocol

import requests

from backend.data_sources.http import strip_html
from backend.data_sources.models import (
    RequirementCourse,
    RequirementGroup,
    RequirementRule,
)

# Course-code regex duplicated locally (not imported from programs.client) so this
# module is decoupled from that file. 3 letters + alnum + 2 digits + H/Y + campus
# digit: POL208H1, MAT133Y1, ANTC35H3 (UTSC), ANT418H5 (UTM), ARH306Y0 (abroad).
import re

_COURSE_CODE_RE = re.compile(r"\b[A-Z]{3}[A-Z0-9]\d{2}[HY]\d\b")

# Credit weight from the H/Y in a course code: H = 0.5, Y = 1.0.
_CREDIT_SUFFIX_RE = re.compile(r"([HY])\d$")
_CREDIT_BY_LETTER = {"H": 0.5, "Y": 1.0}


def _credit_from_code(code: str) -> float:
    """Course credit weight derived from its code (POL208H1 -> 0.5, ABP100Y1 -> 1.0)."""
    match = _CREDIT_SUFFIX_RE.search(code)
    return _CREDIT_BY_LETTER.get(match.group(1), 0.0) if match else 0.0

_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
# "-latest" routes to a current Flash model with live free-tier quota; override
# with GEMINI_MODEL (e.g. "gemma-3-27b-it" for Gemma's separate quota pool).
_DEFAULT_MODEL = "gemini-flash-latest"
_MAX_RETRIES = 3
_RETRY_STATUS = {429, 503}  # rate-limited / transient overload -> back off and retry

# Gemini structured-output schema (OpenAPI subset; note the UPPERCASE types).
_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "total_credits": {"type": "NUMBER"},
        "groups": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "heading": {"type": "STRING"},
                    "credits": {"type": "NUMBER"},
                    "is_note": {"type": "BOOLEAN"},
                    "notes": {"type": "STRING"},
                    "courses": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "code": {"type": "STRING"},
                                "notes": {"type": "STRING"},
                            },
                            "required": ["code"],
                        },
                    },
                },
                "required": ["heading", "courses"],
            },
        },
    },
    "required": ["groups"],
}

_PROMPT = """\
You are extracting the structured requirement groups from a University of Toronto \
program's completion requirements. The source text is messy and inconsistent.

Segment it into requirement GROUPS. A group is a labelled section such as \
"First Year", "Second Year", "Higher Years", "Group A: ...", "Core Courses", \
"Electives", "Stream 1", or an intro/ungrouped block. For EACH group return:
- heading: the group's label exactly as written (e.g. "First Year", "Group A: Social \
and Political Topics"), or "" for an intro/ungrouped block.
- credits: the number of credits this group requires if stated, else 0.
- is_note: true if the block is a note/annotation, not an actual requirement.
- notes: any ADDITIONAL information about the group as a whole (caveats, substitution \
rules, "choose one of", footnotes that apply to the whole group), else "".
- courses: the list of courses under this group. For EACH course return:
    - code: the EXACT UofT course code (e.g. POL208H1, ANTC35H3). Copy it verbatim.
    - notes: any additional information about THIS specific course (e.g. "recommended", \
"only for double majors", a footnote marker's meaning), else "".
  DO NOT invent course codes. DO NOT drop any. Every course code in the source text must \
appear under exactly one group.

Also return total_credits: the program's total required credits if stated (usually in a \
leading line like "(7.0 credits ...)"), else 0.

Requirements text:
---
{text}
---
Return JSON only, matching the provided schema."""


def _retry_delay(resp: requests.Response) -> float | None:
    """Parse the server's suggested retry delay (RetryInfo, e.g. "31s") from a 429."""
    try:
        for detail in resp.json().get("error", {}).get("details", []):
            if detail.get("@type", "").endswith("RetryInfo"):
                raw = str(detail.get("retryDelay", ""))
                if raw.endswith("s"):
                    return float(raw[:-1])
    except (ValueError, KeyError, AttributeError):
        return None
    return None


_MARKDOWN_FENCE_RE = re.compile(r"^```[a-zA-Z]*\s*\n?|\n?```\s*$")


def _extract_json_text(payload_text: str) -> str:
    """Strip a markdown code fence (` ```json ... ``` ` or ` ``` ... ``` `)
    around the model's output, if present.

    `responseMimeType: "application/json"` (set in `_generate`'s payload)
    should make Gemini return bare JSON, but models occasionally wrap
    structured output in a fence regardless of the requested MIME type — this
    is defensive, not load-bearing for the happy path.
    """
    text = payload_text.strip()
    if text.startswith("```"):
        text = _MARKDOWN_FENCE_RE.sub("", text)
    return text.strip()


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for it in items:
        if it not in seen:
            seen.add(it)
            out.append(it)
    return out


class LLMGroupingError(Exception):
    """Raised when the LLM grouping call fails or returns unusable output.

    `status_code` is the HTTP status the API layer (`backend/api/programs.py`)
    should surface for this failure — a sensible default of 502 (the server
    talked to Gemini and Gemini's response couldn't be used), overridden by
    subclasses for failure modes that aren't really "Gemini's fault" (e.g. a
    missing server-side API key is a 503, not a bad-gateway).
    """

    status_code = 502


class GeminiNotConfiguredError(LLMGroupingError):
    """No `GEMINI_API_KEY` configured server-side — a deploy/config issue,
    not a transient Gemini failure, so the frontend shouldn't invite a retry."""

    status_code = 503


class GeminiRequestError(LLMGroupingError):
    """Gemini (or the network) rejected/failed the HTTP request itself —
    non-2xx status, exhausted retries, or a connection failure."""

    status_code = 502


class GeminiResponseError(LLMGroupingError):
    """Gemini answered 200 OK but the body wasn't the expected JSON shape —
    e.g. markdown-fenced text that didn't get stripped, or truncated output."""

    status_code = 502


@dataclass
class GroupingResult:
    """Structured groups plus a validation report for one program."""

    groups: list[RequirementGroup]
    total_credits: float
    report: dict = field(default_factory=dict)


class Grouper(Protocol):
    """Provider-agnostic interface: text/HTML -> validated GroupingResult."""

    def group(self, completion_html: str) -> GroupingResult: ...


def _validate_and_repair(raw: dict, source_text: str) -> tuple[list[RequirementGroup], dict]:
    """Coerce raw LLM JSON into RequirementGroups with a hard completeness guarantee.

    Course codes the model invented (absent from the source) are dropped; codes the
    model missed are swept into a recovered "Unclassified" group. So the union of all
    group codes always equals exactly the set of codes present in the source.
    """
    present = set(_COURSE_CODE_RE.findall(source_text))
    groups: list[RequirementGroup] = []
    captured: set[str] = set()
    hallucinated: set[str] = set()

    for g in raw.get("groups") or []:
        # Accept both the rich `courses: [{code, notes}]` shape and a plain
        # `course_codes: [str]` fallback, so the validator is robust to either.
        raw_courses = g.get("courses")
        if not raw_courses:
            raw_courses = [{"code": c} for c in (g.get("course_codes") or [])]

        kept: list[RequirementCourse] = []
        seen: set[str] = set()
        for c in raw_courses:
            code = str((c or {}).get("code") or "").upper().strip()
            note = str((c or {}).get("notes") or "").strip()
            if code in present and code not in seen:
                seen.add(code)
                kept.append(RequirementCourse(code=code, credits=_credit_from_code(code), notes=note))
            elif code not in present and _COURSE_CODE_RE.fullmatch(code):
                hallucinated.add(code)
        codes = [rc.code for rc in kept]
        captured |= set(codes)
        heading = str(g.get("heading") or "").strip()
        group_credits = float(g.get("credits") or 0.0)
        groups.append(
            RequirementGroup(
                heading=heading,
                credits=group_credits,
                is_note=bool(g.get("is_note")),
                course_codes=codes,
                rules=[RequirementRule(credits=group_credits, description=heading, course_codes=codes)]
                if codes else [],
                raw_text=heading,
                notes=str(g.get("notes") or "").strip(),
                courses=kept,
            )
        )

    missing = sorted(present - captured)
    if missing:
        recovered = [
            RequirementCourse(code=m, credits=_credit_from_code(m), notes="") for m in missing
        ]
        groups.append(
            RequirementGroup(
                heading="Unclassified (recovered)",
                credits=0.0,
                is_note=False,
                course_codes=missing,
                rules=[RequirementRule(credits=0.0, description="LLM did not place these",
                                       course_codes=missing)],
                raw_text="",
                notes="Courses present in the source that the model did not place under a group.",
                courses=recovered,
            )
        )

    report = {
        "present": len(present),
        "captured": len(captured),
        "capture_pct": 100.0 if not present else round(len(captured) / len(present) * 100, 1),
        "hallucinated_dropped": sorted(hallucinated),
        "missing_recovered": missing,
        "groups": len(groups),
    }
    return groups, report


class GeminiGrouper:
    """Segments completion requirements using Google Gemini Flash structured output."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        session: requests.Session | None = None,
        timeout: int = 60,
    ) -> None:
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model = model or os.environ.get("GEMINI_MODEL", _DEFAULT_MODEL)
        self.timeout = timeout
        self._session = session or requests.Session()

    def group(self, completion_html: str) -> GroupingResult:
        text = strip_html(completion_html)
        raw = self._generate(text)
        groups, report = _validate_and_repair(raw, text)
        return GroupingResult(
            groups=groups,
            total_credits=float(raw.get("total_credits") or 0.0),
            report=report,
        )

    def _generate(self, text: str) -> dict:
        if not self.api_key:
            raise GeminiNotConfiguredError("Gemini API key not configured on the server.")
        payload = {
            "contents": [{"parts": [{"text": _PROMPT.format(text=text)}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": _RESPONSE_SCHEMA,
                "temperature": 0,
            },
        }
        response = self._call_api(payload)
        try:
            candidates = response["candidates"]
        except KeyError as exc:
            raise GeminiResponseError("Gemini returned an unparseable response.") from exc
        if not candidates:
            reason = str(response.get("promptFeedback", {}).get("blockReason") or "no candidates")
            raise GeminiResponseError(f"Gemini returned an unparseable response: {reason}.")
        try:
            parts = candidates[0]["content"]["parts"]
            payload_text = "".join(p.get("text", "") for p in parts)
        except (KeyError, IndexError, TypeError) as exc:
            raise GeminiResponseError("Gemini returned an unparseable response.") from exc
        try:
            return json.loads(_extract_json_text(payload_text))
        except json.JSONDecodeError as exc:
            raise GeminiResponseError(f"Gemini returned an unparseable response: {exc}") from exc

    def _call_api(self, payload: dict) -> dict:
        """The single HTTP boundary (mocked in tests).

        Authenticates with the ``X-goog-api-key`` header and retries on 429
        (rate/quota) and 503 (transient overload), honouring the server's
        ``retryDelay`` when present.
        """
        url = f"{_GEMINI_BASE}/models/{self.model}:generateContent"
        headers = {"Content-Type": "application/json", "X-goog-api-key": self.api_key or ""}
        last_err = ""
        for attempt in range(_MAX_RETRIES):
            try:
                resp = self._session.post(url, headers=headers, json=payload, timeout=self.timeout)
            except requests.RequestException as exc:
                last_err = str(exc)
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(2 ** attempt + 1)
                    continue
                raise GeminiRequestError(f"Gemini rejected the request: {exc}") from exc

            if resp.status_code in _RETRY_STATUS and attempt < _MAX_RETRIES - 1:
                time.sleep(min(_retry_delay(resp) or (2 ** attempt + 1), 20))
                last_err = f"HTTP {resp.status_code}"
                continue
            try:
                resp.raise_for_status()
            except requests.HTTPError as exc:
                raise GeminiRequestError(
                    f"Gemini rejected the request: {exc}: {resp.text[:200]}"
                ) from exc
            return resp.json()
        raise GeminiRequestError(f"Gemini rejected the request after {_MAX_RETRIES} retries ({last_err}).")


# ------------------------------------------------------------- heuristic fallback
_GROUP_MARKER_RE = re.compile(r"\bGroup\s+[A-Z0-9]", re.IGNORECASE)
_YEAR_MARKER_RE = re.compile(
    r"\b(First|Second|Third|Fourth|Higher|Upper|Lower)\s+[Yy]ear", re.IGNORECASE
)


def looks_under_segmented(completion_text: str, groups: list[RequirementGroup]) -> bool:
    """Heuristic: does the source clearly have >=2 sections the parser collapsed?

    Used to decide when to spend an LLM call: only when the deterministic parser
    produced fewer groups than the source's obvious Group/Year section markers.
    """
    markers = len(set(_GROUP_MARKER_RE.findall(completion_text or ""))) + len(
        _YEAR_MARKER_RE.findall(completion_text or "")
    )
    return markers >= 2 and len(groups) < markers


if __name__ == "__main__":  # pragma: no cover - manual smoke over a corpus
    import sys

    from backend.config import load_env

    load_env()  # pick up GEMINI_API_KEY / GEMINI_MODEL from .env
    corpus = sys.argv[1] if len(sys.argv) > 1 else None
    if not corpus:
        print("usage: python -m backend.data_sources.llm_grouper <corpus.jsonl> [limit]")
        raise SystemExit(2)
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    grouper = GeminiGrouper()
    with open(corpus, encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if i >= limit:
                break
            rec = json.loads(line)
            res = grouper.group(rec.get("completion_html", ""))
            print(f"\n=== {rec.get('code')} — {len(res.groups)} groups, "
                  f"{res.report['capture_pct']}% capture ===")
            for g in res.groups:
                print(f"  [{g.heading or '(intro)'}] {len(g.course_codes)} courses")
