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
 */
import * as mock from "./mock";
import { DEGREE_MINIMUMS, evaluateBreadth } from "./degreeAudit";
import { BREADTH_KEYS } from "./types";
import type {
  Alert,
  AlertKind,
  BreadthData,
  Course,
  DegreeAuditData,
  EnrolledProgramRef,
  PlanValidationIssue,
  Program,
  SessionCode,
  StudentRecord,
  Summary,
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

async function http<T>(path: string, init?: RequestInit): Promise<T> {
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
  if (res.status === 404) {
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
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

function qs(params: object | undefined): string {
  if (!params) return "";
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== "");
  if (entries.length === 0) return "";
  return `?${new URLSearchParams(entries as [string, string][]).toString()}`;
}

// `GET /api/me/summary` (backend/api/me.py `summary()`) is the one endpoint
// that actually computes degree-credit / breadth / GPA numbers server-side —
// there is no separate `/me/degree-audit` or `/me/breadth` route (backend/
// api/_audit.py's `degree_progress`/`breadth_progress` helpers that would
// back such routes exist but were never wired to a blueprint route). Rather
// than invent backend endpoints, `getMyDegreeAudit`/`getMyBreadth`/
// `getMySummary` below all read this one envelope and reshape it client-side
// into the three separate contracts screens expect (mirrors what
// `mockClient` does from its own static fixtures).
interface RawMeSummary {
  credits: {
    total_credits: number;
    artsci_credits: number;
    level_200_plus_credits: number;
    level_300_plus_credits: number;
    credits_by_subject: Record<string, number>;
    same_subject_over_cap: Record<string, number>;
  };
  breadth: {
    earned_by_category: Record<string, number>;
    satisfied: boolean;
  };
  gpa: {
    cgpa: number | null;
    creditsCounted: number;
    recent: number | null;
  };
}

function fetchMeSummary(): Promise<RawMeSummary> {
  return http<RawMeSummary>("/me/summary");
}

/** The subject with the most credits (design/09 same-subject <=15.0 cap), or
 * `null` if the student has no credited courses yet. */
function topDesignatorFrom(creditsBySubject: Record<string, number>): { code: string; credits: number } | null {
  const entries = Object.entries(creditsBySubject);
  if (entries.length === 0) return null;
  const [code, credits] = entries.reduce((max, entry) => (entry[1] > max[1] ? entry : max));
  return { code, credits };
}

function breadthDataFrom(earnedByCategory: Record<string, number>): BreadthData {
  const out = {} as BreadthData;
  BREADTH_KEYS.forEach((key, i) => {
    out[key] = earnedByCategory[String(i + 1)] ?? 0;
  });
  return out;
}

// `GET /api/me/alerts` (backend/api/me.py `alerts()`) returns
// `{"alerts": [...]}, `, each item shaped as a validator `Issue`
// (`{severity, code, message, course_code}` — backend/planner/types.py) —
// neither the envelope nor the item shape matches this contract's bare
// `Alert[]` (`{id, kind, title, time?, read?}`, frontend/src/api/types.ts).
// Unwrap and remap both. There's no persisted "read" state server-side (no
// mark-as-read endpoint), so every alert starts unread, same as the mock's
// no-`read`-key entries.
interface RawAlert {
  severity: "error" | "warning" | "info";
  code: string;
  message: string;
  course_code: string | null;
}

function alertFrom(raw: RawAlert, index: number): Alert {
  const kind: AlertKind = raw.code === "distinct-credits" || raw.code === "one-type-per-subject" ? "prereq" : "info";
  return {
    id: `${raw.code || "alert"}-${index}`,
    kind,
    title: raw.message,
  };
}

export const httpClient: ApiClient = {
  // `GET /api/sessions` returns `{sessions: [{code, term, termName, year,
  // label}, ...], defaultSession}` (backend/api/courses.py), not the bare
  // `SessionCode[]` this contract promises -- unwrap to codes, tolerating a
  // bare array (the 404 fallback in `http()` yields `[]`).
  getSessions: () =>
    http<{ sessions: { code: SessionCode }[] } | SessionCode[]>("/sessions").then((res) =>
      Array.isArray(res) ? res : res.sessions.map((s) => s.code),
    ),

  // `GET /api/programs` and `/api/courses` return a paginated envelope
  // (`{programs: [...], page, total, ...}` / `{courses: [...], ...}`), not a
  // bare array -- except on the legit "no-match 404" path (see `http()`
  // above), where the 404 fallback is already the bare `[]` this unwraps to.
  getPrograms: (params) =>
    http<{ programs: Program[] } | Program[]>(`/programs${qs(params)}`).then((res) =>
      Array.isArray(res) ? res : res.programs,
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
  getProgram: (code) => http(`/programs/${encodeURIComponent(code)}`),
  // `GET /api/programs/:code/requirements` returns the whole `Program`-
  // requirements envelope (`{code, totalCredits, requirementsLoaded,
  // completionRequirements, rawCompletionText}`, backend/api/programs.py
  // `_requirements_json`), not the bare `RequirementGroup[]` this contract
  // promises -- unwrap, same as `getPrograms`/`getCourses` above.
  getProgramRequirements: (code) =>
    http<{ completionRequirements: Program["completionRequirements"] }>(
      `/programs/${encodeURIComponent(code)}/requirements`,
    ).then((res) => res.completionRequirements),
  // `POST /api/programs/:code/requirements/reparse` returns the full
  // `Program` detail body (+ `parseReport`), not the bare
  // `RequirementGroup[]` this contract promises -- same unwrap.
  reparseProgramRequirements: (code) =>
    http<{ completionRequirements: Program["completionRequirements"] }>(
      `/programs/${encodeURIComponent(code)}/requirements/reparse`,
      { method: "POST" },
    ).then((res) => res.completionRequirements),

  getCourses: (params) =>
    http<{ courses: Course[] } | Course[]>(`/courses${qs(params)}`).then((res) =>
      Array.isArray(res) ? res : res.courses,
    ),
  getCourse: (code) => http(`/courses/${encodeURIComponent(code)}`),

  // `POST /api/plan/validate` returns `{issues: [{severity, type, courseCode,
  // message}], summary, programs}` (backend/api/plan.py) -- normalize the
  // wire shape's `type`/`courseCode` to our `PlanValidationIssue`'s
  // `kind`/`code` at the client boundary (same pattern as the
  // getPrograms/getCourses envelope-unwrap above), so screens only ever see
  // the one issue shape regardless of mock vs live backend.
  validatePlan: (items) =>
    http<{ issues: { severity: string; type: string; courseCode: string; message: string }[] }>(
      "/plan/validate",
      { method: "POST", body: JSON.stringify({ items }) },
    ).then((res) => ({
      issues: (res.issues ?? []).map((iss) => ({
        severity: (iss.severity as PlanValidationIssue["severity"]) || "error",
        kind: iss.type,
        code: iss.courseCode ?? "",
        message: iss.message,
      })),
    })),

  getMyRecord: () => http("/me"),
  // `GET /api/me/requirements` (backend/api/me.py `requirements()`) is the
  // program-*combination* check (`{combination, issues}`), not per-program
  // `RequirementProgress[]` -- that data already exists, computed correctly,
  // as the `requirementProgress` field of `GET /api/me` (backend/api/me.py
  // `student_record()` via `_requirement_progress_by_program`). Read it from
  // there instead of the wrong endpoint.
  getMyRequirementProgress: () =>
    http<StudentRecord>("/me").then((res) => res.requirementProgress),
  // No dedicated `/me/degree-audit` or `/me/breadth` route exists server-side
  // (see `fetchMeSummary` above) -- derive both from `/me/summary`.
  getMyDegreeAudit: () =>
    fetchMeSummary().then((res) => ({
      totalEarned: res.credits.total_credits,
      artsciEarned: res.credits.artsci_credits,
      level200: res.credits.level_200_plus_credits,
      level300: res.credits.level_300_plus_credits,
      topDesignator: topDesignatorFrom(res.credits.credits_by_subject),
      cgpa: res.gpa.cgpa ?? 0,
    })),
  getMyBreadth: () =>
    fetchMeSummary().then((res) => {
      const data = breadthDataFrom(res.breadth.earned_by_category);
      return { data, evaluation: evaluateBreadth(data) };
    }),
  // `GET /api/me/summary`'s actual body (`{credits, degreeIssues, breadth,
  // gpa, standing, probationCap, graduation}`) doesn't match this contract's
  // flat `Summary` (`{creditsEarned, creditsTotal, breadthSatisfied, cgpa,
  // degreePct}`) at all -- map the fields this screen needs out of it.
  getMySummary: () =>
    fetchMeSummary().then((res) => {
      const creditsEarned = res.credits.total_credits;
      const creditsTotal = DEGREE_MINIMUMS.total;
      return {
        creditsEarned,
        creditsTotal,
        breadthSatisfied: res.breadth.satisfied,
        cgpa: res.gpa.cgpa ?? 0,
        degreePct: creditsTotal > 0 ? Math.round((creditsEarned / creditsTotal) * 100) : 0,
      };
    }),
  // `GET /api/me/alerts` returns `{"alerts": [...]}`, each item a validator
  // `Issue` (`{severity, code, message, course_code}`), not the bare
  // `Alert[]` (`{id, kind, title, ...}`) this contract promises -- unwrap
  // AND remap (see `alertFrom` above). This was the confirmed crash: Dashboard
  // called `.filter` directly on the `{alerts: [...]}` envelope object.
  getMyAlerts: () =>
    http<{ alerts: RawAlert[] } | Alert[]>("/me/alerts").then((res) =>
      Array.isArray(res) ? res : res.alerts.map(alertFrom),
    ),

  getMyPrograms: () =>
    http<{ programs: { code: string; title: string | null; startSession: string | null }[] }>(
      "/me/programs",
    ).then((res) => res.programs.map((p) => ({ code: p.code, name: p.title ?? p.code, startSession: p.startSession ?? "" }))),
  addMyProgram: (code) =>
    http("/me/programs", { method: "POST", body: JSON.stringify({ code }) }).then(() => undefined),
  removeMyProgram: (code) =>
    http(`/me/programs/${encodeURIComponent(code)}`, { method: "DELETE" }).then(() => undefined),
  reorderMyPrograms: (codes) =>
    http("/me/programs/order", { method: "PUT", body: JSON.stringify({ codes }) }).then(() => undefined),

  // `POST /api/share` (backend/api/share.py `create_share`) returns
  // `{token, path}` (`path` a site-relative path, e.g. "/share/abc123"), not
  // the `{token, url}` this contract promises -- build the absolute url
  // client-side, same as `mockClient` does with `window.location.origin`.
  createShareLink: () =>
    http<{ token: string; path: string }>("/share", { method: "POST" }).then((res) => ({
      token: res.token,
      url: `${window.location.origin}${res.path}`,
    })),
  getShared: (token) => http(`/share/${encodeURIComponent(token)}`),
};

/** The client screens should use. Real backend unless `VITE_API_BASE=mock` opted into the demo adapter (see `isMockApi` above). */
export const api: ApiClient = isMockApi ? mockClient : httpClient;
