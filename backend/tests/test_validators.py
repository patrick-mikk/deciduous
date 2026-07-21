"""Unit tests for `backend/planner/{validators,prereqs,gpa}.py`.

Pure-function engine — no network, no DB. Runnable both as:
    python -m pytest backend/tests/test_validators.py
    python backend/tests/test_validators.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest  # noqa: E402

from backend.planner import gpa, prereqs, validators  # noqa: E402
from backend.planner.types import (  # noqa: E402
    CourseRecord,
    CourseRequirementText,
    ProgramRequirement,
)

# ---------------------------------------------------------------------------
# prereqs.py
# ---------------------------------------------------------------------------


def test_parse_requirement_and_group_in_parens():
    # Real TTB example (backend/docs/TTB_API_REFERENCE.md):
    # "(MAT223H1,MAT224H1)/ MAT247H1" -> (223 AND 224) OR 247
    tree = prereqs.parse_requirement("<p>(MAT223H1,MAT224H1)/ MAT247H1</p>")
    assert prereqs.evaluate(tree, {"MAT247H1"})
    assert prereqs.evaluate(tree, {"MAT223H1", "MAT224H1"})
    assert not prereqs.evaluate(tree, {"MAT223H1"})
    assert not prereqs.evaluate(tree, set())


def test_parse_requirement_plain_or_list():
    tree = prereqs.parse_requirement("POL200Y1/ POL201Y1/ POL208H1")
    assert prereqs.referenced_codes(tree) == {"POL200Y1", "POL201Y1", "POL208H1"}
    assert prereqs.evaluate(tree, {"POL208H1"})
    assert not prereqs.evaluate(tree, {"ECO100Y1"})


def test_parse_requirement_and_via_comma_and_word_and():
    tree = prereqs.parse_requirement("ECO101H1, ECO102H1")
    assert prereqs.evaluate(tree, {"ECO101H1", "ECO102H1"})
    assert not prereqs.evaluate(tree, {"ECO101H1"})

    tree2 = prereqs.parse_requirement("ECO101H1 and ECO102H1")
    assert prereqs.evaluate(tree2, {"ECO101H1", "ECO102H1"})
    assert not prereqs.evaluate(tree2, {"ECO102H1"})


def test_parse_requirement_free_text_is_unverifiable_but_satisfied():
    tree = prereqs.parse_requirement("Permission of the instructor")
    assert prereqs.has_unverifiable_text(tree)
    assert prereqs.evaluate(tree, set())  # can't check -> doesn't block


def test_parse_requirement_empty_text():
    tree = prereqs.parse_requirement("")
    assert tree is prereqs.EMPTY
    assert prereqs.evaluate(tree, set())
    assert prereqs.referenced_codes(tree) == frozenset()

    assert prereqs.parse_requirement(None) is prereqs.EMPTY


def test_missing_alternatives_reports_cheapest_options():
    tree = prereqs.parse_requirement("(MAT223H1,MAT224H1)/ MAT247H1")
    options = prereqs.missing_alternatives(tree, set())
    assert frozenset({"MAT247H1"}) in options
    assert frozenset({"MAT223H1", "MAT224H1"}) in options
    assert prereqs.missing_alternatives(tree, {"MAT247H1"}) == []


def test_prerequisite_corequisite_exclusion_wrappers():
    assert prereqs.prerequisite_met("POL208H1", {"POL208H1"})
    assert not prereqs.prerequisite_met("POL208H1", set())

    assert prereqs.corequisite_met("STA220H1", set(), {"STA220H1"})
    assert not prereqs.corequisite_met("STA220H1", set(), set())

    assert prereqs.excluded_conflict("POL109H1/ POL109Y1", {"POL109H1", "ECO101H1"}) == {"POL109H1"}
    assert prereqs.excluded_conflict("POL109H1", {"ECO101H1"}) == frozenset()


def test_validate_plan_prerequisites_end_to_end():
    course_texts = {
        "POL208H1": CourseRequirementText(code="POL208H1", prerequisites="POL200Y1"),
        "POL305H1": CourseRequirementText(code="POL305H1", prerequisites="POL208H1"),
    }
    records = [
        CourseRecord(code="POL200Y1", credits=1.0, status="completed", session="20259-20261"),
        CourseRecord(code="POL208H1", credits=0.5, status="planned", session="20269"),
        CourseRecord(code="POL305H1", credits=0.5, status="planned", session="20269"),  # same term!
    ]
    issues = prereqs.validate_plan_prerequisites(records, course_texts)
    kinds = {(i.code, i.course_code) for i in issues}
    assert ("prerequisite", "POL305H1") in kinds  # POL208H1 is same-term, not prior
    assert ("prerequisite", "POL208H1") not in kinds  # POL200Y1 already completed


def test_validate_plan_prerequisites_unknown_course_is_skipped():
    records = [CourseRecord(code="XYZ999H1", credits=0.5, status="planned", session="20269")]
    assert prereqs.validate_plan_prerequisites(records, {}) == []


def test_validate_plan_prerequisites_exclusion_conflict():
    course_texts = {
        "POL109H1": CourseRequirementText(code="POL109H1", exclusions="POL109Y1"),
    }
    records = [
        CourseRecord(code="POL109H1", credits=0.5, status="planned", session="20269"),
        CourseRecord(code="POL109Y1", credits=1.0, status="completed", session="20259-20261"),
    ]
    issues = prereqs.validate_plan_prerequisites(records, course_texts)
    assert any(i.code == "exclusion" for i in issues)


def test_session_strictly_before():
    assert prereqs.session_strictly_before("20259-20261", "20269")  # prior year -> Fall 2026
    assert not prereqs.session_strictly_before("20269", "20269")
    assert not prereqs.session_strictly_before("20271", "20269")


# ---------------------------------------------------------------------------
# gpa.py
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mark,letter,points",
    [
        (95, "A+", 4.0),
        (90, "A+", 4.0),
        (87, "A", 4.0),
        (82, "A-", 3.7),
        (78, "B+", 3.3),
        (74, "B", 3.0),
        (71, "B-", 2.7),
        (68, "C+", 2.3),
        (64, "C", 2.0),
        (61, "C-", 1.7),
        (58, "D+", 1.3),
        (54, "D", 1.0),
        (51, "D-", 0.7),
        (49, "F", 0.0),
        (0, "F", 0.0),
        (100, "A+", 4.0),
    ],
)
def test_grade_scale_bands(mark, letter, points):
    assert gpa.letter_for_mark(mark) == letter
    assert gpa.points_for_mark(mark) == points


def test_grade_scale_out_of_range_raises():
    with pytest.raises(ValueError):
        gpa.letter_for_mark(101)
    with pytest.raises(ValueError):
        gpa.letter_for_mark(-1)


def test_grade_points_prefers_grade_over_mark():
    record = CourseRecord(code="POL208H1", credits=0.5, status="completed", grade="A-", mark=60)
    points, counts = gpa.grade_points(record)
    assert points == 3.7
    assert counts


@pytest.mark.parametrize("notation", sorted(gpa.NOTATIONS_EXCLUDED_FROM_GPA))
def test_grade_points_excludes_notations(notation):
    record = CourseRecord(code="POL208H1", credits=0.5, status="completed", grade=notation)
    points, counts = gpa.grade_points(record)
    assert points is None
    assert not counts


def test_grade_points_fl_counts_as_zero():
    record = CourseRecord(code="POL208H1", credits=0.5, status="completed", grade="FL")
    points, counts = gpa.grade_points(record)
    assert points == 0.0
    assert counts


def test_grade_points_planned_and_extra_never_count():
    planned = CourseRecord(code="POL208H1", credits=0.5, status="planned", grade="A+")
    extra = CourseRecord(code="POL208H1", credits=0.5, status="extra", grade="A+")
    assert gpa.grade_points(planned) == (None, False)
    assert gpa.grade_points(extra) == (None, False)


def test_grade_points_unresolvable_course():
    record = CourseRecord(code="POL208H1", credits=0.5, status="completed")
    assert gpa.grade_points(record) == (None, False)


def test_is_passing():
    assert gpa.is_passing(CourseRecord(code="A", credits=0.5, grade="CR"))
    assert not gpa.is_passing(CourseRecord(code="A", credits=0.5, grade="NCR"))
    assert gpa.is_passing(CourseRecord(code="A", credits=0.5, mark=50))
    assert not gpa.is_passing(CourseRecord(code="A", credits=0.5, mark=49))
    assert gpa.is_passing(CourseRecord(code="A", credits=0.5, grade="D-"))
    assert not gpa.is_passing(CourseRecord(code="A", credits=0.5, grade="F"))


def test_compute_gpa_weighted_average():
    records = [
        CourseRecord(code="A", credits=1.0, status="completed", grade="A+"),  # 4.0 * 1.0
        CourseRecord(code="B", credits=0.5, status="completed", grade="C"),  # 2.0 * 0.5
        CourseRecord(code="C", credits=0.5, status="completed", grade="CR"),  # excluded
        CourseRecord(code="D", credits=0.5, status="planned", grade="A+"),  # excluded (not taken)
    ]
    summary = gpa.compute_gpa(records)
    # (4.0*1.0 + 2.0*0.5) / 1.5 = 5.0 / 1.5
    assert summary.gpa == pytest.approx(3.333, abs=1e-2)
    assert summary.credits_counted == 1.5
    assert summary.courses_counted == 2


def test_compute_gpa_no_countable_credits():
    summary = gpa.compute_gpa([CourseRecord(code="A", credits=0.5, status="planned")])
    assert summary.gpa is None
    assert summary.credits_counted == 0.0


def test_sgpa_agpa_cgpa_session_filtering():
    records = [
        CourseRecord(code="A", credits=0.5, status="completed", grade="A+", session="20269"),
        CourseRecord(code="B", credits=0.5, status="completed", grade="F", session="20271"),
        CourseRecord(code="C", credits=0.5, status="completed", grade="A+", session="20255"),
    ]
    assert gpa.sgpa(records, "20269").gpa == 4.0
    assert gpa.agpa(records, ["20269", "20271"]).gpa == pytest.approx(2.0)
    assert gpa.cgpa(records).courses_counted == 3


def test_academic_standing():
    assert gpa.academic_standing(1.6, 0.0) == "good"
    assert gpa.academic_standing(1.2, 1.8) == "probation"
    assert gpa.academic_standing(1.0, 1.0) == "suspension"
    assert gpa.academic_standing(1.0, 1.0, previously_suspended=True) == "refused"


def test_max_credits_for_term():
    assert gpa.max_credits_for_term("probation", "fall") == 2.5
    assert gpa.max_credits_for_term("probation", "summer") == 1.0
    assert gpa.max_credits_for_term("good", "fall") is None
    assert gpa.max_credits_for_term("suspension", "fall") == 0.0
    with pytest.raises(ValueError):
        gpa.max_credits_for_term("good", "spring")


def test_meets_graduation_gpa():
    assert gpa.meets_graduation_gpa(1.85)
    assert not gpa.meets_graduation_gpa(1.84)


# ---------------------------------------------------------------------------
# validators.py — degree credit checks
# ---------------------------------------------------------------------------


def _completed(code, credits, **kw):
    return CourseRecord(code=code, credits=credits, status="completed", **kw)


def test_effective_courses_dedupes_and_drops_extra():
    records = [
        _completed("POL208H1", 0.5),
        CourseRecord(code="POL208H1", credits=0.5, status="planned"),  # dup, lower priority
        CourseRecord(code="ECO100Y1", credits=1.0, status="extra"),
    ]
    result = validators.effective_courses(records)
    codes = {c.code for c in result}
    assert codes == {"POL208H1"}
    assert result[0].status == "completed"


def test_parse_breadth_category():
    assert validators.parse_breadth_category("Society and Its Institutions (3)") == 3
    assert validators.parse_breadth_category("No breadth here") is None
    assert validators.breadth_categories_from_labels(
        ["Society and Its Institutions (3)", "The Physical and Mathematical Universes (5)"]
    ) == (3, 5)


def test_degree_credit_summary_basic():
    records = [
        _completed("POL101Y1", 1.0, distribution=("Arts",)),
        _completed("POL208H1", 0.5, distribution=("Arts",)),
        _completed("POL305H1", 0.5, distribution=("Arts",)),
        _completed("MAT135H1", 0.5, distribution=("Science",)),
    ]
    summary = validators.degree_credit_summary(records)
    assert summary.total_credits == 2.5
    assert summary.artsci_credits == 2.5
    assert summary.level_200_plus_credits == 1.0
    assert summary.level_300_plus_credits == 0.5
    assert summary.credits_by_subject["POL"] == 2.0


def test_degree_credit_summary_transfer_cap_on_300_plus():
    records = [
        _completed("XYZ301H1", 0.5, is_transfer_credit=True),
        _completed("XYZ302H1", 0.5, is_transfer_credit=True),
        _completed("XYZ303H1", 0.5, is_transfer_credit=True, is_uoft_exchange=True),
    ]
    summary = validators.degree_credit_summary(records)
    # Non-exchange transfer 300+ capped at 1.0 total (of 1.0 actual) + exchange 0.5 uncapped.
    assert summary.level_300_plus_credits == 1.5


def test_degree_credit_summary_same_subject_cap():
    records = [_completed(f"POL{200+i}H1", 0.5) for i in range(32)]  # 16.0 credits of POL
    summary = validators.degree_credit_summary(records)
    assert "POL" in summary.same_subject_over_cap
    assert summary.same_subject_over_cap["POL"] == 16.0


def test_validate_degree_credits_reports_gaps_and_cap_violation():
    summary = validators.DegreeCreditSummary(
        total_credits=5.0,
        artsci_credits=5.0,
        level_200_plus_credits=1.0,
        level_300_plus_credits=0.0,
        credits_by_subject={"POL": 16.0},
        same_subject_over_cap={"POL": 16.0},
    )
    issues = validators.validate_degree_credits(summary)
    codes = {i.code: i.severity for i in issues}
    assert codes["credits-total"] == "info"
    assert codes["same-subject-cap"] == "error"


def test_validate_degree_credits_all_clear():
    summary = validators.DegreeCreditSummary(
        total_credits=20.0,
        artsci_credits=10.0,
        level_200_plus_credits=13.0,
        level_300_plus_credits=6.0,
        credits_by_subject={"POL": 5.0},
        same_subject_over_cap={},
    )
    assert validators.validate_degree_credits(summary) == []


# ---------------------------------------------------------------------------
# validators.py — program combination
# ---------------------------------------------------------------------------


def test_evaluate_program_combination_two_majors_valid():
    programs = [
        ProgramRequirement(
            code="ASMAJ1305A",
            program_type="major",
            subject="1305",
            total_credits=6.0,
            course_codes=frozenset({"POL101Y1", "POL208H1", "POL305H1"}),
        ),
        ProgramRequirement(
            code="ASMAJ2660A",
            program_type="major",
            subject="2660",
            total_credits=6.0,
            course_codes=frozenset({"PPG301H1"}),
        ),
    ]
    records = [
        _completed("POL101Y1", 1.0),
        _completed("POL208H1", 0.5),
        _completed("POL305H1", 0.5),
        _completed("PPG301H1", 0.5),
    ]
    result, issues = validators.evaluate_program_combination(programs, records)
    assert result.combo_type == "two_majors"
    assert result.combo_valid
    assert not result.one_type_per_subject_violations
    # distinct credits = 2.5 (all four are distinct, none shared) < 12.0
    assert not result.distinct_credits_ok
    assert any(i.code == "distinct-credits" for i in issues)


def test_evaluate_program_combination_invalid_shape():
    programs = [
        ProgramRequirement(code="ASMIN0001", program_type="minor", subject="0001", total_credits=4.0)
    ]
    result, issues = validators.evaluate_program_combination(programs, [])
    assert result.combo_type is None
    assert not result.combo_valid
    assert any(i.code == "program-combination" for i in issues)


def test_evaluate_program_combination_one_type_per_subject_violation():
    programs = [
        ProgramRequirement(code="ASMAJ1305A", program_type="major", subject="1305", total_credits=6.0),
        ProgramRequirement(code="ASMIN1305", program_type="minor", subject="1305", total_credits=4.0),
    ]
    result, issues = validators.evaluate_program_combination(programs, [])
    assert "1305" in result.one_type_per_subject_violations
    assert any(i.code == "one-type-per-subject" for i in issues)


def test_evaluate_program_combination_upper_level_minimums():
    programs = [
        ProgramRequirement(
            code="ASMAJ1305A",
            program_type="major",
            subject="1305",
            total_credits=6.0,
            course_codes=frozenset({"POL101Y1", "POL208H1", "POL305H1"}),
        ),
    ]
    # Only a 100-level course completed: earns credit but not the 300+/400+ minimums.
    records = [_completed("POL101Y1", 1.0)]
    result, _ = validators.evaluate_program_combination(programs, records)
    pp = result.program_progress[0]
    assert not pp.meets_credit_target  # 1.0 earned < 6.0 target
    assert not pp.meets_upper_level_minimums  # 0 at 300+ < 2.0 required


# ---------------------------------------------------------------------------
# validators.py — unparsed-program exclusion + nonstandard combinations
# (issue #2: 4 declared majors reporting a false "0.0 distinct credits")
# ---------------------------------------------------------------------------


def test_unparsed_program_excluded_from_distinct_credits_and_flagged():
    """An enrolled program whose requirements never parsed (empty
    course_codes with requirements_parsed=False) must NOT silently drop the
    distinct-credits total to whatever the *other* programs contribute with
    no explanation -- it must be excluded and reported, per issue #2."""
    programs = [
        ProgramRequirement(
            code="ASMAJ1478",
            program_type="major",
            subject="1478",
            total_credits=8.0,
            title="Economics Major",
            course_codes=frozenset(),  # never parsed
            requirements_parsed=False,
        ),
        ProgramRequirement(
            code="ASMAJ2660A",
            program_type="major",
            subject="2660",
            total_credits=6.0,
            title="Public Policy Major",
            course_codes=frozenset({"PPG301H1", "PPG302H1"}),
        ),
        ProgramRequirement(
            code="ASMAJ2001A",
            program_type="major",
            subject="2001",
            total_credits=6.0,
            title="Urban Studies Major",
            course_codes=frozenset({"URB201H1"}),
        ),
    ]
    records = [
        _completed("ECO101H1", 0.5),
        _completed("PPG301H1", 0.5),
        _completed("PPG302H1", 0.5),
        _completed("URB201H1", 0.5),
    ]
    result, issues = validators.evaluate_program_combination(programs, records)

    assert result.unparsed_programs == ["ASMAJ1478"]
    # Only the two PARSED programs' covered credits count -- ECO101H1 doesn't
    # silently count as "0 shared credits", it's excluded from the math.
    assert result.distinct_credits == 1.5  # PPG301H1 + PPG302H1 + URB201H1 only
    unparsed_issues = [i for i in issues if i.code == "requirements-unparsed"]
    assert len(unparsed_issues) == 1
    assert unparsed_issues[0].course_code == "ASMAJ1478"
    assert "Economics Major" in unparsed_issues[0].message
    assert "not yet parsed" in unparsed_issues[0].message


