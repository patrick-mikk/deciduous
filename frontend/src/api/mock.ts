/**
 * Seeded mock data so every screen renders without a live backend. The
 * persona ("Priya Sharma", a Public Policy Major with two in-progress
 * Minors) and numbers are carried over from the design package's own
 * `ui_kits/deciduous/data.js` sample record for continuity with the
 * screen mockups — reshaped here to the *real* API types
 * (design/06-data-model-and-api.md) rather than that file's ad-hoc shape.
 *
 * Swap to the real backend by setting `VITE_API_BASE` (see client.ts) —
 * screens should never import this module directly, only `./client`.
 */
import type {
  Alert,
  BreadthData,
  Course,
  DegreeAuditData,
  Program,
  RequirementGroup,
  RequirementProgress,
  SessionCode,
  StudentRecord,
  Summary,
} from "./types";

// ---- Sessions (design/06: "never hard-code; fetch from /reference-data") ----
// Mock stands in for that fetch. Term digit: 1=Winter, 5=Summer, 9=Fall.
export const mockSessions: SessionCode[] = ["20265", "20269", "20271"];
export const mockCurrentSession: SessionCode = "20269"; // Fall 2026

// ---- Course catalog -----------------------------------------------------

function section(
  name: string,
  teachMethod: Course["sections"][number]["teachMethod"],
  currentEnrol: number,
  maxEnrol: number,
  waitlist: number,
  instructors: { first: string; last: string }[],
  meetingTimes: { day: 1 | 2 | 3 | 4 | 5 | 6 | 7; startMin: number; endMin: number }[],
): Course["sections"][number] {
  return {
    name,
    teachMethod,
    sectionNumber: name.replace(/[A-Z]+/, ""),
    currentEnrol,
    maxEnrol,
    waitlist,
    instructors,
    meetingTimes: meetingTimes.map((m) => ({ ...m, building: "St. George", session: mockCurrentSession })),
    deliveryModes: ["In Person"],
  };
}

