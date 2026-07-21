/**
 * Typed API client, shaped to the endpoint map in
 * design/06-data-model-and-api.md. Screens should only ever import `api`
 * from here — never `./mock` directly — so flipping to a live backend is a
 * one-line env change (`VITE_API_BASE`), not a per-screen rewrite.
 *
 * `api` resolves to:
 *  - `httpClient`, a real `fetch()` client against `VITE_API_BASE`, if that
 *    env var is set (see .env / vite docs — `VITE_`-prefixed vars are
 *    inlined at build time and are NOT secret; never put an API key here).
 *  - `mockClient` otherwise (e.g. local dev with no backend running yet) —
 *    every method resolves from the seeded data in `./mock` after a small
 *    artificial delay, so loading states are exercisable too.
 *
 * ---------------------------------------------------------------------------
 * BOUNDARY CONTRACT (read this before adding or touching a method below):
 *
 * This file is the ONLY place a raw backend JSON response is allowed to
 * touch app code. Screens, `src/ds`, and every other module trust the
 * `ApiClient` return types completely — they do not (and must not) re-check
 * whether a field is an array, a number, or present at all. That trust is
 * only safe because every `httpClient` method below normalizes its response
 * before resolving:
 *
 *   - Envelopes are unwrapped (`{courses: [...]}` -> `Course[]`, never the
 *     wrapper object itself).
 *   - Arrays default to `[]` (via `asArray`), never `undefined`/`null`, so a
 *     screen's `.map`/`.filter`/`.find`/etc. can never throw
 *     "X is not a function" on a partial or malformed response.
 *   - Numbers default to an explicit fallback (via `asNum`) or explicit
 *     `null` for genuinely-optional numerics (via `asNullableNum`) — never
 *     bare `undefined`, so `.toFixed()`/arithmetic can't silently produce
 *     `NaN` or throw.
 *   - Nested objects get field-by-field defaults, not passed through as-is.
 *   - A backend shape that doesn't match this file's assumed shape (wrong
 *     field name, snake_case vs camelCase, a completely different envelope)
 *     is adapted HERE, not worked around at the call site.
 *
 * This was written after five near-identical production crashes
 * ("X.map/.filter/.find is not a function", "Cannot read properties of
 * undefined (reading 'toFixed')") all traced back to a raw, unnormalized
 * backend response reaching a screen. See `asArray`/`asNum`/`asNullableNum`/
 * `asStr`/`asRecord` below — use them for every new field this file reads
 * off a `fetch()` response, no exceptions.
 */
import * as mock from "./mock";
import { DEGREE_MINIMUMS, evaluateBreadth, resolveGradePoints } from "./degreeAudit";
import type {
  Alert,
  AlertKind,
  BreadthData,
  Course,
  DegreeAuditData,
  EnrolledProgramRef,
  Instructor,
  MeetingTime,
  PlanValidationIssue,
  Program,
  ProgramType,
  RequirementCourse,
  RequirementGroup,
  RequirementProgress,
  RequirementProgressStatus,
  RequirementRule,
  Section,
  SessionCode,
  StudentRecord,
  Summary,
  TeachMethod,
  Term,
  TranscriptCourse,
  TranscriptCourseStatus,
  TranscriptResponse,
  TranscriptSessionGroup,
} from "./types";

export interface CourseSearchParams {
  q?: string;
  level?: number;
  breadth?: string;
  term?: SessionCode;
  hasSeats?: boolean;
}

export interface ProgramSearchParams {
  q?: string;
  type?: string;
  subject?: string;
  page?: number;
  pageSize?: number;
}

/** One `planCourses` entry, shaped for `POST /api/plan/validate`'s ad hoc `items` override. */
export interface PlanValidationItem {
  courseCode: string;
  termSession: string;
  status?: "planned" | "completed" | "in_progress" | "extra";
}

export interface PlanValidationResult {
  issues: PlanValidationIssue[];
}

/** The full surface a screen can call. Both `mockClient` and `httpClient` implement this. */
export interface ApiClient {
  // Reference data
  getSessions(): Promise<SessionCode[]>;

  // Programs
  getPrograms(params?: ProgramSearchParams): Promise<Program[]>;
  /**
   * The WHOLE program catalog, for screens that filter client-side
   * (onboarding search, department dropdowns). `GET /api/programs` is
   * paginated (default page size 20), so a bare `getPrograms()` silently
   * returns only the first page — this pages through until exhausted.
   */
  getAllPrograms(): Promise<Program[]>;
  getProgram(code: string): Promise<Program | null>;
  getProgramRequirements(code: string): Promise<Program["completionRequirements"]>;
  /** POST /api/programs/:code/requirements/reparse — on-demand Gemini grouper, ~10-20s. */
  reparseProgramRequirements(code: string): Promise<Program["completionRequirements"]>;

  // Courses
  getCourses(params?: CourseSearchParams): Promise<Course[]>;
  getCourse(code: string): Promise<Course | null>;

  /**
   * `POST /api/plan/validate` (backend/api/plan.py) — validates an ad hoc
   * `items` list (the client-held plan, not yet persisted via `PUT
   * /api/plan`) against prerequisites/exclusions/offering plus the caller's
   * program-requirement coverage. Server-authoritative: this is the only
   * source that can surface plan-wide warnings the client can't compute
   * itself (e.g. a program whose requirements haven't been parsed yet).
   */
  validatePlan(items: PlanValidationItem[]): Promise<PlanValidationResult>;

  // Me
  getMyRecord(): Promise<StudentRecord>;
  /**
   * `GET /api/me/transcript` (backend/api/me.py `transcript()`) — the ONE
   * authoritative source for every GPA figure the Transcript screen shows
   * (CGPA, per-session sessional/cumulative GPA): all computed server-side
   * by the same `backend/planner/gpa.py` engine, never recomputed
   * client-side from raw marks. See that route's docstring for why.
   */
  getMyTranscript(): Promise<TranscriptResponse>;
  getMyRequirementProgress(): Promise<StudentRecord["requirementProgress"]>;
  getMyDegreeAudit(): Promise<DegreeAuditData>;
  getMyBreadth(): Promise<{ data: BreadthData; evaluation: ReturnType<typeof evaluateBreadth> }>;
  getMySummary(): Promise<Summary>;
  getMyAlerts(): Promise<Alert[]>;