def test_four_majors_is_a_nonstandard_but_valid_combination():
    """4 majors exceeds any standard shape (1 Specialist / 2 Majors / 1 Major
    + 2 Minors), but 2 of the 4 already satisfy the 2-Major pattern -- this
    must be recognized as valid + informational, not mis-flagged as an
    invalid/incomplete combination (issue #2)."""
    programs = [
        ProgramRequirement(code="ASMAJ1478", program_type="major", subject="1478", total_credits=8.0),
        ProgramRequirement(code="ASMAJ2001", program_type="major", subject="2001", total_credits=6.0),
        ProgramRequirement(code="ASMAJ2660", program_type="major", subject="2660", total_credits=6.0),
        ProgramRequirement(code="ASMAJ3001", program_type="major", subject="3001", total_credits=6.0),
    ]
    result, issues = validators.evaluate_program_combination(programs, [])

    assert result.combo_type == "two_majors"
    assert result.combo_valid
    assert not any(i.code == "program-combination" for i in issues)  # not "invalid"
    nonstandard = [i for i in issues if i.code == "program-combination-nonstandard"]
    assert len(nonstandard) == 1
    assert nonstandard[0].severity == "info"
    assert "4 programs" in nonstandard[0].message
    assert "2 of your 4 majors" in nonstandard[0].message