export const mockCourses: Course[] = [
  {
    code: "POL208H1",
    title: "Introduction to International Relations",
    sectionCode: "F",
    credit: 0.5,
    campus: "St. George",
    description:
      "A survey of the theories, history, and current practice of international relations: war and peace, international political economy, human rights, and the institutions of global governance.",
    prerequisites: "4.0 credits, or POL101Y1",
    corequisites: "",
    exclusions: "POL208Y1, POL208Y5",
    breadth: ["Society and Its Institutions (3)"],
    distribution: ["Social Science"],
    sections: [
      section("LEC0101", "LEC", 162, 185, 12, [{ first: "A", last: "Krannich" }], [
        { day: 2, startMin: 1080, endMin: 1200 },
        { day: 4, startMin: 1080, endMin: 1140 },
      ]),
      section("LEC5101", "LEC", 60, 60, 5, [{ first: "J", last: "Lee" }], [{ day: 1, startMin: 600, endMin: 720 }]),
      section("TUT0101", "TUT", 19, 40, 0, [], [{ day: 3, startMin: 540, endMin: 600 }]),
      section("TUT0201", "TUT", 33, 40, 0, [], [{ day: 5, startMin: 660, endMin: 720 }]),
    ],
  },
  {
    code: "PPG301H1",
    title: "Public Policy",
    sectionCode: "F",
    credit: 0.5,
    campus: "St. George",
    description: "Foundational concepts and frameworks in public policy analysis and design.",
    prerequisites: "ECO101H1, ECO102H1",
    corequisites: "",
    exclusions: "",
    breadth: [],
    distribution: ["Social Science"],
    sections: [section("LEC0101", "LEC", 48, 60, 0, [{ first: "M", last: "Osei" }], [
      { day: 1, startMin: 600, endMin: 660 },
      { day: 3, startMin: 600, endMin: 660 },
    ])],
  },
  {
    code: "PPG310H1",
    title: "Policy Analysis",
    sectionCode: "F",
    credit: 0.5,
    campus: "St. George",
    description: "Applied methods for analyzing and evaluating public policy options.",
    prerequisites: "PPG301H1",
    corequisites: "",
    exclusions: "",
    breadth: [],
    distribution: ["Social Science"],
    sections: [],
  },
  {
    code: "POL222H1",
    title: "Understanding Political Data",
    sectionCode: "Y",
    credit: 0.5,
    campus: "St. George",
    description: "An introduction to quantitative reasoning and data analysis in political science.",
    prerequisites: "4.0 credits",
    corequisites: "",
    exclusions: "",
    breadth: ["The Physical and Mathematical Universes (5)"],
    distribution: ["Social Science"],
    sections: [section("LEC0101", "LEC", 88, 120, 0, [{ first: "R", last: "Fine" }], [
      { day: 2, startMin: 780, endMin: 900 },
    ])],
  },
  {
    code: "GGR272H1",
    title: "Geographic Information & Mapping I",
    sectionCode: "F",
    credit: 0.5,
    campus: "St. George",
    description: "Foundations of geographic information systems and cartographic mapping.",
    prerequisites: "",
    corequisites: "",
    exclusions: "",
    breadth: ["The Physical and Mathematical Universes (5)"],
    distribution: ["Science"],
    sections: [],
  },
  {
    code: "HIS271Y1",
    title: "United States History",
    sectionCode: "Y",
    credit: 1.0,
    campus: "St. George",
    description: "A survey of United States history from colonial settlement to the present.",
    prerequisites: "",
    corequisites: "",
    exclusions: "",
    breadth: ["Society and Its Institutions (3)"],
    distribution: ["Arts"],
    sections: [
      section("LEC0101", "LEC", 40, 200, 0, [{ first: "D", last: "Wu" }], [{ day: 2, startMin: 780, endMin: 900 }]),
      section("TUT0101", "TUT", 12, 25, 0, [], [{ day: 4, startMin: 600, endMin: 660 }]),
    ],
  },
  {
    code: "PHL265H1",
    title: "Philosophy of Human Rights",
    sectionCode: "S",
    credit: 0.5,
    campus: "St. George",
    description: "Philosophical foundations and critiques of the concept of human rights.",
    prerequisites: "",
    corequisites: "",
    exclusions: "",
    breadth: ["Thought, Belief, and Behaviour (2)"],
    distribution: ["Arts"],
    sections: [],
  },
  {
    code: "ENV222H1",
    title: "Ethics & the Environment",
    sectionCode: "F",
    credit: 0.5,
    campus: "St. George",
    description: "Ethical frameworks for thinking about environmental change and policy.",
    prerequisites: "",
    corequisites: "",
    exclusions: "",
    breadth: ["Living Things and Their Environment (4)"],
    distribution: ["Arts"],
    sections: [],
  },
  {
    code: "ENG140H1",
    title: "Literature for Our Time",
    sectionCode: "F",
    credit: 0.5,
    campus: "St. George",
    description: "Close reading of contemporary literature across genres.",
    prerequisites: "",
    corequisites: "",
    exclusions: "",
    breadth: ["Creative and Cultural Representations (1)"],
    distribution: ["Arts"],
    sections: [],
  },
  { code: "ECO101H1", title: "Principles of Microeconomics", sectionCode: "F", credit: 0.5, campus: "St. George", description: "Introductory microeconomics.", prerequisites: "", corequisites: "", exclusions: "", breadth: [], distribution: ["Social Science"], sections: [] },
  { code: "ECO102H1", title: "Principles of Macroeconomics", sectionCode: "S", credit: 0.5, campus: "St. George", description: "Introductory macroeconomics.", prerequisites: "", corequisites: "", exclusions: "", breadth: [], distribution: ["Social Science"], sections: [] },
  { code: "STA220H1", title: "The Practice of Statistics I", sectionCode: "F", credit: 0.5, campus: "St. George", description: "Introductory applied statistics.", prerequisites: "", corequisites: "", exclusions: "", breadth: [], distribution: ["Science"], sections: [] },
  // Demo case for the requirement-line-satisfaction + exclusion-filtering fix
  // (see degreeAudit.ts remainingRequirementMatches / isExcludedByTaken): the
  // mock student completed STA220H1, which both satisfies the Methods group's
  // "STA220H1 / STA257H1" rule below AND formally excludes STA257H1 -- it
  // must not be suggested.
  { code: "STA257H1", title: "Probability and Statistics I", sectionCode: "F", credit: 0.5, campus: "St. George", description: "Calculus-based introduction to probability and statistics.", prerequisites: "", corequisites: "", exclusions: "Exclusion: STA220H1", breadth: [], distribution: ["Science"], sections: [] },
  { code: "POL340H1", title: "Public Opinion", sectionCode: "S", credit: 0.5, campus: "St. George", description: "The formation and measurement of public opinion.", prerequisites: "POL208H1", corequisites: "", exclusions: "", breadth: ["Society and Its Institutions (3)"], distribution: ["Social Science"], sections: [] },
  { code: "PPG340H1", title: "Policy Evaluation", sectionCode: "S", credit: 0.5, campus: "St. George", description: "Methods for evaluating the impact of public policy interventions.", prerequisites: "PPG310H1", corequisites: "", exclusions: "", breadth: ["Society and Its Institutions (3)"], distribution: ["Social Science"], sections: [] },
  { code: "ECO333H1", title: "Urban Economics", sectionCode: "F", credit: 0.5, campus: "St. George", description: "Economic analysis of cities and urban policy.", prerequisites: "ECO101H1, ECO102H1", corequisites: "", exclusions: "", breadth: ["Society and Its Institutions (3)"], distribution: ["Social Science"], sections: [] },
  { code: "GGR336H1", title: "Urban Geography", sectionCode: "S", credit: 0.5, campus: "St. George", description: "The spatial structure and dynamics of cities.", prerequisites: "", corequisites: "", exclusions: "", breadth: ["Society and Its Institutions (3)"], distribution: ["Social Science"], sections: [] },
  { code: "POL333Y1", title: "Advanced Topics in Public Policy", sectionCode: "Y", credit: 1.0, campus: "St. George", description: "A seminar on current debates in public policy.", prerequisites: "PPG301H1, PPG310H1", corequisites: "", exclusions: "", breadth: [], distribution: ["Social Science"], sections: [] },
];