  // Me — enrolled programs (design/02-user-flows.md "/programs/mine": add/remove/reorder priority)
  getMyPrograms(): Promise<EnrolledProgramRef[]>;
  addMyProgram(code: string): Promise<void>;
  removeMyProgram(code: string): Promise<void>;
  /** Persists the given display order; `codes` must be every enrolled program code, reordered. */
  reorderMyPrograms(codes: string[]): Promise<void>;

  // Share
  createShareLink(): Promise<{ token: string; url: string }>;
  getShared(token: string): Promise<Partial<StudentRecord> | null>;
}

function delay<T>(value: T, ms = 250): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

/** Weighted-average GPA (weight = credits) over `list`, using the shared
 * `resolveGradePoints` precedence rule — mirrors `backend/planner/gpa.py`
 * `compute_gpa()`. `null` when nothing in `list` counts toward GPA. */
function weightedGpa(list: TranscriptCourse[]): number | null {
  let credits = 0;
  let points = 0;
  for (const c of list) {
    const gp = resolveGradePoints(c);
    if (gp == null) continue;
    credits += c.credits;
    points += c.credits * gp;
  }
  return credits > 0 ? points / credits : null;
}

/**
 * Offline-demo stand-in for `GET /api/me/transcript`: derives per-session
 * sessional/cumulative GPA from the same static `mock.mockStudentRecord.
 * transcript` fixture `getMyRecord` reads, using the one shared
 * `resolveGradePoints` rule so the mock adapter can't drift from the real
 * backend's precedence the way the old client-side `computeGpa` did.
 */
function mockTranscriptResponse(): TranscriptResponse {
  const courses = mock.mockStudentRecord.transcript;
  const graded = courses.filter((c) => c.status !== "planned" && c.status !== "extra");

  const bySession = new Map<string, TranscriptCourse[]>();
  for (const c of graded) {
    const arr = bySession.get(c.session) ?? [];
    arr.push(c);
    bySession.set(c.session, arr);
  }
  const chronological = [...bySession.keys()].sort(
    (a, b) => Number(a.split("-")[0]) - Number(b.split("-")[0]),
  );

  let running: TranscriptCourse[] = [];
  const cumBySession = new Map<string, number | null>();
  for (const s of chronological) {
    running = [...running, ...(bySession.get(s) ?? [])];
    cumBySession.set(s, weightedGpa(running));
  }

  const sessions: TranscriptSessionGroup[] = [...chronological].reverse().map((s) => ({
    session: s,
    courses: (bySession.get(s) ?? []).map((c) => ({
      code: c.code,
      title: c.title,
      credits: c.credits,
      mark: c.mark,
      grade: c.grade || null,
      status: c.status,
    })),
    sgpa: weightedGpa(bySession.get(s) ?? []),
    cumGpa: cumBySession.get(s) ?? null,
  }));

  const overallCgpa = chronological.length
    ? cumBySession.get(chronological[chronological.length - 1]) ?? null
    : null;

  return { sessions, cgpa: overallCgpa, warnings: [] };
}

export const mockClient: ApiClient = {
  getSessions: () => delay(mock.mockSessions),

  getPrograms: (params) => {
    let results = mock.mockPrograms;
    if (params?.q) {
      const q = params.q.toLowerCase();
      results = results.filter((p) => p.title.toLowerCase().includes(q) || p.code.toLowerCase().includes(q));
    }
    if (params?.type) results = results.filter((p) => p.programType === params.type);
    return delay(results);
  },
  getAllPrograms: () => delay(mock.mockPrograms),
  getProgram: (code) => delay(mock.findProgram(code) ?? null),
  getProgramRequirements: (code) => delay(mock.findProgram(code)?.completionRequirements ?? []),
  reparseProgramRequirements: async (code) => {
    // Simulate the ~10-20s Gemini grouping latency (shortened for local dev).
    await delay(null, 1200);
    const program = mock.findProgram(code);
    if (program) program.requirementsLoaded = true;
    return program?.completionRequirements ?? [];
  },

  getCourses: (params) => {
    let results = mock.mockCourses;
    if (params?.q) {
      const q = params.q.toLowerCase();
      results = results.filter((c) => c.title.toLowerCase().includes(q) || c.code.toLowerCase().includes(q));
    }
    if (params?.breadth) {
      results = results.filter((c) => c.breadth.some((b) => b.includes(params.breadth!)));
    }
    if (params?.hasSeats) {
      results = results.filter((c) => c.sections.some((s) => s.currentEnrol < s.maxEnrol));
    }
    // Design/06: "Empty search ≠ error" — TTB 404s on no-match; we just return [].
    return delay(results);
  },
  getCourse: (code) => delay(mock.findCourse(code) ?? null),

  // Lightweight demo approximation (exclusion conflicts only) -- the offline
  // mock adapter has no server to run the real prereq/requirement engine
  // against; screens should treat this as a stand-in, not a spec.
  validatePlan: (items) => {
    const codes = new Set(items.map((i) => i.courseCode));
    const issues: PlanValidationIssue[] = [];
    for (const item of items) {
      const course = mock.findCourse(item.courseCode);
      if (!course) continue;
      const excluded = Array.from(new Set(course.exclusions.match(/[A-Z]{3}\d{3}[HY]\d/g) ?? [])).filter(
        (c) => c !== item.courseCode && codes.has(c),
      );
      if (excluded.length > 0) {
        issues.push({
          severity: "error",
          kind: "exclusion",
          code: item.courseCode,
          message: `${item.courseCode} cannot be taken with ${excluded.join(", ")} (exclusion).`,
        });
      }
    }
    return delay({ issues });
  },

  getMyRecord: () => delay(mock.mockStudentRecord),
  getMyTranscript: () => delay(mockTranscriptResponse()),
  getMyRequirementProgress: () => delay(mock.mockStudentRecord.requirementProgress),
  getMyDegreeAudit: () => delay(mock.mockDegreeAudit),
  getMyBreadth: () => delay({ data: mock.mockBreadthData, evaluation: evaluateBreadth(mock.mockBreadthData) }),
  getMySummary: () => delay(mock.mockSummary),
  getMyAlerts: () => delay(mock.mockAlerts),

  getMyPrograms: () => delay(mock.mockStudentRecord.programs),
  addMyProgram: async (code) => {
    await delay(null);
    if (mock.mockStudentRecord.programs.some((p) => p.code === code)) return;
    const catalog = mock.findProgram(code);
    mock.mockStudentRecord.programs.push({
      code,
      name: catalog?.title ?? code,
      startSession: "",
      earnedCredits: 0,
      totalCredits: catalog?.totalCredits ?? 0,
      percent: 0,
      requirementsLoaded: Boolean(catalog),
    });
  },
  removeMyProgram: async (code) => {
    await delay(null);
    mock.mockStudentRecord.programs = mock.mockStudentRecord.programs.filter((p) => p.code !== code);
  },
  reorderMyPrograms: async (codes) => {
    await delay(null);
    const byCode = new Map(mock.mockStudentRecord.programs.map((p) => [p.code, p]));
    mock.mockStudentRecord.programs = codes.map((code) => byCode.get(code)!).filter(Boolean);
  },

  createShareLink: () => delay({ token: "demo-share-token", url: `${window.location.origin}/share/demo-share-token` }),
  getShared: (token) =>
    delay(
      token === "demo-share-token"
        ? { programs: mock.mockStudentRecord.programs, cgpa: mock.mockStudentRecord.cgpa }
        : null,
    ),
};