# ---------------------------------------------------------------------------
# validators.py — breadth
# ---------------------------------------------------------------------------


def test_evaluate_breadth_satisfied_4_of_5():
    records = [
        CourseRecord(code=f"C{i}", credits=1.0, status="completed", breadth_categories=(i,))
        for i in (1, 2, 3, 4)
    ]
    result = validators.evaluate_breadth(records)
    assert result.satisfied
    assert result.satisfied_via == "4-of-5"
    assert result.cheapest_additional_credits == 0.0


def test_evaluate_breadth_satisfied_3_plus_2():
    records = [
        CourseRecord(code="C1", credits=1.0, status="completed", breadth_categories=(1,)),
        CourseRecord(code="C2", credits=1.0, status="completed", breadth_categories=(2,)),
        CourseRecord(code="C3", credits=1.0, status="completed", breadth_categories=(3,)),
        CourseRecord(code="C4", credits=0.5, status="completed", breadth_categories=(4,)),
        CourseRecord(code="C5", credits=0.5, status="completed", breadth_categories=(5,)),
    ]
    result = validators.evaluate_breadth(records)
    assert result.satisfied
    assert result.satisfied_via == "3-plus-2"


def test_evaluate_breadth_unsatisfied_reports_cheapest_path():
    records = [
        CourseRecord(code="C1", credits=1.0, status="completed", breadth_categories=(1,)),
    ]
    result = validators.evaluate_breadth(records)
    assert not result.satisfied
    assert result.cheapest_additional_credits > 0
    assert sum(result.cheapest_path.values()) == pytest.approx(result.cheapest_additional_credits)


