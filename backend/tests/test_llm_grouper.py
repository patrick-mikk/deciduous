"""Offline tests for the Gemini LLM grouper.

The single HTTP boundary (`GeminiGrouper._call_api`) is monkeypatched to return a
canned Gemini response, so nothing here touches the network. A live smoke that
actually calls Gemini is included but skipped unless GEMINI_API_KEY is set.

Runnable both ways:
    python -m pytest backend/tests/test_llm_grouper.py -q
    python backend/tests/test_llm_grouper.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.data_sources.llm_grouper import (  # noqa: E402
    GeminiGrouper,
    GroupingResult,
    looks_under_segmented,
    _credit_from_code,
    _validate_and_repair,
)
from backend.data_sources.models import RequirementCourse, RequirementGroup  # noqa: E402

# A completion field with three real courses across two obvious sections.
# GGR172H1/GGR272H1 are 0.5-credit (H); ABP100Y1 would be 1.0 (Y) - used below.
_SOURCE_HTML = (
    "<p>(7.0 credits)</p>"
    "<p>First Year: <a href='/course/GGR172H1'>GGR172H1</a></p>"
    "<p>Group A: Methods <a href='/course/GGR272H1'>GGR272H1</a>, "
    "<a href='/course/GGR274H1'>GGR274H1</a></p>"
)


def _course(code: str, notes: str = "") -> dict:
    return {"code": code, "notes": notes}


def _fake_gemini(groups: list[dict], total_credits: float = 7.0) -> dict:
    text = json.dumps({"total_credits": total_credits, "groups": groups})
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def _grouper_returning(payload: dict) -> GeminiGrouper:
    g = GeminiGrouper(api_key="test-key")
    g._call_api = lambda _payload: payload  # type: ignore[assignment]
    return g


def _all_codes(result: GroupingResult) -> set[str]:
    return {c for grp in result.groups for c in grp.course_codes}


def test_maps_llm_groups_to_requirement_groups() -> None:
    g = _grouper_returning(_fake_gemini([
        {"heading": "First Year", "credits": 1.0, "is_note": False, "notes": "",
         "courses": [_course("GGR172H1")]},
        {"heading": "Group A: Methods", "credits": 1.5, "is_note": False, "notes": "",
         "courses": [_course("GGR272H1"), _course("GGR274H1")]},
    ]))
    result = g.group(_SOURCE_HTML)
    assert isinstance(result, GroupingResult)
    assert result.total_credits == 7.0
    assert [grp.heading for grp in result.groups] == ["First Year", "Group A: Methods"]
    assert all(isinstance(grp, RequirementGroup) for grp in result.groups)
    assert result.report["capture_pct"] == 100.0


def test_per_course_credits_are_included() -> None:
    g = _grouper_returning(_fake_gemini([
        {"heading": "First Year", "credits": 0.5, "is_note": False, "notes": "",
         "courses": [_course("GGR172H1")]},
    ]))
    result = g.group(_SOURCE_HTML)
    first = result.groups[0]
    assert first.courses  # per-course detail present
    assert isinstance(first.courses[0], RequirementCourse)
    assert first.courses[0].code == "GGR172H1"
    assert first.courses[0].credits == 0.5  # H -> 0.5, derived from the code
    # sanity on the credit deriver itself
    assert _credit_from_code("ABP100Y1") == 1.0
    assert _credit_from_code("POL208H1") == 0.5


def test_notes_on_group_and_course_are_included() -> None:
    g = _grouper_returning(_fake_gemini([
        {"heading": "Group A", "credits": 1.5, "is_note": False,
         "notes": "Choose courses from at least two departments.",
         "courses": [
             _course("GGR272H1", notes="recommended for the methods stream"),
             _course("GGR274H1"),
         ]},
    ]))
    result = g.group(_SOURCE_HTML)
    grp = result.groups[0]
    assert grp.notes == "Choose courses from at least two departments."
    by_code = {c.code: c for c in grp.courses}
    assert by_code["GGR272H1"].notes == "recommended for the methods stream"
    assert by_code["GGR274H1"].notes == ""


def test_hallucinated_codes_are_dropped() -> None:
    g = _grouper_returning(_fake_gemini([
        {"heading": "First Year", "credits": 1.0, "is_note": False, "notes": "",
         "courses": [_course("GGR172H1")]},
        {"heading": "Group A", "credits": 1.5, "is_note": False, "notes": "",
         "courses": [_course("GGR272H1"), _course("GGR274H1"), _course("CSC999H1")]},
    ]))  # CSC999H1 is a valid-looking code NOT in the source
    result = g.group(_SOURCE_HTML)
    assert "CSC999H1" not in _all_codes(result)
    assert result.report["hallucinated_dropped"] == ["CSC999H1"]


def test_missing_codes_are_recovered_into_unclassified_group() -> None:
    # LLM omits GGR274H1 entirely -> it must be swept into a recovered group.
    g = _grouper_returning(_fake_gemini([
        {"heading": "First Year", "credits": 1.0, "is_note": False, "notes": "",
         "courses": [_course("GGR172H1")]},
        {"heading": "Group A", "credits": 1.5, "is_note": False, "notes": "",
         "courses": [_course("GGR272H1")]},
    ]))
    result = g.group(_SOURCE_HTML)
    assert _all_codes(result) == {"GGR172H1", "GGR272H1", "GGR274H1"}  # 100% guaranteed
    assert result.report["missing_recovered"] == ["GGR274H1"]
    recovered = next(g for g in result.groups if "Unclassified" in g.heading)
    assert recovered.courses[0].code == "GGR274H1"
    assert recovered.courses[0].credits == 0.5  # still gets its credit weight


def test_missing_api_key_raises() -> None:
    from backend.data_sources.llm_grouper import LLMGroupingError

    # Ensure no ambient key leaks in (e.g. a real exported GEMINI_API_KEY).
    saved = os.environ.pop("GEMINI_API_KEY", None)
    try:
        g = GeminiGrouper(api_key="")
        try:
            g.group(_SOURCE_HTML)
        except LLMGroupingError as exc:
            assert "GEMINI_API_KEY" in str(exc)
        else:
            raise AssertionError("expected LLMGroupingError when no API key is set")
    finally:
        if saved is not None:
            os.environ["GEMINI_API_KEY"] = saved


def test_looks_under_segmented_flags_collapsed_programs() -> None:
    text = "First Year: ... Group A: ... Group B: ... Group C: ..."
    one_group = [RequirementGroup("", 0.0, False, ["AAA100H1"], [], "")]
    assert looks_under_segmented(text, one_group) is True
    four_groups = [RequirementGroup(f"G{i}", 0.0, False, [], [], "") for i in range(4)]
    assert looks_under_segmented(text, four_groups) is False
    assert looks_under_segmented("0.5 credit from: AAA100H1, BBB200H1", one_group) is False


def test_validate_and_repair_is_pure_and_complete() -> None:
    raw = {"groups": [{"heading": "X", "credits": 0,
                       "courses": [_course("POL208H1"), _course("CSC999H1")]}]}
    groups, report = _validate_and_repair(raw, "POL208H1 and MAT137Y1 are required")
    codes = {c for g in groups for c in g.course_codes}
    assert codes == {"POL208H1", "MAT137Y1"}  # CSC999H1 dropped, MAT137Y1 recovered
    assert report["hallucinated_dropped"] == ["CSC999H1"]
    assert report["missing_recovered"] == ["MAT137Y1"]
    assert report["capture_pct"] == 50.0  # the LLM itself only placed 1 of 2


def test_live_smoke_gemini() -> None:
    """Real Gemini call; skipped unless GEMINI_API_KEY is set, and skipped (not
    failed) if the API is transiently unavailable/rate-limited — a live external
    smoke must not fail the suite on Gemini's uptime."""
    from backend.data_sources.llm_grouper import LLMGroupingError

    if not os.environ.get("GEMINI_API_KEY"):
        print("SKIPPED: set GEMINI_API_KEY to run the live Gemini smoke test")
        return
    try:
        result = GeminiGrouper().group(_SOURCE_HTML)
    except LLMGroupingError as exc:
        print(f"SKIPPED: Gemini API unavailable/rate-limited: {exc}")
        return
    assert _all_codes(result) == {"GGR172H1", "GGR272H1", "GGR274H1"}
    assert len(result.groups) >= 2


if __name__ == "__main__":
    for _name, _fn in sorted(globals().items()):
        if _name.startswith("test_") and callable(_fn):
            _fn()
            print(f"OK - {_name}")
    print("OK - all llm_grouper tests passed")