// `VITE_API_BASE` wins when set. Otherwise EVERY build -- dev and prod --
// defaults to `/api`: prod is served same-origin by Flask (backend/app.py's
// `_register_spa`), and `npm run dev` reaches Flask through vite.config.ts's
// `server.proxy`. When no backend is running, requests fail LOUDLY (see
// `http()` below) instead of silently rendering demo data.
//
// The offline mock adapter (mock.ts) is opt-in only: set `VITE_API_BASE=mock`.
export const isMockApi = import.meta.env.VITE_API_BASE === "mock";
export const API_BASE: string | undefined = isMockApi
  ? undefined
  : import.meta.env.VITE_API_BASE || "/api";

/**
 * Double-submit CSRF (backend/app.py `_register_csrf_guard`): every non-GET
 * `/api/*` request needs an `X-CSRF-Token` header matching the readable
 * `csrf_token` cookie, fetched once from `GET /api/auth/csrf`.
 */
function readCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

let csrfReady: Promise<unknown> | null = null;

/**
 * Exported so SignIn/SignUp — which talk to `/api/auth/*` directly instead of
 * through `http()` above (see those screens' own doc comments) — can attach
 * the same double-submit header the backend's CSRF guard requires.
 */
export async function ensureCsrfToken(): Promise<string> {
  const existing = readCookie("csrf_token");
  if (existing) return existing;
  csrfReady ??= fetch(`${API_BASE}/auth/csrf`, { credentials: "include" });
  await csrfReady;
  return readCookie("csrf_token") ?? "";
}

/**
 * Thrown by `http()` for any non-2xx, non-network-failure response so call
 * sites that need to distinguish "not found" (404) from every other error
 * can do so without parsing message strings — see `httpOrNull`.
 */
export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

interface HttpOpts {
  /**
   * What a 404 should resolve to. `"array"` (the default) preserves the
   * long-standing behavior for list/search endpoints, where TTB's "no-match
   * search returns HTTP 404" quirk (AGENTS.md) and this app's own empty-list
   * responses are indistinguishable from "resource genuinely not found" at
   * this layer — an empty list is the correct, safe reading either way.
   * `"throw"` is for single-resource GETs (`/programs/:code`, `/courses/:code`,
   * `/share/:token`) where 404 means "doesn't exist" and coercing that to an
   * array would silently hand a screen `[]` where it expected `T | null` —
   * `[].title` etc. is `undefined`, not a caught "not found" state. Use
   * `httpOrNull` for those instead of setting this directly.
   */
  fallback404?: "array" | "throw";
}

async function http<T>(path: string, init?: RequestInit, opts?: HttpOpts): Promise<T> {
  const fallback404 = opts?.fallback404 ?? "array";
  const method = (init?.method ?? "GET").toUpperCase();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (method !== "GET") {
    headers["X-CSRF-Token"] = await ensureCsrfToken();
  }
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      credentials: "include",
      ...init,
      headers: { ...headers, ...(init?.headers as Record<string, string> | undefined) },
    });
  } catch {
    // Network-level failure (backend down, proxy unreachable) -- fail LOUDLY
    // with an actionable message instead of a bare "Failed to fetch".
    throw new Error(
      `Can't reach the backend API (${API_BASE}${path}). Is the Flask server running? ` +
        "Start it with `python -m flask --app backend.app run` -- see frontend/.env.example.",
    );
  }
  if (res.status === 404 && fallback404 === "array") {
    // Design/06 + conventions.md: TTB-backed no-match search legitimately 404s — treat as empty, not an error.
    return [] as unknown as T;
  }
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    // A 5xx whose body isn't the backend's JSON error shape is the dev proxy
    // reporting a dead upstream (vite's http-proxy answers 500 with plain
    // text when Flask isn't running) -- surface that clearly.
    if (res.status >= 500 && !text.trimStart().startsWith("{")) {
      throw new Error(
        `Can't reach the backend API (${API_BASE}${path}). Is the Flask server running? ` +
          "Start it with `python -m flask --app backend.app run` -- see frontend/.env.example.",
      );
    }
    throw new ApiError(`API error ${res.status}: ${text}`, res.status);
  }
  return res.json() as Promise<T>;
}

/**
 * `http()` with `fallback404: "throw"`, catching just the 404 case into
 * `null` — the correct shape for single-resource GETs (`Program | null`,
 * `Course | null`, `Partial<StudentRecord> | null`). Any other error
 * (network, 500, 422, ...) still rejects normally.
 */
async function httpOrNull<T>(path: string, init?: RequestInit): Promise<T | null> {
  try {
    return await http<T>(path, init, { fallback404: "throw" });
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  }
}

function qs(params: object | undefined): string {
  if (!params) return "";
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== "");
  if (entries.length === 0) return "";
  return `?${new URLSearchParams(entries as [string, string][]).toString()}`;
}

// ---------------------------------------------------------------------------
// Normalization helpers (see the file-header "BOUNDARY CONTRACT" comment).
// Every httpClient method below must run its response through these before
// resolving — never hand a screen a raw `fetch()`-parsed value.
// ---------------------------------------------------------------------------

function asArray<T>(v: unknown): T[] {
  return Array.isArray(v) ? (v as T[]) : [];
}

