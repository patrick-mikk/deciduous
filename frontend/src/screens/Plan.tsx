import * as React from "react";
import { useNavigate } from "react-router-dom";

import { api } from "@/api";
import type { Course, PlanCourse, PlanValidationIssue, Program, SessionCode, StudentRecord } from "@/api";
import { creditFromCode, shortenProgram, countsTowardPhrase, remainingRequirementMatches } from "@/api";
import {
  AutoPlanPanel,
  Button,
  Callout,
  Combobox,
  CourseRail,
  Dialog,
  Drawer,
  EmptyState,
  PageHeader,
  PlanBoard,
  Select,
  Skeleton,
  Spinner,
  Switch,
  Toast,
  ValidationSummary,
} from "@/ds";

/**
 * Plan board — `/plan` (design/screens/04-plan-and-timetable.md "Plan board").
 *
 * CourseRail (draggable, searchable) + year-grouped seasonal TermColumns
 * (native HTML5 drag-drop, optimistic add/move + client-side validation),
 * PlanCourseCard badges (prereq/exclusion/not-offered) + requirement/breadth
 * tags, a ValidationSummary, and an AutoPlanPanel drawer that proposes a
 * diff of adds against the student's still-open requirement groups.
 *
 * Note on `GET/PUT /api/plan` + `POST /api/plan/validate` + `POST
 * /api/plan/autoplan` (design/06-data-model-and-api.md line 82): those
 * endpoints don't exist on `ApiClient` yet (see frontend/src/api/client.ts —
 * only the reference-data/programs/courses/me/share surface is implemented).
 * This screen still binds to real data for everything that *does* exist
 * (courses, the student record, program requirements, sessions) and keeps
 * the plan itself — term placement, locks, validation — as client-side
 * state autosaved to localStorage, so the board is fully usable today and a
 * one-line swap to real `GET/PUT /api/plan` calls once the backend ships.
 */

// ---------------------------------------------------------------------------
// Local view-model types
// ---------------------------------------------------------------------------

interface PlanCardVM {
  code: string;
  title: string;
  credit: number;
  status: "planned" | "completed";
  issues: string[]; // "prereq" | "exclusion" | "not-offered"
  satisfies: { breadth?: string; label: string }[]; // breadth chips only
  countsToward?: string; // plain-language "Counts toward X" line
  draggable: boolean;
  locked: boolean;
}

interface PlanTermVM {
  id: SessionCode;
  season: "Fall" | "Winter";
  year: string; // grouping label for PlanBoard, e.g. "2026–27"
  calendarYear: number;
  credits: number;
  courses: PlanCardVM[];
}

interface ToastItem {
  id: number;
  tone: "info" | "success" | "warning" | "danger";
  message: string;
}

const PLAN_STORAGE_KEY = "deciduous:plan:v1";
const YEAR_OPTIONS = [2, 3, 4, 5];
// How many ranked remaining-requirement courses the rail fetches for its
// proactive default view (each is one live getCourse call).
const RAIL_SUGGEST_LIMIT = 40;

// ---------------------------------------------------------------------------
// Pure helpers
// ---------------------------------------------------------------------------

/** Y-course transcript sessions are stored "20239-20241" — the plan only tracks one term id. */
function normalizeTerm(term: string): string {
  return term.split("-")[0];
}

function seasonOf(termId: string): "Fall" | "Winter" {
  return termId.endsWith("9") ? "Fall" : "Winter";
}

/** Course codes mentioned in free-text prerequisites/exclusions, e.g. "POL208H1". */
function extractCodes(text: string): string[] {
  return Array.from(new Set(text.match(/[A-Z]{3}\d{3}[HY]\d/g) ?? []));
}

/** "4.0 credits" -> 4. Null when the text has no bare credit threshold. */
function extractCreditThreshold(text: string): number | null {
  const m = text.match(/(\d+(?:\.\d+)?)\s*credits?/i);
  return m ? Number(m[1]) : null;
}

/** "Society and Its Institutions (3)" -> "BR3", for the design system's breadth-coloured Chips. */
function mapBreadthKeys(breadth: string[]): string[] {
  const keys: string[] = [];
  for (const b of breadth) {
    const m = b.match(/\((\d)\)/);
    if (m) keys.push(`BR${m[1]}`);
  }
  return keys;
}

function anchorFallYear(sessions: SessionCode[]): number {
  const fallYears = sessions.filter((s) => s.endsWith("9")).map((s) => Number(s.slice(0, 4)));
  if (fallYears.length > 0) return Math.min(...fallYears);
  return new Date().getFullYear();
}