def test_evaluate_breadth_y_course_splits_across_two_categories():
    record = CourseRecord(code="Y1", credits=1.0, status="completed", breadth_categories=(1, 2))
    allocations = validators.allocate_breadth_credits(record)
    assert {a.category: a.credits for a in allocations} == {1: 0.5, 2: 0.5}


def test_evaluate_breadth_excludes_extra():
    records = [CourseRecord(code="C1", credits=1.0, status="extra", breadth_categories=(1,))]
    result = validators.evaluate_breadth(records)
    assert result.earned_by_category[1] == 0.0


def test_evaluate_breadth_no_categories_no_allocation():
    assert validators.allocate_breadth_credits(CourseRecord(code="C1", credits=0.5, status="completed")) == []


# ---------------------------------------------------------------------------
# validators.py — graduation eligibility (composition)
# ---------------------------------------------------------------------------


def test_graduation_eligibility_not_yet_eligible():
    records = [_completed("POL101Y1", 1.0, distribution=("Arts",))]
    result = validators.graduation_eligibility(records, [], cgpa_value=1.2, standing="probation")
    assert not result.eligible
    assert result.checklist["credits-20"] is False
    assert result.checklist["cgpa-1.85"] is False
    assert result.checklist["good-standing"] is False
    assert result.issues  # something explains why