function asNum(v: unknown, fallback: number): number {
  return typeof v === "number" && Number.isFinite(v) ? v : fallback;
}

/** For genuinely-optional numerics (e.g. an ungraded course's mark): explicit
 * `null`, never bare `undefined` — `x != null` guards stay meaningful. */
function asNullableNum(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

function asStr(v: unknown, fallback = ""): string {
  return typeof v === "string" ? v : fallback;
}

function asBool(v: unknown, fallback = false): boolean {
  return typeof v === "boolean" ? v : fallback;
}

function asRecord<T>(v: unknown): Record<string, T> {
  return v && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, T>) : {};
}

// ---------------------------------------------------------------------------
// Raw backend shapes. These mirror the actual JSON `backend/api/*.py` routes
// return (verified against source, not assumed) -- deliberately loose
// (every field optional) since that's the only honest way to type "whatever
// the network handed back". Normalizers below turn these into the real
// `frontend/src/api/types.ts` types with defaults for everything.
// ---------------------------------------------------------------------------

interface RawInstructor {
  first?: string;
  last?: string;
}

interface RawMeetingTime {
  day?: number;
  startMin?: number;
  endMin?: number;
  building?: string;
  session?: string;
}

interface RawSection {
  name?: string;
  teachMethod?: string;
  sectionNumber?: string;
  currentEnrol?: number;
  maxEnrol?: number;
  waitlist?: number;
  instructors?: RawInstructor[];
  meetingTimes?: RawMeetingTime[];
  deliveryModes?: string[];
}

/** `_course_summary_dict` (backend/api/courses.py) -- the `/api/courses` search-result row. */
interface RawCourseSummary {
  code?: string;
  title?: string;
  sectionCode?: string;
  credit?: number;
  campus?: string;
  breadth?: string[];
  sectionCount?: number;
  hasSeats?: boolean;
}

/** `_offering_dict` (backend/api/courses.py). */
interface RawOffering {
  sectionCode?: string;
  sections?: RawSection[];
}

/** `_detail_dict` (backend/api/courses.py) -- `/api/courses/:code`. Note there
 * is NO top-level `sectionCode`/`sections` here (unlike `RawCourseSummary`)
 * -- sections live per-offering, because a code can have more than one live
 * TTB entry (one per term). `normalizeCourseDetail` flattens `offerings[]`
 * into the flat `sections` this app's `Course` type promises everywhere. */
interface RawCourseDetail {
  code?: string;
  title?: string;
  credit?: number;
  campus?: string;
  description?: string;
  prerequisites?: string;
  corequisites?: string;
  exclusions?: string;
  breadth?: string[];
  distribution?: string[];
  terms?: string[];
  offerings?: RawOffering[];
  source?: string;
}

interface RawRequirementRule {
  credits?: number;
  description?: string;
  courseCodes?: string[];
}

interface RawRequirementCourse {
  code?: string;
  credits?: number;
  notes?: string;
}

interface RawRequirementGroup {
  heading?: string;
  credits?: number;
  isNote?: boolean;
  courseCodes?: string[];
  rules?: RawRequirementRule[];
  courses?: RawRequirementCourse[];
  notes?: string;
}

/** `_program_json`/`_program_detail_json` (backend/api/programs.py). List
 * rows (`/api/programs`) only carry the `_program_json` fields --
 * `completionRequirements`/`rawCompletionText`/`requirementsLoaded` are
 * `undefined` there, not just empty; `normalizeProgram` defaults them. */
interface RawProgram {
  code?: string;
  title?: string;
  programType?: string;
  department?: string;
  departmentUrl?: string;
  enrolmentRequirements?: string;
  totalCredits?: number;
  completionRequirements?: RawRequirementGroup[];
  rawCompletionText?: string;
  requirementsLoaded?: boolean;
}

/** `_requirements_json` (backend/api/programs.py) -- `/api/programs/:code/requirements`
 * and the `/requirements/reparse` POST both return this WRAPPER object, not
 * a bare `RequirementGroup[]` -- `normalizeRequirementsResponse` unwraps it. */
interface RawRequirementsResponse {
  code?: string;
  totalCredits?: number;
  requirementsLoaded?: boolean;
  completionRequirements?: RawRequirementGroup[];
  rawCompletionText?: string;
}

interface RawTranscriptCourse {
  code?: string;
  title?: string;
  credits?: number;
  mark?: number | null;
  grade?: string;
  session?: string;
  status?: string;
}

interface RawRequirementProgress {
  key?: string;
  label?: string;
  status?: string;
  earned?: number;
  required?: number;
  appliedCourses?: string[];
}

interface RawEnrolledProgramRef {
  code?: string;
  name?: string;
  startSession?: string;
  earnedCredits?: number;
  totalCredits?: number;
  percent?: number;
  requirementsLoaded?: boolean;
}

/** `GET /api/me` (backend/api/me.py `student_record`). */
interface RawMeResponse {
  programs?: RawEnrolledProgramRef[];
  transcript?: RawTranscriptCourse[];
  requirementProgress?: Record<string, RawRequirementProgress[]>;
  cgpa?: number;
}

/** `_program_refs`/`GET /api/me/programs` shape (backend/api/programs.py `_enrolment_json`). */
interface RawMyProgramsResponse {
  programs?: { code?: string; title?: string | null; startSession?: string | null }[];
}

/** `degree_credit_summary()` (backend/planner/validators.py `DegreeCreditSummary`),
 * `asdict()`'d as-is by `GET /api/me/summary` -- so, unlike the rest of that
 * route's payload, this nested object keeps its Python **snake_case** field
 * names verbatim. Same for `RawBreadthResult` below. */
interface RawDegreeCreditSummary {
  total_credits?: number;
  artsci_credits?: number;
  level_200_plus_credits?: number;
  level_300_plus_credits?: number;
  credits_by_subject?: Record<string, number>;
  same_subject_over_cap?: Record<string, number>;
}

/** `evaluate_breadth()` (backend/planner/validators.py `BreadthResult`), same
 * `asdict()` snake_case note as `RawDegreeCreditSummary`. `earned_by_category`
 * is keyed by the breadth category NUMBER (1-5), stringified by JSON. */
interface RawBreadthResult {
  earned_by_category?: Record<string, number>;
  satisfied?: boolean;
}

