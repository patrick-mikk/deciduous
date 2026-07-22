import * as React from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { api, remainingRequirementMatches, countsTowardPhrase, isExcludedByTaken } from "@/api";
import type { Course, Program, SessionCode, StudentRecord } from "@/api";
import {
  Button,
  Callout,
  Chip,
  Combobox,
  CourseTray,
  Dialog,
  EmptyState,
  PageHeader,
  ScenarioTabs,
  SectionList,
  Select,
  Skeleton,
  TimetableGrid,
  Toast,
} from "@/ds";

/**
 * Timetable builder — `/timetable` (design/screens/04-plan-and-timetable.md
 * "Timetable builder").
 *
 * ScenarioTabs (Plan A / Plan B / …) + CourseTray (one selectable section per
 * teach method, lockable) + TimetableGrid (Mon–Fri, conflicting sections
 * render a red hatch, click a block to swap sections via a SectionList
 * popover) + an ICS export and a link into the optimizer.
 *
 * Note on `GET/PUT /api/plan/:term/sections` (design/06-data-model-and-api.md
 * line 85): that endpoint doesn't exist on `ApiClient` yet (see
 * frontend/src/api/client.ts — only reference-data/programs/courses/me/share
 * are implemented). This screen still binds to real data for everything that
 * *does* exist (course + section details, sessions, the student's planned
 * courses) and keeps scenarios — tray membership, section picks, locks — as
 * client-side state autosaved to localStorage under a per-term key, mirroring
 * the same pattern src/screens/Plan.tsx uses for `/api/plan`. `/timetable/optimize`
 * (src/screens/TimetableOptimize.tsx) reads/writes the same storage key so
 * "Use this" candidates land back here.
 */

// ---------------------------------------------------------------------------
// Local types + client-side scenario storage
// ---------------------------------------------------------------------------

export interface ScenarioVM {
  id: string;
  name: string;
  courseCodes: string[];
  selected: Record<string, Record<string, string>>; // code -> teachMethod -> section name
  locked: Record<string, Record<string, boolean>>; // code -> teachMethod -> locked
}

export interface TermTimetableState {
  activeScenarioId: string;
  scenarios: ScenarioVM[];
}

export type StoredTimetable = Partial<Record<string, TermTimetableState>>;

export const TIMETABLE_STORAGE_KEY = "deciduous:timetable:v1";
/** Per-course accent palette, shared with TimetableOptimize.tsx so a course keeps its colour across screens. */
export const COURSE_COLORS = ["var(--br1)", "var(--br3)", "var(--br5)", "var(--br2)", "var(--br4)", "var(--accent)"];

export function loadStoredTimetable(): StoredTimetable {
  try {
    const raw = window.localStorage.getItem(TIMETABLE_STORAGE_KEY);
    if (!raw) return {};
    const parsed: unknown = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? (parsed as StoredTimetable) : {};
  } catch {
    return {};
  }
}

export function saveStoredTimetable(data: StoredTimetable) {
  try {
    window.localStorage.setItem(TIMETABLE_STORAGE_KEY, JSON.stringify(data));
  } catch {
    // Best-effort only — private browsing / quota errors shouldn't break the builder.
  }
}

function newScenario(id: string, name: string, courseCodes: string[] = []): ScenarioVM {
  return { id, name, courseCodes, selected: {}, locked: {} };
}

/** Y-course transcript sessions are stored "20239-20241" — the timetable only tracks one term. */
function normalizeTerm(session: string): string {
  return session.split("-")[0];
}

export function seasonOf(termId: string): "Fall" | "Winter" | "Summer" {
  if (termId.endsWith("9")) return "Fall";
  if (termId.endsWith("5")) return "Summer";
  return "Winter";
}

export function termLabel(termId: string): string {
  return `${seasonOf(termId)} ${termId.slice(0, 4)}`;
}

export function defaultTerm(sessions: SessionCode[]): SessionCode {
  return sessions.find((s) => s.endsWith("9")) ?? sessions[0] ?? "";
}