def test_graduation_eligibility_fully_eligible():
    # Credits by level: 100=7.0, 200=6.5, 300=5.0, 400=1.5 -> total 20.0,
    # 200+ = 13.0, 300+ = 6.5 (all §1 thresholds cleared; each subject tops
    # out at 7.0, well under the 15.0 same-subject cap).
    level100 = [_completed(f"AAA1{i:02d}H1", 0.5, distribution=("Arts",)) for i in range(14)]
    level200 = [_completed(f"BBB2{i:02d}H1", 0.5, distribution=("Arts",)) for i in range(13)]
    level300 = [_completed(f"CCC3{i:02d}H1", 0.5, distribution=("Arts",)) for i in range(10)]
    level400 = [_completed(f"DDD4{i:02d}H1", 0.5, distribution=("Arts",)) for i in range(3)]
    breadth_records = [
        CourseRecord(code=f"BRC{cat}", credits=1.0, status="completed", breadth_categories=(cat,))
        for cat in (1, 2, 3, 4)
    ]
    all_records = level100 + level200 + level300 + level400 + breadth_records

    # A single Specialist covering the 200/300/400-level courses: 13.0
    # earned (>= the 10.0 minimum), 6.5 at 300+ (>= 4.0), 1.5 at 400+ (>= 1.0).
    program_codes = frozenset(c.code for c in (level200 + level300 + level400))
    programs = [
        ProgramRequirement(
            code="ASSPE0001A",
            program_type="specialist",
            subject="0001",
            total_credits=10.0,
            course_codes=program_codes,
        )
    ]

    result = validators.graduation_eligibility(all_records, programs, cgpa_value=3.0, standing="good")
    assert result.checklist["credits-20"]
    assert result.checklist["artsci-10"]
    assert result.checklist["level-200-13"]
    assert result.checklist["level-300-6"]
    assert result.checklist["same-subject-cap"]
    assert result.checklist["breadth"]
    assert result.checklist["cgpa-1.85"]
    assert result.checklist["good-standing"]
    assert result.checklist["program-combination"]
    assert result.checklist["program-progress"]
    assert result.eligible


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