/** `GET /api/me/summary` (backend/api/me.py `summary`). There is no
 * `/api/me/degree-audit` or `/api/me/breadth` route on the backend at all --
 * `getMyDegreeAudit`/`getMyBreadth` below both derive their result from THIS
 * endpoint's response, same as `getMySummary` does. */
interface RawMeSummaryResponse {
  credits?: RawDegreeCreditSummary;
  breadth?: RawBreadthResult;
  gpa?: { cgpa?: number | null; creditsCounted?: number; recent?: number | null };
}

/** One `Issue` (backend/planner/types.py), `asdict()`'d by `backend/api/_audit.py`'s
 * `_issues()` -- this is what `GET /api/me/alerts`'s `alerts[]` entries
 * actually are. Nothing like the frontend `Alert` shape
 * (`{id, kind, title, time?, read?}`) -- `normalizeAlertFromIssue` adapts it,
 * it does not just unwrap an envelope. */
interface RawIssue {
  severity?: string;
  code?: string;
  message?: string;
  course_code?: string | null;
}

/** `create_share`'s response (backend/api/share.py) -- `{token, path}`, not
 * `{token, url}`; `path` is site-relative (`"/share/<token>"`). */
interface RawCreateShareResponse {
  token?: string;
  path?: string;
}

/** `view_share`'s public response (backend/api/share.py) -- deliberately NOT
 * a `StudentRecord`: no `transcript`, no per-program `requirementProgress`,
 * and each program row is `{code, title}` (not `{code, name, startSession}`).
 * `normalizeSharedRecord` maps what genuinely carries over and leaves the
 * rest unset (matching the `Partial<StudentRecord>` contract, which every
 * consumer -- Share.tsx -- already treats as optional field-by-field). */
interface RawShareResponse {
  programs?: { code?: string; title?: string | null }[];
}

// ---------------------------------------------------------------------------
// Normalizers
// ---------------------------------------------------------------------------

function normalizeInstructor(raw: RawInstructor | null | undefined): Instructor {
  return { first: asStr(raw?.first), last: asStr(raw?.last) };
}

function normalizeMeetingTime(raw: RawMeetingTime | null | undefined): MeetingTime {
  const day = asNum(raw?.day, 1);
  return {
    day: (day >= 1 && day <= 7 ? day : 1) as MeetingTime["day"],
    startMin: asNum(raw?.startMin, 0),
    endMin: asNum(raw?.endMin, 0),
    building: asStr(raw?.building),
    session: asStr(raw?.session),
  };
}

function normalizeSection(raw: RawSection | null | undefined): Section {
  return {
    name: asStr(raw?.name),
    teachMethod: asStr(raw?.teachMethod, "LEC") as TeachMethod,
    sectionNumber: asStr(raw?.sectionNumber),
    currentEnrol: asNum(raw?.currentEnrol, 0),
    maxEnrol: asNum(raw?.maxEnrol, 0),
    waitlist: asNum(raw?.waitlist, 0),
    instructors: asArray<RawInstructor>(raw?.instructors).map(normalizeInstructor),
    meetingTimes: asArray<RawMeetingTime>(raw?.meetingTimes).map(normalizeMeetingTime),
    deliveryModes: asArray<string>(raw?.deliveryModes),
  };
}

/** `/api/courses` search rows -- no per-section detail is returned here (see
 * `RawCourseSummary`), so `sections` is honestly `[]`, not fabricated. Screens
 * that need live sections (meet times, seats) must fetch `getCourse(code)`. */
function normalizeCourseSummary(raw: RawCourseSummary | null | undefined): Course {
  return {
    code: asStr(raw?.code),
    title: asStr(raw?.title),
    sectionCode: asStr(raw?.sectionCode, "F") as Term,
    credit: asNum(raw?.credit, 0.5),
    campus: asStr(raw?.campus),
    description: "",
    prerequisites: "",
    corequisites: "",
    exclusions: "",
    breadth: asArray<string>(raw?.breadth),
    distribution: [],
    sections: [],
    sectionCount: asNum(raw?.sectionCount, 0),
    hasSeats: asBool(raw?.hasSeats),
  };
}

/** `/api/courses/:code` detail -- flattens the backend's per-term
 * `offerings[].sections` into the flat `sections` array `Course` promises.
 * THIS is the fix for the confirmed Courses/CourseDetail crash: every screen
 * that reads `course.sections` (Courses.tsx, CourseDetail.tsx, Plan.tsx,
 * Timetable.tsx, TimetableOptimize.tsx, RequirementDetail.tsx) was getting
 * `undefined` before, because the raw response has no top-level `sections`
 * at all -- only `offerings[].sections`. */
function normalizeCourseDetail(raw: RawCourseDetail | null | undefined): Course {
  const offerings = asArray<RawOffering>(raw?.offerings);
  const sections = offerings.flatMap((o) => asArray<RawSection>(o?.sections).map(normalizeSection));
  const terms = asArray<string>(raw?.terms);
  const fallbackTerm = asStr(terms[0] ?? offerings[0]?.sectionCode, "F") as Term;
  return {
    code: asStr(raw?.code),
    title: asStr(raw?.title),
    sectionCode: fallbackTerm,
    credit: asNum(raw?.credit, 0.5),
    campus: asStr(raw?.campus),
    description: asStr(raw?.description),
    prerequisites: asStr(raw?.prerequisites),
    corequisites: asStr(raw?.corequisites),
    exclusions: asStr(raw?.exclusions),
    breadth: asArray<string>(raw?.breadth),
    distribution: asArray<string>(raw?.distribution),
    sections,
    sectionCount: sections.length,
    hasSeats: sections.some((s) => s.currentEnrol < s.maxEnrol),
  };
}

function normalizeRequirementRule(raw: RawRequirementRule | null | undefined): RequirementRule {
  return {
    credits: asNum(raw?.credits, 0),
    description: asStr(raw?.description),
    courseCodes: asArray<string>(raw?.courseCodes),
  };
}

function normalizeRequirementCourse(raw: RawRequirementCourse | null | undefined): RequirementCourse {
  return { code: asStr(raw?.code), credits: asNum(raw?.credits, 0), notes: asStr(raw?.notes) };
}

function normalizeRequirementGroup(raw: RawRequirementGroup | null | undefined): RequirementGroup {
  return {
    heading: asStr(raw?.heading),
    credits: asNum(raw?.credits, 0),
    isNote: asBool(raw?.isNote),
    courseCodes: asArray<string>(raw?.courseCodes),
    rules: asArray<RawRequirementRule>(raw?.rules).map(normalizeRequirementRule),
    courses: asArray<RawRequirementCourse>(raw?.courses).map(normalizeRequirementCourse),
    notes: asStr(raw?.notes),
  };
}