function fmtTime(min: number): string {
  const h = Math.floor(min / 60);
  const m = min % 60;
  const period = h >= 12 ? "PM" : "AM";
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}:${String(m).padStart(2, "0")} ${period}`;
}

const DAY_NAMES = ["", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export interface TimeInterval {
  day: number;
  startMin: number;
  endMin: number;
}

export function overlaps(a: TimeInterval, b: TimeInterval): boolean {
  return a.day === b.day && a.startMin < b.endMin && b.startMin < a.endMin;
}

export interface BlockVM extends TimeInterval {
  code: string;
  method: string;
  section: string;
  color: string;
  locked: boolean;
  building: string;
  conflict: boolean;
}

/** Every meeting time of every selected section in the scenario, with pairwise conflicts flagged. */
function buildBlocks(scenario: ScenarioVM, courseDetails: Map<string, Course | null>): BlockVM[] {
  const blocks: BlockVM[] = [];
  scenario.courseCodes.forEach((code, idx) => {
    const course = courseDetails.get(code);
    if (!course) return;
    const color = COURSE_COLORS[idx % COURSE_COLORS.length];
    const methodSel = scenario.selected[code] ?? {};
    for (const [method, sectionName] of Object.entries(methodSel)) {
      const sec = course.sections.find((s) => s.teachMethod === method && s.name === sectionName);
      if (!sec) continue;
      for (const mt of sec.meetingTimes) {
        blocks.push({
          code,
          method,
          section: sectionName,
          color,
          locked: !!scenario.locked[code]?.[method],
          day: mt.day,
          startMin: mt.startMin,
          endMin: mt.endMin,
          building: mt.building,
          conflict: false,
        });
      }
    }
  });
  for (let i = 0; i < blocks.length; i++) {
    for (let j = i + 1; j < blocks.length; j++) {
      if (overlaps(blocks[i], blocks[j])) {
        blocks[i].conflict = true;
        blocks[j].conflict = true;
      }
    }
  }
  return blocks;
}

function conflictMessages(blocks: BlockVM[]): string[] {
  const msgs: string[] = [];
  for (let i = 0; i < blocks.length; i++) {
    for (let j = i + 1; j < blocks.length; j++) {
      const a = blocks[i];
      const b = blocks[j];
      if (!overlaps(a, b)) continue;
      const start = Math.max(a.startMin, b.startMin);
      const end = Math.min(a.endMin, b.endMin);
      msgs.push(
        `${a.code} ${a.method} overlaps ${b.code} ${b.method} (${DAY_NAMES[a.day]} ${fmtTime(start)}–${fmtTime(end)})`,
      );
    }
  }
  return msgs;
}

// ---- ICS export -------------------------------------------------------------

function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

function nextDateForIsoDay(isoDay: number): Date {
  const now = new Date();
  const jsDay = now.getDay() === 0 ? 7 : now.getDay(); // ISO Mon=1..Sun=7
  let diff = isoDay - jsDay;
  if (diff < 0) diff += 7;
  return new Date(now.getFullYear(), now.getMonth(), now.getDate() + diff);
}

function icsDateTime(d: Date, minutes: number): string {
  const hh = Math.floor(minutes / 60);
  const mm = minutes % 60;
  return `${d.getFullYear()}${pad2(d.getMonth() + 1)}${pad2(d.getDate())}T${pad2(hh)}${pad2(mm)}00`;
}

function buildIcs(blocks: BlockVM[], termName: string): string {
  const lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Deciduous//Timetable//EN", "CALSCALE:GREGORIAN"];
  blocks.forEach((b, i) => {
    const date = nextDateForIsoDay(b.day);
    lines.push(
      "BEGIN:VEVENT",
      `UID:deciduous-${b.code}-${b.section}-${i}@deciduous.local`,
      `SUMMARY:${b.code} ${b.section}`,
      `DESCRIPTION:${termName}`,
      `LOCATION:${b.building || "TBA"}`,
      `DTSTART:${icsDateTime(date, b.startMin)}`,
      `DTEND:${icsDateTime(date, b.endMin)}`,
      "RRULE:FREQ=WEEKLY;COUNT=12",
      "END:VEVENT",
    );
  });
  lines.push("END:VCALENDAR");
  return lines.join("\r\n");
}

function downloadText(filename: string, mime: string, text: string) {
  const blob = new Blob([text], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

interface ToastItem {
  id: number;
  tone: "info" | "success" | "warning" | "danger";
  message: string;
}

// ---------------------------------------------------------------------------
// Screen
// ---------------------------------------------------------------------------

export default function Timetable() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // ---- Core data ----
  const [sessions, setSessions] = React.useState<SessionCode[]>([]);
  const [record, setRecord] = React.useState<StudentRecord | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [loadError, setLoadError] = React.useState<string | null>(null);
  const [reloadKey, setReloadKey] = React.useState(0);

  const [term, setTerm] = React.useState<SessionCode>(searchParams.get("term") ?? "");

  // ---- Scenario storage (client-local until /api/plan/:term/sections ships) ----
  const [stored, setStored] = React.useState<StoredTimetable>({});
  const storedReadyRef = React.useRef(false);

  const [courseDetails, setCourseDetails] = React.useState<Map<string, Course | null>>(new Map());
  const fetchedRef = React.useRef<Set<string>>(new Set());

  // ---- Add-course dialog ----
  const [addOpen, setAddOpen] = React.useState(false);
  const [addChoice, setAddChoice] = React.useState<string | null>(null);
  // `/api/courses` is paged, so the dialog searches the server as the user
  // types (driven by the Combobox query) instead of loading and client-side
  // filtering a single alphabetical page -- which could neither default
  // usefully nor reach a course past page one.
  const [addQuery, setAddQuery] = React.useState("");
  const [catalog, setCatalog] = React.useState<Course[]>([]);
  const [catalogLoading, setCatalogLoading] = React.useState(false);
  const [catalogError, setCatalogError] = React.useState<string | null>(null);
  const [catalogRetryKey, setCatalogRetryKey] = React.useState(0);

  // ---- Swap-section popover (click a grid block) ----
  const [swapCode, setSwapCode] = React.useState<string | null>(null);

  // ---- Toasts ----
  const [toasts, setToasts] = React.useState<ToastItem[]>([]);
  const toastIdRef = React.useRef(0);
  const pushToast = React.useCallback((tone: ToastItem["tone"], message: string) => {
    const id = ++toastIdRef.current;
    setToasts((prev) => [...prev, { id, tone, message }]);
    window.setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4500);
  }, []);

  // ---- Load sessions + student record ----
  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    Promise.all([api.getSessions(), api.getMyRecord()])
      .then(([sess, rec]) => {
        if (cancelled) return;
        setSessions(sess);
        setRecord(rec);
        setLoading(false);
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setLoadError(e instanceof Error ? e.message : "Couldn't load the timetable.");
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  // ---- Enrolled program requirements + ranked remaining suggestions --------
  const [programDetails, setProgramDetails] = React.useState<Program[]>([]);
  const [suggestionCourses, setSuggestionCourses] = React.useState<Course[]>([]);
  React.useEffect(() => {
    if (!record || record.programs.length === 0) {
      setProgramDetails([]);
      return;
    }
    let cancelled = false;
    Promise.all(record.programs.map((p) => api.getProgram(p.code).catch(() => null))).then((res) => {
      if (!cancelled) setProgramDetails(res.filter((p): p is Program => p != null));
    });
    return () => {
      cancelled = true;
    };
  }, [record]);

  // Completed/in-progress transcript codes -- "taken" for both requirement-line
  // accounting (remainingMatches below) and exclusion filtering (the
  // suggestion-fetch effect below).
  const takenCodes = React.useMemo(() => {
    if (!record) return new Set<string>();
    return new Set(
      record.transcript.filter((t) => t.status === "completed" || t.status === "in_progress").map((t) => t.code),
    );
  }, [record]);

  const remainingMatches = React.useMemo(() => {
    if (!record) return [];
    return remainingRequirementMatches(programDetails, record.requirementProgress, takenCodes);
  }, [record, programDetails, takenCodes]);

  // Fetch details for the top suggestions so the "add a course" dialog can lead
  // with courses that fill a remaining requirement (later narrowed to the ones
  // actually offered in the selected term). Formal Calendar exclusions (e.g. a
  // course excluded by an already-completed one) are dropped here too -- a hard
  // rule, checked independently of the requirement-line satisfaction above.
  React.useEffect(() => {
    const top = remainingMatches.slice(0, 40).map((m) => m.code);
    if (top.length === 0) {
      setSuggestionCourses([]);
      return;
    }
    let cancelled = false;
    Promise.all(
      top.map((code) =>
        api
          .getCourse(code)
          .then((c) => [code, c] as const)
          .catch(() => [code, null] as const),
      ),
    ).then((pairs) => {
      if (cancelled) return;
      const byCode = new Map(pairs);
      setSuggestionCourses(
        top
          .map((code) => byCode.get(code))
          .filter((c): c is Course => Boolean(c))
          .filter((c) => !isExcludedByTaken(c.exclusions, takenCodes)),
      );
    });
    return () => {
      cancelled = true;
    };
  }, [remainingMatches, takenCodes]);

  // ---- Load stored scenarios once ----
  React.useEffect(() => {
    setStored(loadStoredTimetable());
    storedReadyRef.current = true;
  }, []);

  // ---- Default term once sessions arrive (a valid ?term= wins) ----
  React.useEffect(() => {
    if (sessions.length === 0) return;
    setTerm((prev) => (prev && sessions.includes(prev) ? prev : defaultTerm(sessions)));
  }, [sessions]);

  // ---- Keep ?term= in sync so the optimizer link carries it ----
  React.useEffect(() => {
    if (!term) return;
    if (searchParams.get("term") === term) return;
    const next = new URLSearchParams(searchParams);
    next.set("term", term);
    setSearchParams(next, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [term]);

  // ---- Seed a term's first scenario from the student's "planned" transcript courses ----
  React.useEffect(() => {
    if (!term || !record || !storedReadyRef.current) return;
    setStored((prev) => {
      if (prev[term]) return prev;
      const seeded = record.transcript
        .filter((t) => t.status === "planned" && normalizeTerm(t.session) === term)
        .map((t) => t.code);
      return { ...prev, [term]: { activeScenarioId: "plan-a", scenarios: [newScenario("plan-a", "Plan A", seeded)] } };
    });
  }, [term, record]);

  // ---- Autosave (stands in for `PUT /api/plan/:term/sections`) ----
  React.useEffect(() => {
    if (!storedReadyRef.current) return;
    saveStoredTimetable(stored);
  }, [stored]);

  const termState = term ? stored[term] : undefined;
  const scenario = termState ? (termState.scenarios.find((s) => s.id === termState.activeScenarioId) ?? termState.scenarios[0]) : undefined;

  // ---- Fetch course details for the active scenario's tray ----
  React.useEffect(() => {
    if (!scenario) return;
    const missing = scenario.courseCodes.filter((c) => !fetchedRef.current.has(c));
    if (missing.length === 0) return;
    missing.forEach((c) => fetchedRef.current.add(c));
    let cancelled = false;
    Promise.all(
      missing.map((code) =>
        api
          .getCourse(code)
          .then((c) => [code, c] as const)
          .catch(() => [code, null] as const),
      ),
    ).then((pairs) => {
      if (cancelled) return;
      setCourseDetails((prev) => {
        const next = new Map(prev);
        for (const [code, c] of pairs) next.set(code, c);
        return next;
      });
    });
    return () => {
      cancelled = true;
    };
  }, [scenario]);

  // ---- Debounced server search for the "add course" dialog ----
  // Fires only while the dialog is open with a non-empty query; an empty query
  // keeps the Combobox in its "type to search" state (no arbitrary first-page
  // dump).
  const addSearchId = React.useRef(0);
  React.useEffect(() => {
    const q = addQuery.trim();
    if (!addOpen) {
      setCatalog([]);
      setCatalogLoading(false);
      return;
    }
    if (!q) {
      // Selecting an option resets the Combobox query to empty; keep the last
      // results so the chosen course's label still resolves in the trigger.
      setCatalogLoading(false);
      return;
    }
    const id = ++addSearchId.current;
    setCatalogLoading(true);
    setCatalogError(null);
    const t = window.setTimeout(() => {
      api
        .getCourses({ q })
        .then((cs) => {
          if (addSearchId.current !== id) return;
          setCatalog(cs);
          setCatalogLoading(false);
        })
        .catch((e: unknown) => {
          if (addSearchId.current !== id) return;
          setCatalogError(e instanceof Error ? e.message : "Couldn't search the course catalog.");
          setCatalogLoading(false);
        });
    }, 200);
    return () => window.clearTimeout(t);
  }, [addOpen, addQuery, catalogRetryKey]);

  // ---- Mutators (scoped to the active scenario) ----
  function mutateScenario(fn: (s: ScenarioVM) => ScenarioVM) {
    if (!term) return;
    setStored((prev) => {
      const ts = prev[term];
      if (!ts) return prev;
      const activeId = ts.activeScenarioId;
      return { ...prev, [term]: { ...ts, scenarios: ts.scenarios.map((s) => (s.id === activeId ? fn(s) : s)) } };
    });
  }

  function addCourseToTray(code: string) {
    mutateScenario((s) => (s.courseCodes.includes(code) ? s : { ...s, courseCodes: [...s.courseCodes, code] }));
    pushToast("success", `Added ${code} to the tray.`);
  }

  function removeCourseFromTray(code: string) {
    mutateScenario((s) => {
      const selected = { ...s.selected };
      const locked = { ...s.locked };
      delete selected[code];
      delete locked[code];
      return { ...s, courseCodes: s.courseCodes.filter((c) => c !== code), selected, locked };
    });
    pushToast("info", `Removed ${code} from the tray.`);
  }

  function selectSection(code: string, method: string, name: string) {
    if (scenario?.locked[code]?.[method]) {
      pushToast("warning", `${code} ${method} is locked. Unlock it before changing sections.`);
      return;
    }
    mutateScenario((s) => ({ ...s, selected: { ...s.selected, [code]: { ...(s.selected[code] ?? {}), [method]: name } } }));
  }

  function toggleLock(code: string, method: string) {
    mutateScenario((s) => {
      const wasLocked = !!s.locked[code]?.[method];
      return { ...s, locked: { ...s.locked, [code]: { ...(s.locked[code] ?? {}), [method]: !wasLocked } } };
    });
  }

  function autoPickAll() {
    if (!scenario) return;
    let hadConflict = false;
    mutateScenario((s) => {
      const selected: Record<string, Record<string, string>> = JSON.parse(JSON.stringify(s.selected));
      const chosen: TimeInterval[] = [];

      // Seed with the already-locked picks so auto-pick avoids conflicting with them.
      for (const code of s.courseCodes) {
        const course = courseDetails.get(code);
        if (!course) continue;
        for (const [method, name] of Object.entries(selected[code] ?? {})) {
          if (!s.locked[code]?.[method]) continue;
          course.sections.find((sec) => sec.teachMethod === method && sec.name === name)?.meetingTimes.forEach((mt) => chosen.push(mt));
        }
      }

      for (const code of s.courseCodes) {
        const course = courseDetails.get(code);
        if (!course) continue;
        const methods = new Map<string, Course["sections"]>();
        course.sections.forEach((sec) => {
          if (!methods.has(sec.teachMethod)) methods.set(sec.teachMethod, []);
          methods.get(sec.teachMethod)?.push(sec);
        });
        for (const [method, secs] of methods) {
          if (s.locked[code]?.[method]) continue; // keep locked picks untouched
          const open = secs.filter((sec) => sec.currentEnrol < sec.maxEnrol);
          const pool = open.length > 0 ? open : secs;
          const clean = pool.find((sec) => !sec.meetingTimes.some((mt) => chosen.some((b) => overlaps(b, mt))));
          const pick = clean ?? pool[0];
          if (!pick) continue;
          if (!clean) hadConflict = true;
          selected[code] = { ...(selected[code] ?? {}), [method]: pick.name };
          pick.meetingTimes.forEach((mt) => chosen.push(mt));
        }
      }
      return { ...s, selected };
    });
    if (hadConflict) pushToast("warning", "Auto-pick placed every course, but a few sections still conflict.");
    else pushToast("success", "Auto-pick chose a conflict-free section for every course.");
  }

  // ---- Scenario tabs ----
  function addScenario() {
    if (!term || !termState) return;
    const id = `scenario-${Date.now()}`;
    const letter = String.fromCharCode(65 + termState.scenarios.length);
    setStored((prev) => {
      const ts = prev[term];
      if (!ts) return prev;
      const base = ts.scenarios.find((s) => s.id === ts.activeScenarioId) ?? ts.scenarios[0];
      return {
        ...prev,
        [term]: { activeScenarioId: id, scenarios: [...ts.scenarios, newScenario(id, `Plan ${letter}`, base ? [...base.courseCodes] : [])] },
      };
    });
  }

  function selectScenario(id: string) {
    if (!term) return;
    setStored((prev) => {
      const ts = prev[term];
      if (!ts) return prev;
      return { ...prev, [term]: { ...ts, activeScenarioId: id } };
    });
  }

  function deleteScenario(id: string) {
    if (!term) return;
    setStored((prev) => {
      const ts = prev[term];
      if (!ts || ts.scenarios.length <= 1) return prev;
      const scenarios = ts.scenarios.filter((s) => s.id !== id);
      const activeScenarioId = ts.activeScenarioId === id ? scenarios[0].id : ts.activeScenarioId;
      return { ...prev, [term]: { activeScenarioId, scenarios } };
    });
  }

  function handleExport() {
    if (blocks.length === 0) {
      pushToast("warning", "Nothing to export yet. Add a course and pick sections first.");
      return;
    }
    downloadText(`deciduous-${term}.ics`, "text/calendar", buildIcs(blocks, termLabel(term)));
    pushToast("success", "Downloaded deciduous.ics");
  }

  // ---- View models ----
  const trayCourses = React.useMemo(() => {
    if (!scenario) return [];
    return scenario.courseCodes.map((code, idx) => {
      const course = courseDetails.get(code);
      return {
        code,
        color: COURSE_COLORS[idx % COURSE_COLORS.length],
        sections: (course?.sections ?? []).map((sec) => ({
          name: sec.name,
          teachMethod: sec.teachMethod,
          current: sec.currentEnrol,
          max: sec.maxEnrol,
          waitlist: sec.waitlist,
        })),
      };
    });
  }, [scenario, courseDetails]);

  const blocks = React.useMemo(() => (scenario ? buildBlocks(scenario, courseDetails) : []), [scenario, courseDetails]);
  const gridBlocks = React.useMemo(() => blocks.map((b) => ({ ...b, room: b.building })), [blocks]);
  const conflicts = React.useMemo(() => conflictMessages(blocks), [blocks]);

  const countsTowardByCode = React.useMemo(() => {
    const map: Record<string, string> = {};
    for (const m of remainingMatches) {
      const phrase = countsTowardPhrase(m.programs);
      if (phrase) map[m.code] = phrase;
    }
    return map;
  }, [remainingMatches]);

  // Default (nothing typed): lead with ranked remaining-requirement courses
  // that are actually offered in this term. Typing switches to catalog search.
  const addSuggesting = !addQuery.trim();
  const addOptions = React.useMemo(() => {
    if (!scenario || !term) return [];
    const season = seasonOf(term);
    const offeredInTerm = (c: Course) =>
      c.sectionCode === "Y" ||
      season === "Summer" ||
      (season === "Fall" && c.sectionCode === "F") ||
      (season === "Winter" && c.sectionCode === "S");
    const source = addSuggesting ? suggestionCourses : catalog;
    const list = source.filter((c) => !scenario.courseCodes.includes(c.code)).filter(offeredInTerm);
    // Keep the current pick resolvable even after the Combobox clears its query.
    if (addChoice && !list.some((c) => c.code === addChoice)) {
      const chosen =
        suggestionCourses.find((c) => c.code === addChoice) ?? catalog.find((c) => c.code === addChoice);
      if (chosen) list.unshift(chosen);
    }
    return list.map((c) => {
      const ct = addSuggesting ? countsTowardByCode[c.code] : undefined;
      return {
        value: c.code,
        label: ct ? `${c.code} · ${c.title} (counts toward ${ct})` : `${c.code} · ${c.title}`,
      };
    });
  }, [addSuggesting, suggestionCourses, catalog, scenario, term, addChoice, countsTowardByCode]);

  const swapCourse = swapCode ? (courseDetails.get(swapCode) ?? null) : null;
  const ready = !loading && !loadError && !!scenario;

  // ---------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------

  return (
    <div>
      <PageHeader
        title="Timetable"
        subtitle="Pick one section per teach method for each course, then check the grid for conflicts."
        actions={
          <div style={{ display: "flex", gap: 10, alignItems: "flex-end", flexWrap: "wrap" }}>
            <div style={{ width: 150 }}>
              <Select
                label="Term"
                value={term}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setTerm(e.target.value)}
                options={sessions.map((s) => ({ value: s, label: termLabel(s) }))}
                disabled={sessions.length === 0}
              />
            </div>
            {termState && (
              <ScenarioTabs
                scenarios={termState.scenarios}
                active={termState.activeScenarioId}
                onSelect={selectScenario}
                onAdd={addScenario}
                onDelete={deleteScenario}
              />
            )}
            <Button
              variant="secondary"
              icon="wand-sparkles"
              disabled={!term}
              onClick={() => navigate(`/timetable/optimize?term=${encodeURIComponent(term)}`)}
            >
              Optimize
            </Button>
            <Button variant="secondary" icon="download" disabled={!ready} onClick={handleExport}>
              Export ICS
            </Button>
          </div>
        }
      />

      {loadError && (
        <div style={{ marginBottom: 20 }}>
          <Callout
            tone="danger"
            title="Couldn't load the timetable"
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
        <TimetableSkeleton />
      ) : loadError ? null : !ready || !scenario ? (
        <TimetableSkeleton />
      ) : scenario.courseCodes.length === 0 ? (
        <EmptyState
          icon="calendar-days"
          title="No courses in this term yet"
          description={`Add a course to ${termLabel(term)} to start choosing sections and building the grid.`}
          action={
            <Button variant="primary" icon="plus" onClick={() => setAddOpen(true)}>
              Add a course
            </Button>
          }
        />
      ) : (
        <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 10, width: 280, flexShrink: 0 }}>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {scenario.courseCodes.map((code) => (
                <Chip key={code} tone="neutral" onRemove={() => removeCourseFromTray(code)}>
                  {code}
                </Chip>
              ))}
            </div>
            <CourseTray
              courses={trayCourses}
              selected={scenario.selected}
              locked={scenario.locked}
              onSelectSection={selectSection}
              onToggleLock={toggleLock}
              onAdd={() => setAddOpen(true)}
              onAutoPick={autoPickAll}
            />
          </div>

          <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: 14 }}>
            {conflicts.length > 0 && (
              <Callout tone="danger" title={`${conflicts.length} conflict${conflicts.length === 1 ? "" : "s"}`}>
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {conflicts.map((m, i) => (
                    <li key={i}>{m}</li>
                  ))}
                </ul>
              </Callout>
            )}
            <div style={{ overflowX: "auto" }}>
              <TimetableGrid startHour={8} endHour={22} blocks={gridBlocks} onBlockClick={(b: BlockVM) => setSwapCode(b.code)} />
            </div>
          </div>
        </div>
      )}

      {/* ---- Add course ---- */}
      <Dialog
        open={addOpen}
        title="Add a course"
        onClose={() => {
          setAddOpen(false);
          setAddChoice(null);
          setAddQuery("");
        }}
        footer={
          <>
            <Button
              variant="secondary"
              onClick={() => {
                setAddOpen(false);
                setAddChoice(null);
                setAddQuery("");
              }}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              disabled={!addChoice}
              onClick={() => {
                if (addChoice) addCourseToTray(addChoice);
                setAddOpen(false);
                setAddChoice(null);
                setAddQuery("");
              }}
            >
              Add
            </Button>
          </>
        }
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {catalogError && (
            <Callout
              tone="danger"
              title="Couldn't search the course catalog"
              action={
                <Button variant="secondary" size="sm" onClick={() => setCatalogRetryKey((k) => k + 1)}>
                  Retry
                </Button>
              }
            >
              {catalogError}
            </Callout>
          )}
          <Combobox
            label="Course"
            placeholder={addSuggesting ? "Pick a suggestion, or search all courses" : "Search courses…"}
            options={addOptions}
            value={addChoice}
            onChange={(v: string | null) => setAddChoice(v)}
            onQueryChange={(q: string) => setAddQuery(q)}
            loading={addSuggesting ? false : catalogLoading}
            clearable
          />
        </div>
      </Dialog>

      {/* ---- Swap section (click a grid block) ---- */}
      <Dialog open={swapCode != null} title={swapCode ?? ""} onClose={() => setSwapCode(null)} footer={<Button variant="secondary" onClick={() => setSwapCode(null)}>Close</Button>}>
        {swapCode &&
          (swapCourse ? (
            <SectionList
              sections={swapCourse.sections}
              selected={scenario?.selected[swapCode] ?? {}}
              onSelect={(method: string, name: string) => selectSection(swapCode, method, name)}
            />
          ) : (
            <Skeleton height={80} />
          ))}
      </Dialog>

      {/* ---- Toasts ---- */}
      <div
        role="status"
        aria-live="polite"
        style={{ position: "fixed", right: 20, bottom: 20, display: "flex", flexDirection: "column", gap: 8, zIndex: 200 }}
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
// Loading skeleton — mirrors the CourseTray + TimetableGrid layout (design/07: "skeletons that match final layout")
// ---------------------------------------------------------------------------

function TimetableSkeleton() {
  return (
    <div style={{ display: "flex", gap: 24 }}>
      <div style={{ width: 280, flexShrink: 0, display: "flex", flexDirection: "column", gap: 10 }}>
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} height={100} radius="var(--radius-md)" />
        ))}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <Skeleton height={460} radius="var(--radius-md)" />
      </div>
    </div>
  );
}
