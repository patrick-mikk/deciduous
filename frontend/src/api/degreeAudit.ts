/**
 * Pure helpers implementing the hard degree rules from
 * design/09-uoft-degree-rules.md §1, §4, §6. These are UI-glue re-implementations
 * of the same, small, deterministic logic the design bundle's `BreadthTracker`
 * carries internally as `evaluateBreadth` — that helper isn't exposed on the
 * bundle's public namespace (only the 87 components are), so it's reproduced
 * here rather than reaching into the vendored bundle's internals.
 *
 * The *authoritative* validators (full prereq/exclusion/program-combination
 * checks) belong in the backend; these are the lightweight client-side
 * versions used to render progress/audit UI from a StudentRecord.
 */
import { BREADTH_KEYS, type BreadthData, type DegreeAuditData, type Program, type RequirementProgress } from "./types";

/**
 * "Economics Major (ASMAJ1478)" -> "Economics" for plain-language
 * "Counts toward ..." copy. Drops the trailing program-type word and any
 * parenthetical POSt code so the label reads like a person would say it.
 */
export function shortenProgram(title: string): string {
  return title
    .replace(/\s*\([A-Z0-9]+\)\s*$/i, "")
    .replace(/\s+(Specialist|Major|Minor)\b.*$/i, "")
    .trim();
}

/** "Counts toward" phrasing: one name, "A and B", or "N of your programs". */
export function countsTowardPhrase(names: string[]): string | undefined {
  const unique = Array.from(new Set(names.filter(Boolean)));
  if (unique.length === 0) return undefined;
  if (unique.length === 1) return unique[0];
  if (unique.length === 2) return `${unique[0]} and ${unique[1]}`;
  return `${unique.length} of your programs`;
}

/** One course that helps fill still-open requirements, with the enrolled
 * programs it counts toward and how many (higher `count` = higher value). */
export interface RemainingMatch {
  code: string;
  programs: string[]; // shortened enrolled-program names, deduped
  count: number; // distinct enrolled programs this course still counts toward
}

/**
 * The heart of the app's proactive suggestions: across the student's enrolled
 * programs, which courses would fill a *still-open* requirement group, ranked
 * by how many programs they advance at once (multi-program picks first). A
 * group counts as open when its earned credits are below what it requires; a
 * program with no parsed progress row is treated as fully open. Courses the
 * student has already taken (`takenCodes`) are excluded.
 */
export function remainingRequirementMatches(
  programs: Program[],
  progressByProgram: Record<string, RequirementProgress[]>,
  takenCodes: Set<string>,
): RemainingMatch[] {
  const byCode = new Map<string, Set<string>>();
  for (const prog of programs) {
    const progress = progressByProgram[prog.code] ?? [];
    for (const group of prog.completionRequirements) {
      if (group.isNote) continue;
      const gp = progress.find((p) => p.label === group.heading);
      const open = gp ? gp.earned < gp.required : true;
      if (!open) continue;
      for (const code of group.courseCodes) {
        if (takenCodes.has(code)) continue;
        if (!byCode.has(code)) byCode.set(code, new Set());
        byCode.get(code)!.add(shortenProgram(prog.title));
      }
    }
  }
  return Array.from(byCode.entries())
    .map(([code, set]) => ({ code, programs: Array.from(set), count: set.size }))
    .sort((a, b) => b.count - a.count || a.code.localeCompare(b.code));
}

export interface BreadthEvaluation {
  satisfied: boolean;
  fulls: number; // categories with >= 1.0 credit
  /** Credits still needed under whichever satisfaction option is cheaper. 0 if satisfied. */
  remaining: number;
}

/**
 * design/09 §4: satisfied by EITHER 1.0 credit in each of 4 of the 5
 * categories, OR 1.0 in any 3 + 0.5 in the other 2.
 */
export function evaluateBreadth(data: Partial<BreadthData> = {}): BreadthEvaluation {
  const earned = BREADTH_KEYS.map((k) => data[k] ?? 0);
  const fulls = earned.filter((e) => e >= 1.0).length;
  const halves = earned.filter((e) => e >= 0.5).length;
  const satisfied = fulls >= 4 || (fulls >= 3 && halves >= 5);

  const sortedDesc = [...earned].sort((a, b) => b - a);
  // Option A: bring the top 4 categories to 1.0 each.
  const gapA = sortedDesc.slice(0, 4).reduce((s, e) => s + Math.max(0, 1 - e), 0);
  // Option B: bring the top 3 to 1.0, and the remaining 2 to 0.5.
  const gapB =
    sortedDesc.slice(0, 3).reduce((s, e) => s + Math.max(0, 1 - e), 0) +
    sortedDesc.slice(3).reduce((s, e) => s + Math.max(0, 0.5 - e), 0);

  return { satisfied, fulls, remaining: satisfied ? 0 : Math.min(gapA, gapB) };
}