/** `/api/programs` (search) rows only carry `_program_json`'s fields --
 * `completionRequirements`/`rawCompletionText` are genuinely absent there
 * (not merely empty), so this defaults them rather than trusting `Program`'s
 * required fields are actually present on a list row. `/api/programs/:code`
 * detail rows go through the same function; the extra fields are simply
 * already there in that response. */
function normalizeProgram(raw: RawProgram | null | undefined): Program {
  return {
    code: asStr(raw?.code),
    title: asStr(raw?.title),
    programType: asStr(raw?.programType) as ProgramType,
    department: asStr(raw?.department),
    departmentUrl: asStr(raw?.departmentUrl),
    enrolmentRequirements: asStr(raw?.enrolmentRequirements),
    totalCredits: asNum(raw?.totalCredits, 0),
    completionRequirements: asArray<RawRequirementGroup>(raw?.completionRequirements).map(normalizeRequirementGroup),
    rawCompletionText: asStr(raw?.rawCompletionText),
    requirementsLoaded: asBool(raw?.requirementsLoaded),
  };
}

/** Unwraps `_requirements_json`'s `{completionRequirements: [...], ...}`
 * envelope -- the `/requirements` and `/requirements/reparse` routes return
 * that whole object, never a bare array, except via `http()`'s 404 fallback
 * (already `[]` in that case, handled by the `Array.isArray` branch). Without
 * this unwrap, a `for (const g of groups)` call site (CourseDetail.tsx) would
 * throw "groups is not iterable" on the real (non-404) response shape. */
function normalizeRequirementsResponse(
  raw: RawRequirementsResponse | RawRequirementGroup[] | null | undefined,
): RequirementGroup[] {
  const list = Array.isArray(raw) ? raw : raw?.completionRequirements;
  return asArray<RawRequirementGroup>(list).map(normalizeRequirementGroup);
}

function normalizeTranscriptCourse(raw: RawTranscriptCourse | null | undefined): TranscriptCourse {
  const status = raw?.status;
  const validStatus: TranscriptCourseStatus =
    status === "completed" || status === "in_progress" || status === "planned" || status === "extra"
      ? status
      : "completed";
  return {
    code: asStr(raw?.code),
    title: asStr(raw?.title),
    credits: asNum(raw?.credits, 0.5),
    mark: asNullableNum(raw?.mark),
    grade: asStr(raw?.grade),
    session: asStr(raw?.session),
    status: validStatus,
  };
}

function normalizeRequirementProgressRow(raw: RawRequirementProgress | null | undefined): RequirementProgress {
  const status = raw?.status;
  const validStatus: RequirementProgressStatus =
    status === "complete" || status === "na" ? status : "incomplete";
  return {
    key: asStr(raw?.key),
    label: asStr(raw?.label),
    status: validStatus,
    earned: asNum(raw?.earned, 0),
    required: asNum(raw?.required, 0),
    appliedCourses: asArray<string>(raw?.appliedCourses),
  };
}

function normalizeRequirementProgressMap(
  raw: Record<string, RawRequirementProgress[]> | null | undefined,
): Record<string, RequirementProgress[]> {
  const out: Record<string, RequirementProgress[]> = {};
  for (const [code, rows] of Object.entries(asRecord<RawRequirementProgress[]>(raw))) {
    out[code] = asArray<RawRequirementProgress>(rows).map(normalizeRequirementProgressRow);
  }
  return out;
}

function normalizeEnrolledProgramRef(raw: RawEnrolledProgramRef | null | undefined): EnrolledProgramRef {
  const code = asStr(raw?.code);
  return {
    code,
    name: asStr(raw?.name, code),
    startSession: asStr(raw?.startSession),
    earnedCredits: asNum(raw?.earnedCredits, 0),
    totalCredits: asNum(raw?.totalCredits, 0),
    percent: asNum(raw?.percent, 0),
    requirementsLoaded: raw?.requirementsLoaded === true,
  };
}

function normalizeStudentRecord(raw: RawMeResponse | null | undefined): StudentRecord {
  return {
    programs: asArray<RawEnrolledProgramRef>(raw?.programs).map(normalizeEnrolledProgramRef),
    transcript: asArray<RawTranscriptCourse>(raw?.transcript).map(normalizeTranscriptCourse),
    requirementProgress: normalizeRequirementProgressMap(raw?.requirementProgress),
    cgpa: asNum(raw?.cgpa, 0),
  };
}

/** The subject with the most credits, for `DegreeAuditData.topDesignator`
 * (design/09 §1's same-subject ≤15.0 cap) -- the backend only reports
 * `same_subject_over_cap` (entries that already broke the cap), not "the top
 * one regardless", so this is derived from the full `credits_by_subject`
 * map instead. */
function topDesignatorFrom(bySubject: Record<string, number>): { code: string; credits: number } | null {
  const entries = Object.entries(bySubject);
  if (entries.length === 0) return null;
  const [code, credits] = entries.reduce((best, cur) => (cur[1] > best[1] ? cur : best));
  return { code, credits };
}

/** Derives `DegreeAuditData` from `GET /api/me/summary` -- there is no
 * `/api/me/degree-audit` route on the backend (confirmed: `backend/api/me.py`
 * only defines `""`, `/summary`, `/transcript`, `/requirements`, `/alerts`).
 * Before this fix, `getMyDegreeAudit` hit that nonexistent path, got a plain
 * 404, and `http()`'s TTB-quirk fallback silently resolved it to `[]` -- an
 * array standing in for what callers (Requirements.tsx, Dashboard.tsx)
 * treated as a `DegreeAuditData` object, so `audit.totalEarned.toFixed(1)`
 * threw "Cannot read properties of undefined (reading 'toFixed')". */
function deriveDegreeAudit(raw: RawMeSummaryResponse | null | undefined): DegreeAuditData {
  const credits = raw?.credits;
  return {
    totalEarned: asNum(credits?.total_credits, 0),
    artsciEarned: asNum(credits?.artsci_credits, 0),
    level200: asNum(credits?.level_200_plus_credits, 0),
    level300: asNum(credits?.level_300_plus_credits, 0),
    topDesignator: topDesignatorFrom(asRecord<number>(credits?.credits_by_subject)),
    cgpa: asNullableNum(raw?.gpa?.cgpa) ?? 0,
  };
}