export function findCourse(code: string): Course | undefined {
  return mockCourses.find((c) => c.code === code);
}

// ---- Programs -------------------------------------------------------------

const publicPolicyGroups: RequirementGroup[] = [
  {
    heading: "First Year",
    credits: 1.0,
    isNote: false,
    courseCodes: ["ECO101H1", "ECO102H1"],
    rules: [],
    courses: [
      { code: "ECO101H1", credits: 0.5, notes: "" },
      { code: "ECO102H1", credits: 0.5, notes: "" },
    ],
    notes: "Introductory economics.",
  },
  {
    heading: "Methods",
    credits: 1.0,
    isNote: false,
    courseCodes: ["STA220H1", "STA257H1", "POL222H1", "POL232H1"],
    rules: [
      // Line 1: the intro stats requirement. STA257H1 is deliberately NOT in
      // this rule's courseCodes: covered by no rule, it falls back to the
      // group-level "still open" check and so remains a *candidate* from the
      // engine -- what actually removes it is the exclusion filter
      // (isExcludedByTaken), because its Calendar exclusion text names the
      // completed STA220H1 (see mockCourses' STA257H1 entry). This is the one
      // fixture that exercises the exclusion mechanism end to end; putting
      // STA257H1 in this (already satisfied) rule would let rule-satisfaction
      // pre-empt the exclusion filter and leave mechanism 2 untested.
      { credits: 0.5, description: "STA220H1", courseCodes: ["STA220H1"] },
      // Line 2: one further methods course. The mock transcript below also
      // happens to already have POL222H1 completed, so this line is
      // *already* satisfied -- by the rule-satisfaction mechanism, POL232H1
      // correctly stops being suggested (the identical pattern as the real
      // ECO200Y1-completed/ECO204Y1+ECO206Y1-suggested bug this fix targets).
      // Net effect for this student: the engine still emits STA257H1 as a
      // candidate (group open, no covering rule) and the exclusion filter
      // then drops it, while POL232H1 never leaves the engine at all. The
      // group total (1.0 required) is deliberately not reflected in the
      // hand-authored progress row below (kept at 0.5/1.0 so the group stays
      // "open") -- rule-level checks operate independently of that row.
      { credits: 0.5, description: "One methods course beyond STA220H1", courseCodes: ["POL222H1", "POL232H1"] },
    ],
    courses: [
      { code: "STA220H1", credits: 0.5, notes: "" },
      { code: "STA257H1", credits: 0.5, notes: "" },
      { code: "POL222H1", credits: 0.5, notes: "" },
      { code: "POL232H1", credits: 0.5, notes: "" },
    ],
    notes: "One of the listed methods courses beyond STA220H1.",
  },
  {
    heading: "Core Public Policy",
    credits: 2.0,
    isNote: false,
    courseCodes: ["POL208H1", "PPG301H1", "PPG310H1", "POL340H1"],
    rules: [],
    courses: [
      { code: "POL208H1", credits: 0.5, notes: "Planned for Fall 2026." },
      { code: "PPG301H1", credits: 0.5, notes: "" },
      { code: "PPG310H1", credits: 0.5, notes: "" },
      { code: "POL340H1", credits: 0.5, notes: "" },
    ],
    notes: "",
  },
  {
    heading: "Higher-Years Electives",
    credits: 3.0,
    isNote: false,
    courseCodes: ["POL333Y1", "PPG340H1", "ECO333H1", "GGR336H1"],
    rules: [{ credits: 3.0, description: "Any combination of the listed 300+ electives", courseCodes: ["POL333Y1", "PPG340H1", "ECO333H1", "GGR336H1"] }],
    courses: [
      { code: "POL333Y1", credits: 1.0, notes: "" },
      { code: "PPG340H1", credits: 0.5, notes: "" },
      { code: "ECO333H1", credits: 0.5, notes: "" },
      { code: "GGR336H1", credits: 0.5, notes: "" },
    ],
    notes: "",
  },
];

