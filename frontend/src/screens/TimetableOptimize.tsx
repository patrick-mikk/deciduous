import * as React from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { api } from "@/api";
import type { Course, SessionCode } from "@/api";
import {
  Button,
  Callout,
  Checkbox,
  EmptyState,
  OptimizerPanel,
  PageHeader,
  RangeSlider,
  ScheduleCandidateList,
  Select,
  Skeleton,
  Switch,
  TimetableGrid,
  Toast,
} from "@/ds";

import {
  COURSE_COLORS,
  defaultTerm,
  loadStoredTimetable,
  overlaps,
  saveStoredTimetable,
  termLabel,
  type ScenarioVM,
  type StoredTimetable,
  type TimeInterval,
} from "./Timetable";

/**
 * Timetable optimizer — `/timetable/optimize` (design/screens/04-plan-and-timetable.md
 * "Timetable optimizer").
 *
 * OptimizerPanel (preferences: class window, avoid Fri/mornings, keep-locked,
 * allow full/waitlisted) → ScheduleCandidateList (ranked, conflict-free,
 * mini-grid previews) → Preview renders on a full TimetableGrid → "Use this"
 * writes the picks back into the scenario `/timetable` is reading from.
 *
 * Reads/writes the same client-local scenario storage as Timetable.tsx (see
 * that file's header comment — `POST /api/timetable/optimize`,
 * design/06-data-model-and-api.md line 85, doesn't exist on `ApiClient` yet).
 * The candidate search itself (backtracking section-choice enumeration,
 * conflict-free only, scored by distinct days + total gap time) runs entirely
 * client-side, standing in for that endpoint.
 */

// ---------------------------------------------------------------------------
// Section-choice search
// ---------------------------------------------------------------------------

type SectionLike = Course["sections"][number];

interface Group {
  code: string;
  method: string;
  options: SectionLike[];
}

interface FilterOpts {
  allowFull: boolean;
  avoidFri: boolean;
  avoidMornings: boolean;
  earliestMin: number;
  latestMin: number;
}

function withinWindow(sec: SectionLike, opts: FilterOpts): boolean {
  return sec.meetingTimes.every(
    (mt) =>
      mt.startMin >= opts.earliestMin &&
      mt.endMin <= opts.latestMin &&
      (!opts.avoidFri || mt.day !== 5) &&
      (!opts.avoidMornings || mt.startMin >= 660),
  );
}

/** Seats/preferences are soft: fall back to the wider pool rather than producing zero candidates. */
function optionsFor(secs: SectionLike[], opts: FilterOpts): SectionLike[] {
  const seatOk = opts.allowFull ? secs : secs.filter((s) => s.currentEnrol < s.maxEnrol);
  const seatPool = seatOk.length > 0 ? seatOk : secs;
  const windowed = seatPool.filter((s) => withinWindow(s, opts));
  return windowed.length > 0 ? windowed : seatPool;
}

function buildGroups(
  courseCodes: string[],
  courseDetails: Map<string, Course | null>,
  scenario: ScenarioVM,
  keepLocked: boolean,
  filterOpts: FilterOpts,
): { fixedBlocks: TimeInterval[]; groups: Group[] } {
  const fixedBlocks: TimeInterval[] = [];
  const groups: Group[] = [];
  for (const code of courseCodes) {
    const course = courseDetails.get(code);
    if (!course) continue;
    const byMethod = new Map<string, SectionLike[]>();
    course.sections.forEach((sec) => {
      if (!byMethod.has(sec.teachMethod)) byMethod.set(sec.teachMethod, []);
      byMethod.get(sec.teachMethod)?.push(sec);
    });
    for (const [method, secs] of byMethod) {
      const lockedName = keepLocked && scenario.locked[code]?.[method] ? scenario.selected[code]?.[method] : undefined;
      const lockedSec = lockedName ? secs.find((s) => s.name === lockedName) : undefined;
      if (lockedSec) {
        lockedSec.meetingTimes.forEach((mt) => fixedBlocks.push(mt));
        continue;
      }
      groups.push({ code, method, options: optionsFor(secs, filterOpts) });
    }
  }
  return { fixedBlocks, groups };
}

interface CandidateBlock extends TimeInterval {
  code: string;
  method: string;
  section: string;
  color: string;
  building: string;
}

export interface Candidate {
  id: string;
  score: number;
  days: number;
  gaps: string;
  summary: string;
  preview: { day: number; top: number; h: number; color: string }[];
  picks: Record<string, Record<string, string>>;
  blocks: CandidateBlock[];
}