function loadStoredPlan(): PlanCourse[] | null {
  try {
    const raw = window.localStorage.getItem(PLAN_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as PlanCourse[]) : null;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Screen
// ---------------------------------------------------------------------------

export default function Plan() {
  const navigate = useNavigate();

  // ---- Core data (real API, mock fallback baked into src/api/client.ts) ----
  const [record, setRecord] = React.useState<StudentRecord | null>(null);
  const [sessions, setSessions] = React.useState<SessionCode[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [loadError, setLoadError] = React.useState<string | null>(null);
  const [reloadKey, setReloadKey] = React.useState(0);

  const [programDetails, setProgramDetails] = React.useState<Program[]>([]);
  const [courseDetails, setCourseDetails] = React.useState<Map<string, Course | null>>(new Map());

  // ---- The plan itself (client-local until /api/plan ships, see header note) ----
  const [planCourses, setPlanCourses] = React.useState<PlanCourse[]>([]);
  const [planInitialized, setPlanInitialized] = React.useState(false);
  const planSeededRef = React.useRef(false);

  // ---- Board controls ----
  const [yearsAhead, setYearsAhead] = React.useState(3);

  // ---- CourseRail ----
  const [railQuery, setRailQuery] = React.useState("");
  const [debouncedRailQuery, setDebouncedRailQuery] = React.useState("");
  // Default ON: the app already knows the student's programs and gaps, so the
  // rail leads with courses that fill a remaining requirement. Unchecking is
  // the opt-out to browse the full catalog.
  const [onlyRemaining, setOnlyRemaining] = React.useState(true);
  const [railResults, setRailResults] = React.useState<Course[]>([]);
  const [railLoading, setRailLoading] = React.useState(true);
  const [railError, setRailError] = React.useState<string | null>(null);

  // ---- Server-authoritative plan validation (`POST /api/plan/validate`) ----
  // This is the only source that can know about plan-wide warnings the
  // client can't compute itself (e.g. "requirements_unparsed" for a program
  // whose requirement groups never parsed) -- see issue tracker note on
  // Plan validation below. Per-card prereq/exclusion/not-offered badges stay
  // driven by the local `computeIssues` approximation (still useful as
  // instant feedback while dragging); this state instead drives the
  // page-level "N issues" pill and the ValidationSummary panel.
  type ValidationStatus = "idle" | "loading" | "success" | "error";
  const [validationStatus, setValidationStatus] = React.useState<ValidationStatus>("idle");
  const [validationIssues, setValidationIssues] = React.useState<PlanValidationIssue[]>([]);
  const [validationError, setValidationError] = React.useState<string | null>(null);
  const [validationRetryKey, setValidationRetryKey] = React.useState(0);

  // ---- Add-course dialog (keyboard/click alternative to dragging) ----
  const [addDialogTermId, setAddDialogTermId] = React.useState<string | null>(null);
  const [addDialogChoice, setAddDialogChoice] = React.useState<string | null>(null);
  // The dialog runs its own server-backed search rather than reusing the
  // rail's first page of results: `/api/courses` is paged, so client-side
  // filtering a single page can neither offer a useful default (it would dump
  // the alphabetically-first courses) nor find a course past page one. This
  // query is fed from the Combobox's own text input via `onQueryChange`.
  const [addDialogQuery, setAddDialogQuery] = React.useState("");
  const [addDialogResults, setAddDialogResults] = React.useState<Course[]>([]);
  const [addDialogLoading, setAddDialogLoading] = React.useState(false);

  // ---- Course options dialog (move / lock / remove — also the drag alternative) ----
  const [activeCourseCode, setActiveCourseCode] = React.useState<string | null>(null);

  // ---- Auto-plan drawer ----
  const [autoPlanOpen, setAutoPlanOpen] = React.useState(false);
  const [autoPlanGenerating, setAutoPlanGenerating] = React.useState(false);
  const [autoPlanCreditCap, setAutoPlanCreditCap] = React.useState(2.5);
  const [autoPlanDiff, setAutoPlanDiff] = React.useState<{ type: "add" | "move"; code: string; to: string }[] | null>(
    null,
  );
  const [autoPlanDraft, setAutoPlanDraft] = React.useState<PlanCourse[] | null>(null);

  // ---- Toasts ----
  const [toasts, setToasts] = React.useState<ToastItem[]>([]);
  const toastIdRef = React.useRef(0);
  const validationRef = React.useRef<HTMLDivElement | null>(null);

  const pushToast = React.useCallback((tone: ToastItem["tone"], message: string) => {
    const id = ++toastIdRef.current;
    setToasts((prev) => [...prev, { id, tone, message }]);
    window.setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4500);
  }, []);

  // ---- Load the student record + reference sessions ----
  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    Promise.all([api.getMyRecord(), api.getSessions().catch(() => [] as SessionCode[])])
      .then(([rec, sess]) => {
        if (cancelled) return;
        setRecord(rec);
        setSessions(sess);
        setLoading(false);
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setLoadError(e instanceof Error ? e.message : "Couldn't load your plan.");
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  // ---- Seed the plan once (stored plan wins; otherwise the "planned" transcript rows) ----
  React.useEffect(() => {
    if (!record || planSeededRef.current) return;
    planSeededRef.current = true;
    const stored = loadStoredPlan();
    if (stored) {
      setPlanCourses(stored);
    } else {
      setPlanCourses(
        record.transcript
          .filter((t) => t.status === "planned")
          .map((t) => ({ code: t.code, term: normalizeTerm(t.session) })),
      );
    }
    setPlanInitialized(true);
  }, [record]);

  // ---- Autosave (stands in for `PUT /api/plan`) ----
  React.useEffect(() => {
    if (!planInitialized) return;
    try {
      window.localStorage.setItem(PLAN_STORAGE_KEY, JSON.stringify(planCourses));
    } catch {
      // Best-effort only — private browsing / quota errors shouldn't break the board.
    }
  }, [planCourses, planInitialized]);

  // ---- Enrolled programs' full requirement groups (for satisfies tags + auto-plan gaps) ----
  React.useEffect(() => {
    if (!record || record.programs.length === 0) return;
    let cancelled = false;
    Promise.all(record.programs.map((p) => api.getProgram(p.code).catch(() => null)))
      .then((results) => {
        if (cancelled) return;
        setProgramDetails(results.filter((p): p is Program => p != null));
      })
      .catch(() => {
        // Non-fatal: satisfies tags / auto-plan gaps just come back empty.
      });
    return () => {
      cancelled = true;
    };
  }, [record]);

  // ---- Debounced course-rail search (design/07: "debounce typeahead 200ms") ----
  React.useEffect(() => {
    const t = window.setTimeout(() => setDebouncedRailQuery(railQuery.trim()), 200);
    return () => window.clearTimeout(t);
  }, [railQuery]);

  const [railRetryKey, setRailRetryKey] = React.useState(0);
  const railRequestId = React.useRef(0);
  React.useEffect(() => {
    const id = ++railRequestId.current;
    setRailLoading(true);
    setRailError(null);
    api
      .getCourses(debouncedRailQuery ? { q: debouncedRailQuery } : undefined)
      .then((cs) => {
        if (railRequestId.current !== id) return;
        setRailResults(cs);
        setRailLoading(false);
      })
      .catch((e: unknown) => {
        if (railRequestId.current !== id) return;
        setRailError(e instanceof Error ? e.message : "Couldn't search courses.");
        setRailLoading(false);
      });
  }, [debouncedRailQuery, railRetryKey]);

  // ---- Add-dialog debounced server search ----
  // Only fires while the dialog is open and there's a query; an empty query
  // stays in the Combobox's "type to search" state, so we never fetch (or
  // show) the arbitrary first-page dump.
  const addDialogRequestId = React.useRef(0);
  React.useEffect(() => {
    const q = addDialogQuery.trim();
    if (addDialogTermId == null) {
      setAddDialogResults([]);
      setAddDialogLoading(false);
      return;
    }
    if (!q) {
      // Selecting an option resets the Combobox's own query to empty. Keep the
      // last results so the chosen course's label still resolves in the
      // trigger; the dropdown itself stays in the "type to search" state.
      setAddDialogLoading(false);
      return;
    }
    const id = ++addDialogRequestId.current;
    setAddDialogLoading(true);
    const t = window.setTimeout(() => {
      api
        .getCourses({ q })
        .then((cs) => {
          if (addDialogRequestId.current !== id) return;
          setAddDialogResults(cs);
          setAddDialogLoading(false);
        })
        .catch(() => {
          if (addDialogRequestId.current !== id) return;
          setAddDialogResults([]);
          setAddDialogLoading(false);
        });
    }, 200);
    return () => window.clearTimeout(t);
  }, [addDialogQuery, addDialogTermId]);

  // ---- Debounced server validation, re-run whenever the plan changes ----
  const [debouncedPlanForValidation, setDebouncedPlanForValidation] = React.useState<PlanCourse[]>([]);
  React.useEffect(() => {
    const t = window.setTimeout(() => setDebouncedPlanForValidation(planCourses), 300);
    return () => window.clearTimeout(t);
  }, [planCourses]);

  const validationRequestId = React.useRef(0);
  React.useEffect(() => {
    if (!planInitialized) return;
    const id = ++validationRequestId.current;
    setValidationStatus("loading");
    setValidationError(null);
    const items = debouncedPlanForValidation.map((p) => ({ courseCode: p.code, termSession: p.term }));
    api
      .validatePlan(items)
      .then((res) => {
        if (validationRequestId.current !== id) return;
        setValidationIssues(res.issues);
        setValidationStatus("success");
      })
      .catch((e: unknown) => {
        if (validationRequestId.current !== id) return;
        setValidationError(e instanceof Error ? e.message : "Couldn't validate your plan.");
        setValidationStatus("error");
      });
  }, [debouncedPlanForValidation, planInitialized, validationRetryKey]);

  const validationErrorCount = React.useMemo(
    () => validationIssues.filter((i) => i.severity === "error").length,
    [validationIssues],
  );
  const validationWarningCount = validationIssues.length - validationErrorCount;

  // ---- Still-open requirement-group course codes, across enrolled programs ----
  const remainingCodes = React.useMemo(() => {
    const out = new Set<string>();
    if (!record) return out;
    const already = new Set<string>([
      ...record.transcript.filter((t) => t.status === "completed").map((t) => t.code),
      ...planCourses.map((p) => p.code),
    ]);
    for (const prog of programDetails) {
      const progress = record.requirementProgress[prog.code] ?? [];
      for (const group of prog.completionRequirements) {
        const groupProgress = progress.find((p) => p.label === group.heading);
        const stillNeeded = groupProgress ? groupProgress.earned < groupProgress.required : true;
        if (!stillNeeded) continue;
        for (const code of group.courseCodes) {
          if (!already.has(code)) out.add(code);
        }
      }
    }
    return out;
  }, [record, programDetails, planCourses]);

  // Ranked remaining-requirement courses (multi-program first) -- the rail's
  // proactive default when nothing is typed. Excludes what's completed,
  // in progress, or already on the plan.
  const remainingMatches = React.useMemo(() => {
    if (!record) return [];
    const taken = new Set<string>([
      ...record.transcript.filter((t) => t.status === "completed" || t.status === "in_progress").map((t) => t.code),
      ...planCourses.map((p) => p.code),
    ]);
    return remainingRequirementMatches(programDetails, record.requirementProgress, taken);
  }, [record, programDetails, planCourses]);

  // The top-ranked suggestions, in rank order, built from the course details
  // that are already fetched below (no extra network call). Drives both the
  // rail's default view and the "Add a course" dialog's default options.
  const suggestionCodes = React.useMemo(
    () => remainingMatches.slice(0, RAIL_SUGGEST_LIMIT).map((m) => m.code),
    [remainingMatches],
  );
  const suggestionResults = React.useMemo(
    () => suggestionCodes.map((code) => courseDetails.get(code)).filter((c): c is Course => Boolean(c)),
    [suggestionCodes, courseDetails],
  );
  // Still resolving while any top code hasn't come back yet (present in the map
  // means fetched, even if it resolved to null).
  const suggestionLoading = suggestionCodes.length > 0 && suggestionCodes.some((code) => !courseDetails.has(code));

  // ---- On-demand course detail fetch for every code the plan/auto-plan needs to reason about ----
  const neededCodes = React.useMemo(() => {
    const s = new Set<string>(planCourses.map((p) => p.code));
    remainingCodes.forEach((c) => s.add(c));
    return s;
  }, [planCourses, remainingCodes]);

  const fetchedCodesRef = React.useRef<Set<string>>(new Set());
  React.useEffect(() => {
    const missing = Array.from(neededCodes).filter((c) => !fetchedCodesRef.current.has(c));
    if (missing.length === 0) return;
    // Mark a code fetched only once its request resolves (not up front): when
    // `neededCodes` recomputes as record/programDetails load, this effect
    // re-runs and its cleanup cancels the prior in-flight batch. If we marked
    // up front, those cancelled codes would be skipped forever and their
    // titles would never populate (the card would show the code twice).
    let active = true;
    Promise.all(
      missing.map((code) =>
        api
          .getCourse(code)
          .then((c) => [code, c] as const)
          .catch(() => [code, null] as const),
      ),
    ).then((pairs) => {
      if (!active) return;
      pairs.forEach(([code]) => fetchedCodesRef.current.add(code));
      setCourseDetails((prev) => {
        const next = new Map(prev);
        for (const [code, c] of pairs) next.set(code, c);
        return next;
      });
    });
    return () => {
      active = false;
    };
  }, [neededCodes]);

  // ---- Validation + satisfies tags (client-side approximation of `POST /api/plan/validate`) ----
  const computeIssues = React.useCallback(
    (code: string, course: Course, termId: string): string[] => {
      const issues: string[] = [];
      const season = seasonOf(termId);
      if (course.sectionCode === "F" && season !== "Fall") issues.push("not-offered");
      if (course.sectionCode === "S" && season !== "Winter") issues.push("not-offered");

      const priorCodes = new Set<string>([
        ...(record?.transcript
          .filter((t) => t.status === "completed" || t.status === "in_progress")
          .map((t) => t.code) ?? []),
        ...planCourses
          .filter((p) => p.code !== code && Number(normalizeTerm(p.term)) < Number(termId))
          .map((p) => p.code),
      ]);
      const priorCredits =
        (record?.transcript
          .filter((t) => t.status === "completed" || t.status === "in_progress")
          .reduce((s, t) => s + t.credits, 0) ?? 0) +
        planCourses
          .filter((p) => p.code !== code && Number(normalizeTerm(p.term)) < Number(termId))
          .reduce((s, p) => s + (courseDetails.get(p.code)?.credit ?? creditFromCode(p.code)), 0);

      const prereqCodes = extractCodes(course.prerequisites);
      const threshold = extractCreditThreshold(course.prerequisites);
      const hasCheckablePrereq = prereqCodes.length > 0 || threshold != null;
      const codesSatisfied = prereqCodes.length > 0 && prereqCodes.some((c) => priorCodes.has(c));
      const creditsSatisfied = threshold != null && priorCredits >= threshold;
      if (hasCheckablePrereq && !codesSatisfied && !creditsSatisfied) issues.push("prereq");

      const exclusionCodes = extractCodes(course.exclusions);
      const elsewhere = new Set<string>([
        ...(record?.transcript.map((t) => t.code) ?? []),
        ...planCourses.filter((p) => p.code !== code).map((p) => p.code),
      ]);
      if (exclusionCodes.some((c) => elsewhere.has(c))) issues.push("exclusion");

      return issues;
    },
    [record, planCourses, courseDetails],
  );

  // Breadth chips only. The requirement-group heading (raw jargon like
  // "Program Course Requirements") is deliberately no longer surfaced as a
  // chip -- it's replaced by the plain-language "Counts toward ..." line below.
  const computeSatisfies = React.useCallback(
    (_code: string, course: Course | null): { breadth?: string; label: string }[] => {
      if (!course) return [];
      return mapBreadthKeys(course.breadth).map((key) => ({ breadth: key, label: key }));
    },
    [],
  );

  // Which of the student's enrolled programs a course actually counts toward,
  // as a plain-language phrase ("Economics and Public Policy"). Replaces the
  // requirement-group jargon a student wouldn't recognize.
  const computeCountsToward = React.useCallback(
    (code: string): string | undefined => {
      const names: string[] = [];
      for (const prog of programDetails) {
        const inProgram = prog.completionRequirements.some((group) => group.courseCodes.includes(code));
        if (inProgram) names.push(shortenProgram(prog.title));
      }
      return countsTowardPhrase(names);
    },
    [programDetails],
  );

  // ---- Year-grouped seasonal terms, built from the plan + validation above ----
  const terms = React.useMemo<PlanTermVM[]>(() => {
    const startYear = anchorFallYear(sessions);
    const list: PlanTermVM[] = [];
    for (let i = 0; i < yearsAhead; i++) {
      const fallYear = startYear + i;
      const winterYear = fallYear + 1;
      for (const [id, season, calendarYear] of [
        [`${fallYear}9`, "Fall", fallYear],
        [`${winterYear}1`, "Winter", winterYear],
      ] as const) {
        const yearLabel = `${fallYear}–${String(winterYear).slice(2)}`;
        const courses: PlanCardVM[] = planCourses
          .filter((pc) => normalizeTerm(pc.term) === id)
          .map((pc) => {
            const course = courseDetails.get(pc.code) ?? null;
            const completed =
              record?.transcript.some((t) => t.code === pc.code && t.status === "completed") ?? false;
            return {
              code: pc.code,
              title: course?.title ?? pc.code,
              credit: course?.credit ?? creditFromCode(pc.code),
              status: completed ? "completed" : "planned",
              issues: course ? computeIssues(pc.code, course, id) : [],
              satisfies: computeSatisfies(pc.code, course),
              countsToward: computeCountsToward(pc.code),
              draggable: !pc.locked,
              locked: !!pc.locked,
            };
          });
        list.push({
          id,
          season,
          year: yearLabel,
          calendarYear,
          credits: courses.reduce((s, c) => s + c.credit, 0),
          courses,
        });
      }
    }
    return list;
  }, [sessions, yearsAhead, planCourses, courseDetails, record, computeIssues, computeSatisfies]);

  function termLabel(termId: string): string {
    const t = terms.find((x) => x.id === termId);
    return t ? `${t.season} ${t.calendarYear}` : termId;
  }

  // ---- Plan mutations ----
  function addCourseToTerm(code: string, termId: string) {
    setPlanCourses((prev) => {
      if (prev.some((p) => p.code === code)) {
        pushToast("warning", `${code} is already on your plan.`);
        return prev;
      }
      pushToast("success", `Added ${code} to ${termLabel(termId)}.`);
      return [...prev, { code, term: termId }];
    });
  }

  function moveCourse(code: string, toTermId: string) {
    setPlanCourses((prev) => {
      const existing = prev.find((p) => p.code === code);
      if (!existing) return prev;
      if (existing.locked) {
        pushToast("warning", `${code} is locked. Unlock it before moving.`);
        return prev;
      }
      if (existing.term === toTermId) return prev;
      pushToast("success", `Moved ${code} to ${termLabel(toTermId)}.`);
      return prev.map((p) => (p.code === code ? { ...p, term: toTermId } : p));
    });
  }

  function handleDropCourse(termId: string, code: string) {
    if (!code) return;
    if (planCourses.some((p) => p.code === code)) moveCourse(code, termId);
    else addCourseToTerm(code, termId);
  }

  function handleRemoveCourse(_termId: string, code: string) {
    const existing = planCourses.find((p) => p.code === code);
    if (existing?.locked) {
      pushToast("warning", `${code} is locked. Unlock it before removing.`);
      return;
    }
    setPlanCourses((prev) => prev.filter((p) => p.code !== code));
    pushToast("info", `Removed ${code} from your plan.`);
  }

  function toggleLock(code: string, locked: boolean) {
    setPlanCourses((prev) => prev.map((p) => (p.code === code ? { ...p, locked } : p)));
  }

  // ---- Auto-plan (client-side approximation of `POST /api/plan/autoplan`) ----
  async function handleAutoPlanGenerate() {
    setAutoPlanGenerating(true);
    await new Promise((resolve) => window.setTimeout(resolve, 700));

    const draft: PlanCourse[] = [...planCourses];
    const diff: { type: "add" | "move"; code: string; to: string }[] = [];
    const completedOrProgress = new Set(
      record?.transcript.filter((t) => t.status === "completed" || t.status === "in_progress").map((t) => t.code) ??
        [],
    );
    const baseCredits =
      record?.transcript
        .filter((t) => t.status === "completed" || t.status === "in_progress")
        .reduce((s, t) => s + t.credits, 0) ?? 0;

    for (const code of remainingCodes) {
      if (draft.some((d) => d.code === code)) continue;
      const course = courseDetails.get(code);
      if (!course) continue;

      for (const term of terms) {
        if (course.sectionCode === "F" && term.season !== "Fall") continue;
        if (course.sectionCode === "S" && term.season !== "Winter") continue;

        const usedInTerm = draft
          .filter((d) => normalizeTerm(d.term) === term.id)
          .reduce((s, d) => s + (courseDetails.get(d.code)?.credit ?? creditFromCode(d.code)), 0);
        if (usedInTerm + course.credit > autoPlanCreditCap) continue;

        const priorCodes = new Set<string>([
          ...completedOrProgress,
          ...draft.filter((d) => Number(normalizeTerm(d.term)) < Number(term.id)).map((d) => d.code),
        ]);
        const priorCredits =
          baseCredits +
          draft
            .filter((d) => Number(normalizeTerm(d.term)) < Number(term.id))
            .reduce((s, d) => s + (courseDetails.get(d.code)?.credit ?? creditFromCode(d.code)), 0);

        const prereqCodes = extractCodes(course.prerequisites);
        const threshold = extractCreditThreshold(course.prerequisites);
        const hasCheckablePrereq = prereqCodes.length > 0 || threshold != null;
        const codesSatisfied = prereqCodes.length > 0 && prereqCodes.some((c) => priorCodes.has(c));
        const creditsSatisfied = threshold != null && priorCredits >= threshold;
        if (hasCheckablePrereq && !codesSatisfied && !creditsSatisfied) continue;

        draft.push({ code, term: term.id });
        diff.push({ type: "add", code, to: `${term.season} ${term.calendarYear}` });
        break;
      }
    }

    setAutoPlanGenerating(false);
    setAutoPlanDraft(draft);
    setAutoPlanDiff(diff);
    if (diff.length === 0) pushToast("info", "No open requirement gaps fit into the current planning window.");
  }

  function handleAutoPlanApply() {
    if (autoPlanDraft) {
      setPlanCourses(autoPlanDraft);
      pushToast("success", `Auto-plan added ${autoPlanDiff?.length ?? 0} course(s) to your plan.`);
    }
    setAutoPlanDiff(null);
    setAutoPlanDraft(null);
    setAutoPlanOpen(false);
  }

  function handleAutoPlanCancel() {
    setAutoPlanDiff(null);
    setAutoPlanDraft(null);
  }

  function handleValidateClick() {
    if (validationStatus === "loading") return;
    if (validationStatus === "error") {
      pushToast("danger", validationError ?? "We couldn't check your plan just now.");
    } else if (validationIssues.length === 0) {
      pushToast("success", "Your plan looks good.");
    } else if (validationErrorCount === 0) {
      pushToast(
        "warning",
        validationWarningCount === 1
          ? "Your plan works. There's one thing worth a look below."
          : `Your plan works. There are ${validationWarningCount} things worth a look below.`,
      );
    } else {
      pushToast(
        "warning",
        validationErrorCount === 1
          ? "There's one thing to fix. See the details below."
          : `There are ${validationErrorCount} things to fix. See the details below.`,
      );
    }
    validationRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // ---- Course-rail view model ----
  const railCourseStatus = React.useCallback(
    (code: string): "planned" | "completed" | "available" => {
      if (planCourses.some((p) => p.code === code)) return "planned";
      if (record?.transcript.some((t) => t.code === code && t.status === "completed")) return "completed";
      return "available";
    },
    [planCourses, record],
  );

  // Issue 3: when no program's requirements have parsed (or none are
  // enrolled), `remainingCodes` is empty -- filtering by it then would
  // silently show "no matching courses" for every search, indistinguishable
  // from a genuine zero-match search. Disable the checkbox instead, with a
  // hint explaining why, rather than let it lie about the plan's state.
  const onlyRemainingDisabled = remainingCodes.size === 0;
  const onlyRemainingHint = !onlyRemainingDisabled
    ? undefined
    : !record || record.programs.length === 0
      ? "Add a program from Requirements to enable this filter."
      : "Load your programs' requirements first. No requirement data is available yet.";

  // With nothing typed and the filter on, the rail leads with the ranked
  // remaining-requirement suggestions (fetched by code). Typing searches the
  // full catalog; with the filter on, that search is narrowed to remaining
  // courses. Unchecking browses the whole catalog.
  const suggestMode = onlyRemaining && !onlyRemainingDisabled && !debouncedRailQuery && remainingMatches.length > 0;

  const railCourses = React.useMemo(() => {
    let list: Course[];
    if (suggestMode) list = suggestionResults;
    else if (onlyRemaining && !onlyRemainingDisabled && debouncedRailQuery)
      list = railResults.filter((c) => remainingCodes.has(c.code));
    else list = railResults;
    return list.map((c) => ({
      code: c.code,
      title: c.title,
      credit: c.credit,
      breadth: mapBreadthKeys(c.breadth),
      countsToward: computeCountsToward(c.code),
      status: railCourseStatus(c.code),
    }));
  }, [suggestMode, suggestionResults, railResults, onlyRemaining, onlyRemainingDisabled, debouncedRailQuery, remainingCodes, railCourseStatus, computeCountsToward]);

  const railBusy = suggestMode ? suggestionLoading : railLoading;

  // The rail's empty/helper copy should say *why* the list looks the way it
  // does -- suggestions vs a narrowed search vs browsing the whole catalog.
  const railEmptyMessage = debouncedRailQuery
    ? `No courses match "${debouncedRailQuery}".`
    : suggestMode
      ? "Nothing left that fills a remaining requirement. Uncheck to browse the catalog."
      : "No courses available.";
  const railHelperText = debouncedRailQuery
    ? undefined
    : suggestMode
      ? "Courses that fill a remaining requirement, best picks first. Type to search everything."
      : "Browsing the catalog. Type to search.";
  const railCountLabel = railBusy
    ? undefined
    : `${railCourses.length} course${railCourses.length === 1 ? "" : "s"}`;

  // The dialog leads with the same ranked suggestions as the rail; typing
  // switches to a full-catalog search (driven by the Combobox query).
  const addDialogSuggesting = !addDialogQuery.trim();
  const addDialogOptions = React.useMemo(() => {
    const source = addDialogSuggesting ? suggestionResults : addDialogResults;
    const list = source.filter((c) => !planCourses.some((p) => p.code === c.code));
    // Keep the current pick resolvable even after the Combobox clears its query
    // (e.g. you searched, picked a non-suggestion, and the options reverted).
    if (addDialogChoice && !list.some((c) => c.code === addDialogChoice)) {
      const chosen =
        suggestionResults.find((c) => c.code === addDialogChoice) ??
        addDialogResults.find((c) => c.code === addDialogChoice);
      if (chosen) list.unshift(chosen);
    }
    return list.map((c) => {
      const ct = addDialogSuggesting ? computeCountsToward(c.code) : undefined;
      return {
        value: c.code,
        label: ct ? `${c.code} · ${c.title} (counts toward ${ct})` : `${c.code} · ${c.title}`,
      };
    });
  }, [addDialogSuggesting, suggestionResults, addDialogResults, planCourses, computeCountsToward, addDialogChoice]);

  const activeCourse = activeCourseCode ? planCourses.find((p) => p.code === activeCourseCode) ?? null : null;
  const activeCourseDetail = activeCourseCode ? (courseDetails.get(activeCourseCode) ?? null) : null;

  // ---------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------

  return (
    <div>
      <PageHeader
        title="Your plan"
        subtitle="Drag a course onto a term, or search below to add one."
        actions={
          <div style={{ display: "flex", gap: 10, alignItems: "flex-end", flexWrap: "wrap" }}>
            <div style={{ width: 128 }}>
              <Select
                label="Show"
                value={String(yearsAhead)}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setYearsAhead(Number(e.target.value))}
                options={YEAR_OPTIONS.map((n) => ({ value: String(n), label: `${n} years` }))}
              />
            </div>
            <Button
              variant="secondary"
              icon={validationStatus === "loading" ? "loader-circle" : "check-circle"}
              disabled={validationStatus === "loading"}
              onClick={validationStatus === "error" ? () => setValidationRetryKey((k) => k + 1) : handleValidateClick}
            >
              {validationStatus === "loading" ? "Checking…" : "Check my plan"}
            </Button>
            <Button variant="primary" icon="sparkles" onClick={() => setAutoPlanOpen(true)}>
              Auto-plan
            </Button>
          </div>
        }
      />

      {loadError && (
        <div style={{ marginBottom: 20 }}>
          <Callout
            tone="danger"
            title="Couldn't load your plan"
            action={
              <Button variant="secondary" size="sm" onClick={() => setReloadKey((k) => k + 1)}>
                Retry
              </Button>
            }
          >
            {loadError}
          </Callout>
        </div>
      )}

      {loading ? (
        <PlanBoardSkeleton />
      ) : !record ? null : record.programs.length === 0 && planCourses.length === 0 ? (
        <EmptyState
          icon="git-branch"
          title="Nothing planned yet"
          description="Add a program from Requirements, then search for courses and drag them onto a term to start building your plan."
          action={
            <Button variant="primary" onClick={() => navigate("/programs")}>
              Browse programs
            </Button>
          }
        />
      ) : (
        <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
          {railError ? (
            <div style={{ width: 260, flexShrink: 0 }}>
              <Callout
                tone="danger"
                title="Couldn't search courses"
                action={
                  <Button variant="secondary" size="sm" onClick={() => setRailRetryKey((k) => k + 1)}>
                    Retry
                  </Button>
                }
              >
                {railError}
              </Callout>
            </div>
          ) : (
            <CourseRail
              courses={railCourses}
              query={railQuery}
              onQuery={setRailQuery}
              onlyRemaining={onlyRemaining}
              onToggleRemaining={setOnlyRemaining}
              onDragCourse={() => {}}
              loading={railBusy}
              onlyRemainingDisabled={onlyRemainingDisabled}
              onlyRemainingHint={onlyRemainingHint}
              emptyMessage={railEmptyMessage}
              helperText={railHelperText}
              countLabel={railCountLabel}
            />
          )}

          <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: 16 }}>
            <div ref={validationRef}>
              {validationStatus === "error" ? (
                <Callout
                  tone="danger"
                  title="Couldn't validate your plan"
                  action={
                    <Button variant="secondary" size="sm" onClick={() => setValidationRetryKey((k) => k + 1)}>
                      Retry
                    </Button>
                  }
                >
                  {validationError}
                </Callout>
              ) : validationStatus === "loading" && validationIssues.length === 0 ? (
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    color: "var(--text-secondary)",
                    fontSize: "var(--text-body-sm)",
                  }}
                >
                  <Spinner size={16} />
                  Validating your plan…
                </div>
              ) : (
                <ValidationSummary
                  issues={validationIssues}
                  onJump={(iss: PlanValidationIssue) => iss.code && navigate(`/courses/${iss.code}`)}
                />
              )}
            </div>

            <div style={{ fontSize: "var(--text-body-sm)", color: "var(--text-tertiary)" }}>
              {planCourses.length} course{planCourses.length === 1 ? "" : "s"} planned across {terms.length} terms
              shown.
            </div>

            <PlanBoard
              terms={terms}
              onDropCourse={(termId: string, code: string) => handleDropCourse(termId, code)}
              onAddCourse={(termId: string) => {
                setAddDialogTermId(termId);
                setAddDialogChoice(null);
              }}
              onRemoveCourse={handleRemoveCourse}
              onCourseClick={(c: PlanCardVM) => setActiveCourseCode(c.code)}
            />
          </div>
        </div>
      )}

      {/* ---- Add course (keyboard/click alternative to dragging) ---- */}
      <Dialog
        open={addDialogTermId != null}
        title={addDialogTermId ? `Add a course to ${termLabel(addDialogTermId)}` : "Add a course"}
        onClose={() => {
          setAddDialogTermId(null);
          setAddDialogQuery("");
        }}
        footer={
          <>
            <Button
              variant="secondary"
              onClick={() => {
                setAddDialogTermId(null);
                setAddDialogQuery("");
              }}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              disabled={!addDialogChoice}
              onClick={() => {
                if (addDialogTermId && addDialogChoice) addCourseToTerm(addDialogChoice, addDialogTermId);
                setAddDialogTermId(null);
                setAddDialogQuery("");
              }}
            >
              Add
            </Button>
          </>
        }
      >
        <Combobox
          label="Course"
          placeholder="Pick a suggestion, or search all courses"
          options={addDialogOptions}
          value={addDialogChoice}
          onChange={(v: string | null) => setAddDialogChoice(v)}
          onQueryChange={(q: string) => setAddDialogQuery(q)}
          loading={addDialogSuggesting ? suggestionLoading : addDialogLoading}
          clearable
        />
      </Dialog>

      {/* ---- Course options: move / lock / remove (also the drag-and-drop keyboard alternative) ---- */}
      <Dialog
        open={activeCourseCode != null}
        title={activeCourseCode ?? ""}
        onClose={() => setActiveCourseCode(null)}
        footer={
          <>
            <Button
              variant="danger"
              onClick={() => {
                if (activeCourseCode) handleRemoveCourse(activeCourse?.term ?? "", activeCourseCode);
                setActiveCourseCode(null);
              }}
            >
              Remove
            </Button>
            <Button variant="secondary" onClick={() => setActiveCourseCode(null)}>
              Close
            </Button>
          </>
        }
      >
        {activeCourseCode && activeCourse && (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {activeCourseDetail && <div>{activeCourseDetail.title}</div>}
            <div style={{ width: "100%" }}>
              <Select
                label="Move to"
                value={normalizeTerm(activeCourse.term)}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => {
                  moveCourse(activeCourseCode, e.target.value);
                  setActiveCourseCode(null);
                }}
                options={terms.map((t) => ({ value: t.id, label: `${t.season} ${t.calendarYear}` }))}
              />
            </div>
            <Switch
              label="Locked (kept in place by auto-plan)"
              checked={!!activeCourse.locked}
              onChange={(v: boolean) => toggleLock(activeCourseCode, v)}
            />
            <Button variant="link" onClick={() => navigate(`/courses/${activeCourseCode}`)}>
              View course details
            </Button>
          </div>
        )}
      </Dialog>

      {/* ---- Auto-plan drawer ---- */}
      <Drawer open={autoPlanOpen} onClose={() => setAutoPlanOpen(false)} title="Auto-plan">
        <AutoPlanPanel
          generating={autoPlanGenerating}
          onGenerate={handleAutoPlanGenerate}
          diff={autoPlanDiff}
          onApply={handleAutoPlanApply}
          onCancel={handleAutoPlanCancel}
        >
          <Callout tone="info" title="How this works">
            Fills open requirement-group gaps across your enrolled programs into the terms shown on the board,
            honouring offering terms and prerequisites already visible above.
          </Callout>
          <div style={{ width: "100%" }}>
            <Select
              label="Max new credits per term"
              value={String(autoPlanCreditCap)}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setAutoPlanCreditCap(Number(e.target.value))}
              options={[1, 1.5, 2, 2.5, 3].map((n) => ({ value: String(n), label: n.toFixed(1) }))}
            />
          </div>
        </AutoPlanPanel>
      </Drawer>

      {/* ---- Toasts ---- */}
      <div
        role="status"
        aria-live="polite"
        style={{
          position: "fixed",
          right: 20,
          bottom: 20,
          display: "flex",
          flexDirection: "column",
          gap: 8,
          zIndex: 200,
        }}
      >
        {toasts.map((t) => (
          <Toast key={t.id} tone={t.tone} onClose={() => setToasts((prev) => prev.filter((x) => x.id !== t.id))}>
            {t.message}
          </Toast>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Loading skeleton — mirrors the CourseRail + TermColumn layout (design/07: "skeletons that match final layout")
// ---------------------------------------------------------------------------

function PlanBoardSkeleton() {
  return (
    <div style={{ display: "flex", gap: 24 }}>
      <div style={{ width: 260, flexShrink: 0, display: "flex", flexDirection: "column", gap: 10 }}>
        <Skeleton height={36} />
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} height={64} radius="var(--radius-md)" />
        ))}
      </div>
      <div style={{ display: "flex", gap: 14, flex: 1, minWidth: 0 }}>
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} style={{ width: 260, flexShrink: 0, display: "flex", flexDirection: "column", gap: 10 }}>
            <Skeleton height={40} radius="var(--radius-lg)" />
            <Skeleton height={90} radius="var(--radius-md)" />
            <Skeleton height={90} radius="var(--radius-md)" />
          </div>
        ))}
      </div>
    </div>
  );
}
