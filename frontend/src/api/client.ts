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
import { evaluateBreadth } from "./degreeAudit";
import type {
  Alert,
  BreadthData,
  Course,
  DegreeAuditData,
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
}

/** The full surface a screen can call. Both `mockClient` and `httpClient` implement this. */
export interface ApiClient {
  // Reference data
  getSessions(): Promise<SessionCode[]>;

  // Programs
  getPrograms(params?: ProgramSearchParams): Promise<Program[]>;
  getProgram(code: string): Promise<Program | null>;
  getProgramRequirements(code: string): Promise<Program["completionRequirements"]>;
  /** POST /api/programs/:code/requirements/reparse — on-demand Gemini grouper, ~10-20s. */
  reparseProgramRequirements(code: string): Promise<Program["completionRequirements"]>;

  // Courses
  getCourses(params?: CourseSearchParams): Promise<Course[]>;
  getCourse(code: string): Promise<Course | null>;

  // Me
  getMyRecord(): Promise<StudentRecord>;
  getMyRequirementProgress(): Promise<StudentRecord["requirementProgress"]>;
  getMyDegreeAudit(): Promise<DegreeAuditData>;
  getMyBreadth(): Promise<{ data: BreadthData; evaluation: ReturnType<typeof evaluateBreadth> }>;
  getMySummary(): Promise<Summary>;
  getMyAlerts(): Promise<Alert[]>;

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

  getMyRecord: () => delay(mock.mockStudentRecord),
  getMyRequirementProgress: () => delay(mock.mockStudentRecord.requirementProgress),
  getMyDegreeAudit: () => delay(mock.mockDegreeAudit),
  getMyBreadth: () => delay({ data: mock.mockBreadthData, evaluation: evaluateBreadth(mock.mockBreadthData) }),
  getMySummary: () => delay(mock.mockSummary),
  getMyAlerts: () => delay(mock.mockAlerts),

  createShareLink: () => delay({ token: "demo-share-token", url: `${window.location.origin}/share/demo-share-token` }),
  getShared: (token) =>
    delay(
      token === "demo-share-token"
        ? { programs: mock.mockStudentRecord.programs, cgpa: mock.mockStudentRecord.cgpa }
        : null,
    ),
};

const API_BASE = import.meta.env.VITE_API_BASE;

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (res.status === 404) {
    // Design/06 + conventions.md: TTB-backed no-match search legitimately 404s — treat as empty, not an error.
    return [] as unknown as T;
  }
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${await res.text().catch(() => res.statusText)}`);
  }
  return res.json() as Promise<T>;
}

function qs(params: object | undefined): string {
  if (!params) return "";
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== "");
  if (entries.length === 0) return "";
  return `?${new URLSearchParams(entries as [string, string][]).toString()}`;
}

export const httpClient: ApiClient = {
  getSessions: () => http("/sessions"),

  getPrograms: (params) => http(`/programs${qs(params)}`),
  getProgram: (code) => http(`/programs/${encodeURIComponent(code)}`),
  getProgramRequirements: (code) => http(`/programs/${encodeURIComponent(code)}/requirements`),
  reparseProgramRequirements: (code) =>
    http(`/programs/${encodeURIComponent(code)}/requirements/reparse`, { method: "POST" }),

  getCourses: (params) => http(`/courses${qs(params)}`),
  getCourse: (code) => http(`/courses/${encodeURIComponent(code)}`),

  getMyRecord: () => http("/me"),
  getMyRequirementProgress: () => http("/me/requirements"),
  getMyDegreeAudit: () => http("/me/degree-audit"),
  getMyBreadth: () => http("/me/breadth"),
  getMySummary: () => http("/me/summary"),
  getMyAlerts: () => http("/me/alerts"),

  createShareLink: () => http("/share", { method: "POST" }),
  getShared: (token) => http(`/share/${encodeURIComponent(token)}`),
};

/** The client screens should use. Real backend when VITE_API_BASE is set, mock adapter otherwise. */
export const api: ApiClient = API_BASE ? httpClient : mockClient;

export const isMockApi = !API_BASE;
