"""Tests for the program-completion single source of truth.

Regression coverage for the bug where a program's top-of-page summary
("X / 0.0 cr", "0% complete") disagreed with its own per-group requirement
breakdown. Both must now come from the same engine (`effective_total_credits`
for the denominator, deduped-union earned in `program_progress_summary`).
"""
from __future__ import annotations

from backend.api._audit import (
    ProgramRow,
    TranscriptRow,
    effective_total_credits,
    program_progress_summary,
    requirement_progress,
)
from backend.data_sources.models import Program, RequirementGroup


def _group(heading: str, credits: float, codes: list[str]) -> RequirementGroup:
    return RequirementGroup(
        heading=heading,
        credits=credits,
        is_note=False,
        course_codes=codes,
        rules=[],
        raw_text="",
        notes="",
        courses=[],
    )


def _econ_shaped_program(total_credits: float = 0.0) -> Program:
    """A program like the Economics Major (ASMAJ1478): no stated program-level
    total, an umbrella "Program Course Requirements 7.0" group, and a
    "Second Year (Core Courses) 3.0" sub-group whose courses are ALSO in the
    umbrella (the source of the double-count)."""
    core = ["ECO200Y1", "ECO220Y1", "ECO101H1", "ECO102H1", "MAT133Y1"]
    return Program(
        code="ASMAJ1478",
        title="Economics Major",
        program_type="major",
        department="Economics",
        department_url="",
        enrolment_requirements="Students must have completed 4.0 credits to enrol.",
        total_credits=total_credits,
        completion_requirements=[
            _group("Program Course Requirements", 7.0, core),
            _group("Second Year (Core Courses)", 3.0, ["ECO200Y1", "ECO220Y1"]),
        ],
        raw_completion_text="",
    )


def test_effective_total_credits_falls_back_to_umbrella_group_not_sum():
    """A 0.0 stated total must not surface as 0.0, and must not be the naive
    sum of overlapping groups (7.0 + 3.0 = 10.0) — the umbrella (7.0) is the
    real total and matches what the breakdown shows."""
    program = _econ_shaped_program(total_credits=0.0)
    assert effective_total_credits(program) == 7.0


def test_effective_total_credits_prefers_stated_total():
    program = _econ_shaped_program(total_credits=8.0)
    assert effective_total_credits(program) == 8.0


def test_effective_total_credits_uses_min_credits_when_no_groups_state_credits():
    program = Program(
        code="ASMIN9999",
        title="Empty Minor",
        program_type="minor",
        department="X",
        department_url="",
        enrolment_requirements="",
        total_credits=0.0,
        completion_requirements=[_group("Requirements", 0.0, ["XXX100H1"])],
        raw_completion_text="",
    )
    # minor floor is 4.0 (PROGRAM_MIN_CREDITS)
    assert effective_total_credits(program) == 4.0


def test_summary_denominator_matches_breakdown_umbrella():
    program = _econ_shaped_program(total_credits=0.0)
    rows: list[TranscriptRow] = []
    summary = program_progress_summary(program, ProgramRow(code=program.code), rows)
    breakdown = requirement_progress(program, rows)
    umbrella = next(g for g in breakdown if g["label"] == "Program Course Requirements")
    # The top-of-page denominator equals the umbrella group's required credits —
    # they can no longer disagree (7.0, never 0.0).
    assert summary["totalCredits"] == umbrella["required"] == 7.0


def test_summary_earned_is_deduped_union_not_double_counted():
    """A course in both the umbrella and the sub-group must count once toward
    the program total — the old top card summed per-group earned and inflated
    it."""
    program = _econ_shaped_program(total_credits=0.0)
    rows = [
        TranscriptRow(code="ECO101H1", credits=0.5, status="completed", session="20249", grade="A", mark=85, is_artsci=True),
        TranscriptRow(code="ECO102H1", credits=0.5, status="completed", session="20251", grade="B", mark=75, is_artsci=True),
        TranscriptRow(code="ECO200Y1", credits=1.0, status="completed", session="20261", grade="C+", mark=67, is_artsci=True),
    ]
    summary = program_progress_summary(program, ProgramRow(code=program.code), rows)
    breakdown = requirement_progress(program, rows)
    naive_sum = round(sum(g["earned"] for g in breakdown), 2)

    # Deduped union: ECO101 + ECO102 + ECO200 counted once each.
    assert summary["earnedCredits"] == 1.5
    # The naive per-group sum double-counts ECO200 (in both groups) -> 2.0.
    assert naive_sum > summary["earnedCredits"]
    # Percent is real and bounded, never 0% for genuine progress.
    assert summary["percent"] == round(1.5 / 7.0 * 100, 1)
    assert summary["loaded"] is True


def test_summary_unloaded_program_reports_not_loaded():
    summary = program_progress_summary(None, ProgramRow(code="ASMAJ0000"), [])
    assert summary["loaded"] is False
    assert summary["totalCredits"] == 0.0
    assert summary["percent"] == 0.0