/** Derives `BreadthData` from `GET /api/me/summary` -- same "no dedicated
 * `/api/me/breadth` route" situation as `deriveDegreeAudit` above.
 * `earned_by_category` is keyed 1-5 (stringified by JSON), mapped here onto
 * the `BR1`..`BR5` keys `BreadthTracker`/`evaluateBreadth` expect. */
function deriveBreadthData(raw: RawMeSummaryResponse | null | undefined): BreadthData {
  const earned = asRecord<number>(raw?.breadth?.earned_by_category);
  const get = (n: number) => asNum(earned[String(n)], 0);
  return { BR1: get(1), BR2: get(2), BR3: get(3), BR4: get(4), BR5: get(5) };
}

/** Derives the flat `Summary` (Dashboard KPI row / `AppLayout`'s ProgressStrip)
 * from the same `/api/me/summary` nested response. `creditsTotal` is always
 * the degree's fixed 20.0 (design/09 §1's minimum), matching what the
 * backend's own credit-summary is evaluated against. */
function deriveSummary(raw: RawMeSummaryResponse | null | undefined): Summary {
  const totalEarned = asNum(raw?.credits?.total_credits, 0);
  const creditsTotal = DEGREE_MINIMUMS.total;
  return {
    creditsEarned: totalEarned,
    creditsTotal,
    breadthSatisfied: asBool(raw?.breadth?.satisfied),
    cgpa: asNullableNum(raw?.gpa?.cgpa) ?? 0,
    degreePct: creditsTotal > 0 ? Math.round((totalEarned / creditsTotal) * 100) : 0,
  };
}

/** `GET /api/me/alerts`'s `alerts[]` entries are `Issue` dataclasses
 * (`severity`/`code`/`message`/`course_code`), not the frontend `Alert` shape
 * (`id`/`kind`/`title`/`time?`/`read?`) -- there's no natural `AlertKind` for
 * a degree-credit/combination validator issue, so every one maps to "info"
 * and `message` becomes the display title. Before this fix `getMyAlerts`
 * didn't even unwrap the `{alerts: [...]}` envelope, so `alerts.filter(...)`
 * in Dashboard.tsx/AppLayout.tsx threw "alerts.filter is not a function". */
function normalizeAlertFromIssue(raw: RawIssue | null | undefined, index: number): Alert {
  const kind: AlertKind = "info";
  return {
    id: `${asStr(raw?.code, "issue")}-${index}`,
    kind,
    title: asStr(raw?.message, asStr(raw?.code, "Degree requirement issue")),
    time: undefined,
    read: false,
  };
}

/** Backend `create_share` (backend/api/share.py) returns `{token, path}` --
 * `path` is site-relative; screens (Settings.tsx's ShareLinkDialog) want an
 * absolute, copyable `url`, which is built here rather than each call site
 * reconstructing it (or, before this fix, reading a `url` field that was
 * never in the response at all). */
function normalizeCreateShareResponse(raw: RawCreateShareResponse | null | undefined): { token: string; url: string } {
  const token = asStr(raw?.token);
  const path = asStr(raw?.path, token ? `/share/${token}` : "");
  return { token, url: path ? `${window.location.origin}${path}` : "" };
}

/** Backend `view_share` (backend/api/share.py) deliberately never returns a
 * `transcript` or per-program `requirementProgress` (grades/marks never
 * leave the owner's session — see that file's module docstring), and its
 * program rows are `{code, title}`, not `{code, name, startSession}`. Mapping
 * `title` -> `name` here (rather than leaving it unmapped) is the fix for
 * Share.tsx's program rows always rendering a blank label. Everything this
 * function doesn't set is left `undefined`, matching the `Partial<StudentRecord>`
 * contract Share.tsx already renders defensively field-by-field. */
function normalizeSharedRecord(raw: RawShareResponse | null | undefined): Partial<StudentRecord> {
  return {
    programs: asArray<{ code?: string; title?: string | null }>(raw?.programs).map((p) => ({
      code: asStr(p?.code),
      name: asStr(p?.title ?? undefined, asStr(p?.code)),
      startSession: "",
      earnedCredits: 0,
      totalCredits: 0,
      percent: 0,
      requirementsLoaded: false,
    })),
  };
}