export const mockPrograms: Program[] = [
  {
    code: "ASMAJ2660",
    title: "Public Policy",
    programType: "major",
    department: "Political Science",
    departmentUrl: "https://politics.utoronto.ca/",
    enrolmentRequirements: "Open program. Enrol after completing 4.0 credits.",
    totalCredits: 7.0,
    completionRequirements: publicPolicyGroups,
    rawCompletionText: "",
    requirementsLoaded: true,
  },
  {
    code: "ASMIN0301",
    title: "American Studies",
    programType: "minor",
    department: "History",
    departmentUrl: "https://history.utoronto.ca/",
    enrolmentRequirements: "Open program. Enrol after completing 4.0 credits.",
    totalCredits: 4.0,
    completionRequirements: [],
    rawCompletionText:
      "4.0 credits: HIS271Y1; 1.0 credit from HIS2XX; 1.0 credit at the 300+ level in American Studies; 1.0 further credit in American Studies.",
    requirementsLoaded: false, // demonstrates the on-demand "Load requirements (Gemini)" flow
  },
  {
    code: "ASMIN1120",
    title: "Geographic Information Systems",
    programType: "minor",
    department: "Geography & Planning",
    departmentUrl: "https://geography.utoronto.ca/",
    enrolmentRequirements: "Limited program: GGR272H1 with a minimum grade of 63% (C+).",
    totalCredits: 4.0,
    completionRequirements: [],
    rawCompletionText: "4.0 credits: GGR272H1; GGR336H1; 2.5 further credits in GIS/GGR at the 300+ level.",
    requirementsLoaded: false,
  },
  // A handful more so /programs (browse/search) doesn't look sparse.
  {
    code: "ASSPE0608",
    title: "Political Science",
    programType: "specialist",
    department: "Political Science",
    departmentUrl: "https://politics.utoronto.ca/",
    enrolmentRequirements: "Limited program: minimum 70% average in 4.0 POL credits.",
    totalCredits: 12.0,
    completionRequirements: [],
    rawCompletionText: "12.0 credits, including 4.0 at the 300+ level, of which 1.0 at the 400 level.",
    requirementsLoaded: false,
  },
  {
    code: "ASMAJ1689",
    title: "Computer Science",
    programType: "major",
    department: "Computer Science",
    departmentUrl: "https://web.cs.toronto.edu/",
    enrolmentRequirements: "Limited program: CSC148H1, CSC165H1/MAT137Y1/MAT157Y1 with a minimum 60% average.",
    totalCredits: 7.0,
    completionRequirements: [],
    rawCompletionText: "7.0 credits including CSC148H1, CSC165H1, CSC207H1, CSC236H1, CSC258H1, CSC263H1, CSC373H1.",
    requirementsLoaded: false,
  },
  {
    code: "ASMIN0616",
    title: "Statistics",
    programType: "minor",
    department: "Statistical Sciences",
    departmentUrl: "https://www.statistics.utoronto.ca/",
    enrolmentRequirements: "Open program. Enrol after completing 4.0 credits.",
    totalCredits: 4.0,
    completionRequirements: [],
    rawCompletionText: "4.0 credits including STA220H1/STA257H1 and 2.5 further credits in STA at the 200+ level.",
    requirementsLoaded: false,
  },
];