/** design/09 §1: total 20.0, ArtSci ≥10.0, 200+ ≥13.0, 300+ ≥6.0, CGPA ≥1.85 to graduate. */
export const DEGREE_MINIMUMS = {
  total: 20.0,
  artsci: 10.0,
  level200: 13.0,
  level300: 6.0,
  sameSubjectCap: 15.0,
  graduationCgpa: 1.85,
} as const;

export function isDegreeAuditComplete(audit: DegreeAuditData): boolean {
  return (
    audit.totalEarned >= DEGREE_MINIMUMS.total &&
    audit.artsciEarned >= DEGREE_MINIMUMS.artsci &&
    audit.level200 >= DEGREE_MINIMUMS.level200 &&
    audit.level300 >= DEGREE_MINIMUMS.level300 &&
    audit.cgpa >= DEGREE_MINIMUMS.graduationCgpa &&
    (audit.topDesignator == null || audit.topDesignator.credits <= DEGREE_MINIMUMS.sameSubjectCap)
  );
}

/** design/09 §6 grade scale (% → letter, grade points). */
export const GRADE_SCALE: { min: number; letter: string; gp: number }[] = [
  { min: 90, letter: "A+", gp: 4.0 },
  { min: 85, letter: "A", gp: 4.0 },
  { min: 80, letter: "A-", gp: 3.7 },
  { min: 77, letter: "B+", gp: 3.3 },
  { min: 73, letter: "B", gp: 3.0 },
  { min: 70, letter: "B-", gp: 2.7 },
  { min: 67, letter: "C+", gp: 2.3 },
  { min: 63, letter: "C", gp: 2.0 },
  { min: 60, letter: "C-", gp: 1.7 },
  { min: 57, letter: "D+", gp: 1.3 },
  { min: 53, letter: "D", gp: 1.0 },
  { min: 50, letter: "D-", gp: 0.7 },
  { min: 0, letter: "F", gp: 0.0 },
];

export function markToGradePoint(mark: number): number {
  return (GRADE_SCALE.find((g) => mark >= g.min) ?? GRADE_SCALE[GRADE_SCALE.length - 1]).gp;
}

/** Grade *notations* excluded from GPA — mirrors
 * `backend/planner/gpa.py`'s `NOTATIONS_EXCLUDED_FROM_GPA` exactly. "FL" is
 * deliberately NOT in this set (see `resolveGradePoints` below): it counts
 * as a 0.0 fail, unlike the rest. */
export const GPA_EXCLUDED_NOTATIONS = new Set([
  "AEG", "CR", "NCR", "EXT", "XTR", "GWR", "IPR", "LWD", "WDR", "SDF", "P",
]);

/**
 * The letter-vs-mark precedence rule, mirrored client-side EXACTLY from
 * `backend/planner/gpa.py`'s `grade_points()` — the single source of truth
 * for what counts toward GPA and how: an explicit letter grade wins over a
 * raw numeric mark; "FL" always counts as 0.0; a notation in
 * `GPA_EXCLUDED_NOTATIONS`, or a `planned`/`extra` course, never counts.
 * Falls through to the mark only when there's no grade or the grade string
 * isn't a recognised letter/notation.
 *
 * This is the ONE place the rule is written client-side. Every client-side
 * GPA figure that has to exist locally (the offline mock adapter's derived
 * `TranscriptResponse`, and the GPA projector's what-if recompute in
 * Transcript.tsx) resolves grade points through this function instead of
 * re-deriving the rule. Every OTHER GPA figure in the app (CGPA, sessional/
 * cumulative GPA) comes straight from the backend (`GET /api/me/transcript`)
 * and never calls this at all — see AGENTS.md / the Transcript CGPA-mismatch
 * fix for why two independent implementations of this rule caused a bug.
 */
export function resolveGradePoints(course: {
  status: string;
  grade: string | null;
  mark: number | null;
}): number | null {
  if (course.status === "planned" || course.status === "extra") return null;
  const grade = (course.grade || "").trim().toUpperCase();
  if (grade) {
    if (GPA_EXCLUDED_NOTATIONS.has(grade)) return null;
    if (grade === "FL") return 0.0;
    const entry = GRADE_SCALE.find((g) => g.letter === grade);
    if (entry) return entry.gp;
  }
  if (course.mark != null) return markToGradePoint(course.mark);
  return null;
}

/** Credit value from a course code's suffix — H=0.5, Y=1.0 (design/06, "Credits derive from the code suffix"). */
export function creditFromCode(code: string): number {
  return /Y\d?$/.test(code) ? 1.0 : 0.5;
}

/** The course's numeric level from its code, e.g. "POL208H1" -> 200. */
export function courseLevel(code: string): number {
  const match = code.match(/[A-Z]{3}(\d)/);
  return match ? Number(match[1]) * 100 : 0;
}

/** The 3-letter subject designator, e.g. "POL208H1" -> "POL". */
export function courseSubject(code: string): string {
  return code.slice(0, 3);
}