export const httpClient: ApiClient = {
  getSessions: () =>
    http<{ sessions?: { code?: string }[] } | string[]>("/sessions").then((res) =>
      Array.isArray(res)
        ? res.map((s) => asStr(s))
        : asArray<{ code?: string }>(res?.sessions).map((s) => asStr(s?.code)),
    ),

  getPrograms: (params) =>
    http<{ programs?: RawProgram[] } | RawProgram[]>(`/programs${qs(params)}`).then((res) =>
      (Array.isArray(res) ? res : asArray<RawProgram>(res?.programs)).map(normalizeProgram),
    ),
  getAllPrograms: async () => {
    // Page until a short page. The 10-page ceiling only bounds a runaway —
    // the full catalog is ~420 programs (and the backend serves a browse from
    // at most 500 cached rows), so 5 pages is the expected worst case.
    const pageSize = 100;
    const all: Program[] = [];
    for (let page = 1; page <= 10; page += 1) {
      const batch = await httpClient.getPrograms({ page, pageSize });
      all.push(...batch);
      if (batch.length < pageSize) break;
    }
    return all;
  },
  getProgram: (code) =>
    httpOrNull<RawProgram>(`/programs/${encodeURIComponent(code)}`).then((res) => (res ? normalizeProgram(res) : null)),
  getProgramRequirements: (code) =>
    http<RawRequirementsResponse | RawRequirementGroup[]>(`/programs/${encodeURIComponent(code)}/requirements`).then(
      normalizeRequirementsResponse,
    ),
  reparseProgramRequirements: (code) =>
    http<RawRequirementsResponse | RawRequirementGroup[]>(
      `/programs/${encodeURIComponent(code)}/requirements/reparse`,
      { method: "POST" },
    ).then(normalizeRequirementsResponse),

  getCourses: (params) =>
    http<{ courses?: RawCourseSummary[] } | RawCourseSummary[]>(`/courses${qs(params)}`).then((res) =>
      (Array.isArray(res) ? res : asArray<RawCourseSummary>(res?.courses)).map(normalizeCourseSummary),
    ),
  getCourse: (code) =>
    httpOrNull<RawCourseDetail>(`/courses/${encodeURIComponent(code)}`).then((res) =>
      res ? normalizeCourseDetail(res) : null,
    ),

  // `POST /api/plan/validate` returns `{issues: [{severity, type, courseCode,
  // message}], summary, programs}` (backend/api/plan.py) -- normalize the
  // wire shape's `type`/`courseCode` to our `PlanValidationIssue`'s
  // `kind`/`code` at this boundary, so screens only ever see the one issue
  // shape regardless of mock vs live backend.
  validatePlan: (items) =>
    http<{ issues?: { severity?: string; type?: string; courseCode?: string; message?: string }[] }>(
      "/plan/validate",
      { method: "POST", body: JSON.stringify({ items }) },
    ).then((res) => ({
      issues: asArray<{ severity?: string; type?: string; courseCode?: string; message?: string }>(res?.issues).map((iss) => ({
        severity: (asStr(iss?.severity, "error") as PlanValidationIssue["severity"]) || "error",
        kind: asStr(iss?.type, ""),
        code: asStr(iss?.courseCode, ""),
        message: asStr(iss?.message, ""),
      })),
    })),

  getMyRecord: () => http<RawMeResponse>("/me").then(normalizeStudentRecord),

  getMyTranscript: () =>
    http<{ sessions?: unknown; cgpa?: unknown; warnings?: unknown }>("/me/transcript").then((res) => ({
      sessions: asArray<{ session?: unknown; courses?: unknown; sgpa?: unknown; cumGpa?: unknown }>(
        res?.sessions,
      ).map((g) => ({
        session: asStr(g?.session),
        courses: asArray<{
          code?: unknown;
          title?: unknown;
          credits?: unknown;
          mark?: unknown;
          grade?: unknown;
          status?: unknown;
        }>(g?.courses).map((c) => ({
          code: asStr(c?.code),
          title: asStr(c?.title),
          credits: asNum(c?.credits, 0),
          mark: asNullableNum(c?.mark),
          grade: typeof c?.grade === "string" && c.grade !== "" ? c.grade : null,
          status: (asStr(c?.status, "completed") as TranscriptCourseStatus) || "completed",
        })),
        sgpa: asNullableNum(g?.sgpa),
        cumGpa: asNullableNum(g?.cumGpa),
      })),
      cgpa: asNullableNum(res?.cgpa),
      warnings: asArray<unknown>(res?.warnings).filter((w): w is string => typeof w === "string"),
    })),
  // `GET /api/me/requirements` is a DIFFERENT endpoint (plan-combination
  // structural check, `{combination, issues}`) -- not the per-program
  // `Record<code, RequirementProgress[]>` this method promises. The real data
  // is `GET /api/me`'s own `requirementProgress` field (already computed
  // server-side by `backend/api/me.py::_requirement_progress_by_program`), so
  // this reuses that endpoint instead of hitting the mismatched one. Before
  // this fix, every "My programs" progress bar silently stayed at 0/0.
  getMyRequirementProgress: () =>
    http<RawMeResponse>("/me").then((res) => normalizeRequirementProgressMap(res?.requirementProgress)),
  getMyDegreeAudit: () => http<RawMeSummaryResponse>("/me/summary").then(deriveDegreeAudit),
  getMyBreadth: () =>
    http<RawMeSummaryResponse>("/me/summary").then((res) => {
      const data = deriveBreadthData(res);
      return { data, evaluation: evaluateBreadth(data) };
    }),
  getMySummary: () => http<RawMeSummaryResponse>("/me/summary").then(deriveSummary),
  getMyAlerts: () =>
    http<{ alerts?: RawIssue[] } | RawIssue[]>("/me/alerts").then((res) =>
      (Array.isArray(res) ? res : asArray<RawIssue>(res?.alerts)).map(normalizeAlertFromIssue),
    ),

  // `/api/me/programs` (the reorderable enrolled list) carries no completion
  // summary -- that's authoritative only on `GET /api/me`'s `programs[]`
  // (getMyRecord). These defaults keep the type total; screens that need real
  // completion (Programs.tsx) read it from getMyRecord, not from here.
  getMyPrograms: () =>
    http<RawMyProgramsResponse>("/me/programs").then((res) =>
      asArray<{ code?: string; title?: string | null; startSession?: string | null }>(res?.programs).map((p) => ({
        code: asStr(p?.code),
        name: asStr(p?.title ?? undefined, asStr(p?.code)),
        startSession: asStr(p?.startSession ?? undefined),
        earnedCredits: 0,
        totalCredits: 0,
        percent: 0,
        requirementsLoaded: false,
      })),
    ),
  // These three mutations previously defaulted to the list endpoints'
  // `fallback404: "array"` behavior, which -- since the return value is
  // discarded (`.then(() => undefined)`) either way -- meant a genuine 404
  // (e.g. "not enrolled in that program") was silently swallowed as success
  // instead of rejecting into the `.catch()` blocks Programs.tsx already has
  // for exactly this case. `fallback404: "throw"` lets real errors surface.
  addMyProgram: (code) =>
    http("/me/programs", { method: "POST", body: JSON.stringify({ code }) }, { fallback404: "throw" }).then(
      () => undefined,
    ),
  removeMyProgram: (code) =>
    http(`/me/programs/${encodeURIComponent(code)}`, { method: "DELETE" }, { fallback404: "throw" }).then(
      () => undefined,
    ),
  reorderMyPrograms: (codes) =>
    http(
      "/me/programs/order",
      { method: "PUT", body: JSON.stringify({ codes }) },
      { fallback404: "throw" },
    ).then(() => undefined),

  createShareLink: () =>
    http<RawCreateShareResponse>("/share", { method: "POST" }, { fallback404: "throw" }).then(
      normalizeCreateShareResponse,
    ),
  getShared: (token) =>
    httpOrNull<RawShareResponse>(`/share/${encodeURIComponent(token)}`).then((res) =>
      res ? normalizeSharedRecord(res) : null,
    ),
};

/** The client screens should use. Real backend unless `VITE_API_BASE=mock` opted into the demo adapter (see `isMockApi` above). */
export const api: ApiClient = isMockApi ? mockClient : httpClient;