const DAY_NAMES = ["", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const GRID_START = 8 * 60;
const GRID_END = 22 * 60;

function scoreBlocks(blocks: TimeInterval[]): { score: number; days: number; gapMin: number; gapCount: number } {
  const byDay = new Map<number, TimeInterval[]>();
  blocks.forEach((b) => {
    if (!byDay.has(b.day)) byDay.set(b.day, []);
    byDay.get(b.day)?.push(b);
  });
  const days = byDay.size;
  let gapMin = 0;
  let gapCount = 0;
  for (const list of byDay.values()) {
    const sorted = [...list].sort((a, b) => a.startMin - b.startMin);
    for (let i = 1; i < sorted.length; i++) {
      const gap = sorted[i].startMin - sorted[i - 1].endMin;
      if (gap > 0) {
        gapMin += gap;
        gapCount += 1;
      }
    }
  }
  const raw = 100 - days * 6 - Math.round(gapMin / 30) * 3;
  return { score: Math.max(40, Math.min(99, raw)), days, gapMin, gapCount };
}

function colorForCode(courseCodes: string[], code: string): string {
  const idx = courseCodes.indexOf(code);
  return COURSE_COLORS[(idx < 0 ? 0 : idx) % COURSE_COLORS.length];
}

/** Backtracking search over each (course, teach method) group's candidate sections; conflict-free only. */
function generateCandidates(
  courseCodes: string[],
  groups: Group[],
  fixedBlocks: TimeInterval[],
  maxResults = 8,
): Candidate[] {
  const raw: { picks: Record<string, Record<string, string>>; blocks: CandidateBlock[]; allBlocks: TimeInterval[] }[] = [];
  const currentPicks: { code: string; method: string; sec: SectionLike }[] = [];
  let visited = 0;

  function backtrack(i: number, blocksSoFar: TimeInterval[]) {
    if (visited++ > 20000 || raw.length >= 500) return;
    if (i === groups.length) {
      const picks: Record<string, Record<string, string>> = {};
      const blocks: CandidateBlock[] = [];
      currentPicks.forEach(({ code, method, sec }) => {
        picks[code] = { ...(picks[code] ?? {}), [method]: sec.name };
        sec.meetingTimes.forEach((mt) =>
          blocks.push({ code, method, section: sec.name, color: colorForCode(courseCodes, code), day: mt.day, startMin: mt.startMin, endMin: mt.endMin, building: mt.building }),
        );
      });
      raw.push({ picks, blocks, allBlocks: blocksSoFar });
      return;
    }
    const g = groups[i];
    for (const sec of g.options) {
      if (sec.meetingTimes.some((mt) => blocksSoFar.some((b) => overlaps(b, mt)))) continue;
      currentPicks.push({ code: g.code, method: g.method, sec });
      backtrack(i + 1, [...blocksSoFar, ...sec.meetingTimes]);
      currentPicks.pop();
    }
  }
  backtrack(0, fixedBlocks);

  const scored = raw.map(({ picks, blocks, allBlocks }) => {
    const { score, days, gapMin, gapCount } = scoreBlocks(allBlocks);
    const gaps = gapCount === 0 ? "0 gaps" : `${gapCount} gap${gapCount === 1 ? "" : "s"} (${gapMin}m)`;
    const daysUsed = Array.from(new Set(allBlocks.map((b) => b.day)))
      .sort((a, b) => a - b)
      .map((d) => DAY_NAMES[d]);
    const preview = allBlocks
      .filter((b) => b.day >= 1 && b.day <= 5)
      .map((b) => ({
        day: b.day - 1,
        top: Math.max(0, Math.min(100, ((b.startMin - GRID_START) / (GRID_END - GRID_START)) * 100)),
        h: Math.max(4, Math.min(100, ((b.endMin - b.startMin) / (GRID_END - GRID_START)) * 100)),
        color: blocks.find((bl) => bl.day === b.day && bl.startMin === b.startMin)?.color ?? "var(--primary)",
      }));
    return { score, days, gaps, summary: daysUsed.join(" · "), preview, picks, blocks };
  });

  scored.sort((a, b) => b.score - a.score || a.days - b.days);
  return scored.slice(0, maxResults).map((c, i) => ({ id: `cand-${i + 1}`, ...c }));
}

// ---------------------------------------------------------------------------
// Screen
// ---------------------------------------------------------------------------

interface ToastItem {
  id: number;
  tone: "info" | "success" | "warning" | "danger";
  message: string;
}

export default function TimetableOptimize() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [sessions, setSessions] = React.useState<SessionCode[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [loadError, setLoadError] = React.useState<string | null>(null);
  const [reloadKey, setReloadKey] = React.useState(0);

  const [term, setTerm] = React.useState<SessionCode>(searchParams.get("term") ?? "");
  const [stored, setStored] = React.useState<StoredTimetable>({});

  const [courseDetails, setCourseDetails] = React.useState<Map<string, Course | null>>(new Map());
  const [detailsLoading, setDetailsLoading] = React.useState(true);
  const fetchedRef = React.useRef<Set<string>>(new Set());

  // ---- Preferences ----
  const [window_, setWindow] = React.useState<[number, number]>([8, 20]);
  const [avoidFri, setAvoidFri] = React.useState(false);
  const [avoidMornings, setAvoidMornings] = React.useState(false);
  const [keepLocked, setKeepLocked] = React.useState(true);
  const [allowFull, setAllowFull] = React.useState(false);

  const [generating, setGenerating] = React.useState(false);
  const [candidates, setCandidates] = React.useState<Candidate[] | null>(null);
  const [activeId, setActiveId] = React.useState<string | null>(null);

  const [toasts, setToasts] = React.useState<ToastItem[]>([]);
  const toastIdRef = React.useRef(0);
  const pushToast = React.useCallback((tone: ToastItem["tone"], message: string) => {
    const id = ++toastIdRef.current;
    setToasts((prev) => [...prev, { id, tone, message }]);
    window.setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4500);
  }, []);

  // ---- Sessions (for the default term + label if ?term= is missing) ----
  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    api
      .getSessions()
      .then((sess) => {
        if (cancelled) return;
        setSessions(sess);
        setLoading(false);
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setLoadError(e instanceof Error ? e.message : "Couldn't load sessions.");
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  React.useEffect(() => {
    if (sessions.length === 0) return;
    setTerm((prev) => (prev && sessions.includes(prev) ? prev : defaultTerm(sessions)));
  }, [sessions]);

  // ---- Read the scenario storage Timetable.tsx maintains ----
  React.useEffect(() => {
    setStored(loadStoredTimetable());
  }, [term]);

  const termState = term ? stored[term] : undefined;
  const scenario = termState ? (termState.scenarios.find((s) => s.id === termState.activeScenarioId) ?? termState.scenarios[0]) : undefined;

  React.useEffect(() => {
    if (!scenario) {
      setDetailsLoading(false);
      return;
    }
    const missing = scenario.courseCodes.filter((c) => !fetchedRef.current.has(c));
    if (missing.length === 0) {
      setDetailsLoading(false);
      return;
    }
    setDetailsLoading(true);
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
      setDetailsLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [scenario]);

  // Reset any stale results when the term/scenario changes underneath the panel.
  React.useEffect(() => {
    setCandidates(null);
    setActiveId(null);
  }, [term, scenario?.id]);

  function handleGenerate() {
    if (!scenario) return;
    setGenerating(true);
    window.setTimeout(() => {
      const filterOpts: FilterOpts = {
        allowFull,
        avoidFri,
        avoidMornings,
        earliestMin: window_[0] * 60,
        latestMin: window_[1] * 60,
      };
      const { fixedBlocks, groups } = buildGroups(scenario.courseCodes, courseDetails, scenario, keepLocked, filterOpts);
      const results = generateCandidates(scenario.courseCodes, groups, fixedBlocks);
      setGenerating(false);
      setCandidates(results);
      setActiveId(results[0]?.id ?? null);
      if (results.length === 0) pushToast("warning", "No conflict-free combination found. Try loosening your preferences.");
      else pushToast("success", `Generated ${results.length} conflict-free candidate${results.length === 1 ? "" : "s"}.`);
    }, 700);
  }

  function handleUse(c: Candidate) {
    if (!term || !scenario) return;
    const fresh = loadStoredTimetable();
    const ts = fresh[term];
    if (!ts) return;
    const next: StoredTimetable = {
      ...fresh,
      [term]: {
        ...ts,
        scenarios: ts.scenarios.map((s) => {
          if (s.id !== scenario.id) return s;
          const selected = { ...s.selected };
          for (const [code, methods] of Object.entries(c.picks)) {
            for (const [method, name] of Object.entries(methods)) {
              if (keepLocked && s.locked[code]?.[method]) continue; // never override a kept-locked pick
              selected[code] = { ...(selected[code] ?? {}), [method]: name };
            }
          }
          return { ...s, selected };
        }),
      },
    };
    saveStoredTimetable(next);
    setStored(next);
    pushToast("success", `Applied candidate #${c.id.split("-")[1]} to ${scenario.name}.`);
    navigate(`/timetable?term=${encodeURIComponent(term)}`);
  }

  const activeCandidate = candidates?.find((c) => c.id === activeId) ?? null;
  const previewBlocks = React.useMemo(() => (activeCandidate ? activeCandidate.blocks.map((b) => ({ ...b, room: b.building })) : []), [activeCandidate]);

  const ready = !loading && !loadError && !!term;
  const hasCourses = !!scenario && scenario.courseCodes.length > 0;

  return (
    <div>
      <PageHeader
        title="Optimize timetable"
        subtitle={term ? `Ranked, conflict-free schedule candidates for ${termLabel(term)}.` : "Ranked, conflict-free schedule candidates."}
        actions={
          <Button variant="secondary" icon="arrow-left" onClick={() => navigate(`/timetable${term ? `?term=${encodeURIComponent(term)}` : ""}`)}>
            Back to timetable
          </Button>
        }
      />

      {loadError && (
        <div style={{ marginBottom: 20 }}>
          <Callout
            tone="danger"
            title="Couldn't load sessions"
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

      {loading || detailsLoading ? (
        <OptimizeSkeleton />
      ) : loadError ? null : !hasCourses ? (
        <EmptyState
          icon="wand-sparkles"
          title="Nothing to optimize yet"
          description={term ? `${termLabel(term)} has no courses in the timetable tray yet. Add courses first, then come back to generate candidates.` : "Add courses to a term's timetable tray first."}
          action={
            <Button variant="primary" onClick={() => navigate(`/timetable${term ? `?term=${encodeURIComponent(term)}` : ""}`)}>
              Go to Timetable
            </Button>
          }
        />
      ) : (
        <div style={{ display: "flex", gap: 24, alignItems: "flex-start", flexWrap: "wrap" }}>
          <OptimizerPanel generating={generating} onGenerate={handleGenerate}>
            <RangeSlider
              label="Class window"
              min={7}
              max={22}
              step={1}
              value={window_}
              onChange={(v: [number, number]) => setWindow(v)}
              format={(v: number) => `${v}:00`}
            />
            <Checkbox label="Avoid Fridays" checked={avoidFri} onChange={setAvoidFri} />
            <Checkbox label="Avoid mornings (before 11:00)" checked={avoidMornings} onChange={setAvoidMornings} />
            <Switch label="Keep locked sections" checked={keepLocked} onChange={setKeepLocked} />
            <Switch label="Allow full / waitlisted sections" checked={allowFull} onChange={setAllowFull} />
          </OptimizerPanel>

          <div style={{ flex: 1, minWidth: 320, display: "flex", flexDirection: "column", gap: 16 }}>
            {candidates == null ? (
              <EmptyState
                icon="sparkles"
                title="No candidates yet"
                description="Set your preferences and generate to see ranked, conflict-free schedule options."
              />
            ) : candidates.length === 0 ? (
              <Callout tone="warning" title="No conflict-free combination found">
                Every combination of sections for this term's courses conflicts under the current preferences. Try
                widening the class window or allowing full/waitlisted sections.
              </Callout>
            ) : (
              <ScheduleCandidateList
                candidates={candidates}
                activeId={activeId}
                onPreview={(c: Candidate) => setActiveId(c.id)}
                onUse={handleUse}
              />
            )}

            {activeCandidate && (
              <div>
                <div style={{ marginBottom: 8, fontSize: "var(--text-body-sm)", color: "var(--text-secondary)" }}>
                  Preview: candidate #{activeCandidate.id.split("-")[1]} · score {activeCandidate.score}
                </div>
                <div style={{ overflowX: "auto" }}>
                  <TimetableGrid startHour={8} endHour={22} blocks={previewBlocks} />
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {!ready && !loading && !loadError && (
        <div style={{ marginTop: 16, width: 220 }}>
          <Select label="Term" value={term} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setTerm(e.target.value)} options={sessions.map((s) => ({ value: s, label: termLabel(s) }))} />
        </div>
      )}

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
// Loading skeleton
// ---------------------------------------------------------------------------

function OptimizeSkeleton() {
  return (
    <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
      <Skeleton height={360} width={300} radius="var(--radius-lg)" />
      <div style={{ flex: 1, minWidth: 320, display: "flex", flexDirection: "column", gap: 12 }}>
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} height={78} radius="var(--radius-lg)" />
        ))}
      </div>
    </div>
  );
}