export function findProgram(code: string): Program | undefined {
  return mockPrograms.find((p) => p.code === code);
}

// ---- Student record ---------------------------------------------------------

const publicPolicyProgress: RequirementProgress[] = publicPolicyGroups.map((g) => ({
  key: g.heading.toLowerCase().replace(/\s+/g, "-"),
  label: g.heading,
  status: "incomplete", // overwritten below once earned is filled in from the transcript
  earned: 0,
  required: g.credits,
  appliedCourses: [],
}));

// Compute earned per group from the transcript status baked into publicPolicyGroups' notes above,
// mirroring the source design data (First Year 1.0/1.0, Methods 0.5/1.0, Core 1.5/2.0, Electives 1.2/3.0).
const earnedByHeading: Record<string, { earned: number; applied: string[] }> = {
  "First Year": { earned: 1.0, applied: ["ECO101H1", "ECO102H1"] },
  Methods: { earned: 0.5, applied: ["STA220H1"] },
  "Core Public Policy": { earned: 1.5, applied: ["PPG301H1", "PPG310H1"] },
  "Higher-Years Electives": { earned: 1.2, applied: [] },
};
for (const p of publicPolicyProgress) {
  const src = earnedByHeading[p.label];
  if (src) {
    p.earned = src.earned;
    p.appliedCourses = src.applied;
    p.status = p.earned >= p.required ? "complete" : "incomplete";
  }
}

