/**
 * Core data-model types, mirroring backend/data_sources/models.py 1:1 via
 * design/06-data-model-and-api.md. Keep this file in sync with that doc —
 * it is the single source of truth screens and the ds/ components bind to.
 */

export type Term = "F" | "S" | "Y"; // Fall / Winter(Spring) / Year
export type SessionCode = string; // "20269"=Fall 2026, "20271"=Winter 2027, "20265"=Summer 2026

export interface MeetingTime {
  day: 1 | 2 | 3 | 4 | 5 | 6 | 7; // ISO Mon..Sun
  startMin: number; // minutes since midnight
  endMin: number;
  building: string;
  session: SessionCode;
}

export interface Instructor {
  first: string;
  last: string;
}

export type TeachMethod = "LEC" | "TUT" | "PRA";

export interface Section {
  name: string; // "LEC0101"
  teachMethod: TeachMethod;
  sectionNumber: string;
  currentEnrol: number;
  maxEnrol: number;
  waitlist: number;
  instructors: Instructor[];
  meetingTimes: MeetingTime[];
  deliveryModes: string[];
}

export interface Course {
  code: string; // "POL208H1"
  title: string;
  sectionCode: Term;
  credit: number; // 0.5 / 1.0
  campus: string;
  description: string;
  prerequisites: string;
  corequisites: string;
  exclusions: string;
  breadth: string[]; // e.g. ["Society and its Institutions (3)"]
  distribution: string[];
  sections: Section[]; // live TTB offerings (empty for calendar-only)
}

export interface RequirementCourse {
  code: string;
  credits: number;
  notes: string;
}

export interface RequirementRule {
  credits: number;
  description: string;
  courseCodes: string[];
}

export interface RequirementGroup {
  heading: string; // "First Year", "Group A: ...", "" = intro/ungrouped
  credits: number; // credits this group requires
  isNote: boolean;
  courseCodes: string[];
  rules: RequirementRule[];
  courses: RequirementCourse[]; // per-course credit + notes (from Gemini grouper)
  notes: string; // group-level note
}

export type ProgramType = "specialist" | "major" | "minor" | "";

export interface Program {
  code: string; // "ASMAJ1305A"
  title: string;
  programType: ProgramType;
  department: string;
  departmentUrl: string;
  enrolmentRequirements: string;
  totalCredits: number;
  completionRequirements: RequirementGroup[];
  rawCompletionText: string;
  /** True once the on-demand Gemini grouper has populated per-course credits/notes. */
  requirementsLoaded?: boolean;
}

// ---- Student record (sensitive → encrypted at rest server-side) -------------

export type TranscriptCourseStatus = "completed" | "in_progress" | "planned" | "extra";

export interface TranscriptCourse {
  code: string;
  title: string;
  credits: number;
  mark: number | null;
  grade: string;
  session: string;
  status: TranscriptCourseStatus;
}

export type RequirementProgressStatus = "complete" | "incomplete" | "na";

export interface RequirementProgress {
  key: string;
  label: string;
  status: RequirementProgressStatus;
  earned: number;
  required: number;
  appliedCourses: string[];
}

export interface EnrolledProgramRef {
  code: string;
  name: string;
  startSession: string;
}

export interface StudentRecord {
  programs: EnrolledProgramRef[];
  transcript: TranscriptCourse[];
  requirementProgress: Record<string, RequirementProgress[]>; // by program code
  cgpa: number;
}

// ---- Degree-audit & breadth (design/09-uoft-degree-rules.md) ----------------
// Not part of the raw StudentRecord — these are *derived* views the app
// computes (see src/api/degreeAudit.ts) and that map directly onto the
// DegreeAudit / BreadthTracker design-system components' props.

/** Props shape for `<DegreeAudit>` (components/requirements/DegreeAudit.jsx). */
export interface DegreeAuditData {
  totalEarned: number; // x / 20.0
  artsciEarned: number; // x / 10.0
  level200: number; // x / 13.0
  level300: number; // x / 6.0
  topDesignator?: { code: string; credits: number } | null; // same-subject ≤15.0 cap
  cgpa: number; // graduate-eligible ≥ 1.85
}

export const BREADTH_KEYS = ["BR1", "BR2", "BR3", "BR4", "BR5"] as const;
export type BreadthKey = (typeof BREADTH_KEYS)[number];

/** Props shape for `<BreadthTracker data={...}>` — earned credits per category. */
export type BreadthData = Record<BreadthKey, number>;

export const BREADTH_LABELS: Record<BreadthKey, string> = {
  BR1: "Creative and Cultural Representations",
  BR2: "Thought, Belief, and Behaviour",
  BR3: "Society and Its Institutions",
  BR4: "Living Things and Their Environment",
  BR5: "The Physical and Mathematical Universes",
};

// ---- Summary / alerts ---------------------------------------------------

export interface Summary {
  creditsEarned: number;
  creditsTotal: number;
  breadthSatisfied: boolean;
  cgpa: number;
  degreePct: number;
}

export type AlertKind = "deadline" | "prereq" | "seat" | "info";

export interface Alert {
  id: string;
  kind: AlertKind;
  title: string;
  time?: string;
  read?: boolean;
}

// ---- Plan / timetable -----------------------------------------------------

export interface PlanCourse {
  code: string;
  term: SessionCode;
  locked?: boolean;
}

export interface PlanValidationIssue {
  severity: "error" | "warning" | "info";
  code: string; // planCourse code this issue is about, or "" for plan-wide
  message: string;
}

export interface TimetableScenario {
  id: string;
  name: string;
  selectedSections: Record<string, string>; // courseCode -> section name
  locked: Record<string, boolean>;
}