export const mockStudentRecord: StudentRecord = {
  programs: [
    { code: "ASMAJ2660", name: "Public Policy", startSession: "20229", earnedCredits: 2.5, totalCredits: 6.0, percent: 41.7, requirementsLoaded: true },
    { code: "ASMIN0301", name: "American Studies", startSession: "20229", earnedCredits: 1.0, totalCredits: 4.0, percent: 25.0, requirementsLoaded: true },
    { code: "ASMIN1120", name: "Geographic Information Systems", startSession: "20241", earnedCredits: 0.5, totalCredits: 4.0, percent: 12.5, requirementsLoaded: true },
  ],
  transcript: [
    { code: "ECO101H1", title: "Principles of Microeconomics", credits: 0.5, mark: 78, grade: "B+", session: "20229", status: "completed" },
    { code: "ECO102H1", title: "Principles of Macroeconomics", credits: 0.5, mark: 74, grade: "B", session: "20231", status: "completed" },
    { code: "STA220H1", title: "The Practice of Statistics I", credits: 0.5, mark: 71, grade: "B-", session: "20229", status: "completed" },
    { code: "ENG140H1", title: "Literature for Our Time", credits: 0.5, mark: 81, grade: "A-", session: "20229", status: "completed" },
    { code: "PPG301H1", title: "Public Policy", credits: 0.5, mark: 76, grade: "B", session: "20239", status: "completed" },
    { code: "PPG310H1", title: "Policy Analysis", credits: 0.5, mark: 68, grade: "C+", session: "20239", status: "completed" },
    { code: "HIS271Y1", title: "United States History", credits: 1.0, mark: 73, grade: "B", session: "20239-20241", status: "completed" },
    { code: "GGR272H1", title: "Geographic Information & Mapping I", credits: 0.5, mark: 65, grade: "C", session: "20241", status: "completed" },
    { code: "PHL265H1", title: "Philosophy of Human Rights", credits: 0.5, mark: 84, grade: "A-", session: "20241", status: "completed" },
    { code: "POL222H1", title: "Understanding Political Data", credits: 0.5, mark: 79, grade: "B+", session: "20241", status: "completed" },
    { code: "ENV222H1", title: "Ethics & the Environment", credits: 0.5, mark: null, grade: "", session: "20251", status: "completed" },
    { code: "POL208H1", title: "Introduction to International Relations", credits: 0.5, mark: null, grade: "", session: "20269", status: "planned" },
  ],
  requirementProgress: {
    ASMAJ2660: publicPolicyProgress,
    ASMIN0301: [
      { key: "core", label: "Core requirements", status: "incomplete", earned: 2.0, required: 4.0, appliedCourses: ["HIS271Y1"] },
    ],
    ASMIN1120: [
      { key: "core", label: "Core requirements", status: "incomplete", earned: 0.5, required: 4.0, appliedCourses: ["GGR272H1"] },
    ],
  },
  cgpa: 2.7,
};

// ---- Degree audit + breadth (design/09) --------------------------------
// Derived from the transcript above; a real backend would compute these from
// the transcript + level/subject parsed off each course code (see
// src/api/degreeAudit.ts for the shared helpers screens should reuse).

export const mockDegreeAudit: DegreeAuditData = {
  totalEarned: 13.5,
  artsciEarned: 11.5,
  level200: 8.0,
  level300: 3.5,
  topDesignator: { code: "POL", credits: 1.5 },
  cgpa: 2.7,
};

export const mockBreadthData: BreadthData = {
  BR1: 0.5,
  BR2: 0.5,
  BR3: 1.5,
  BR4: 0.5,
  BR5: 1.5,
};

export const mockSummary: Summary = {
  creditsEarned: mockDegreeAudit.totalEarned,
  creditsTotal: 20,
  breadthSatisfied: false,
  cgpa: mockStudentRecord.cgpa,
  degreePct: Math.round((mockDegreeAudit.totalEarned / 20) * 100),
};

export const mockAlerts: Alert[] = [
  { id: "n1", kind: "deadline", title: "Enrolment opens July 21 for Fall 2026", time: "in 6 days" },
  { id: "n2", kind: "prereq", title: "POL208H1 prerequisite not yet met", time: "2h ago" },
  { id: "n3", kind: "seat", title: "A seat opened in PPG340H1", time: "yesterday", read: true },
];
