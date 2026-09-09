import * as React from "react";
import { useNavigate } from "react-router-dom";

import {
  PageHeader,
  FilterBar,
  Input,
  Select,
  Checkbox,
  Button,
  CourseCard,
  Skeleton,
  EmptyState,
  Callout,
  Toast,
} from "@/ds";
import {
  api,
  courseLevel,
  BREADTH_KEYS,
  BREADTH_LABELS,
  remainingRequirementMatches,
  countsTowardPhrase,
  isExcludedByTaken,
} from "@/api";
import type { BreadthKey, Course, CourseSearchParams, Program, SessionCode, StudentRecord } from "@/api";

/**
 * Course search — routed at "/courses" (design/screens/03-programs-and-courses.md
 * "Course search"). FilterBar (level / breadth / term / has-seats) over
 * `GET /api/courses`, rendered as CourseCard rows; "Details" pushes to the
 * CourseDetail drawer route ("/courses/:code").
 */

const LEVELS = [100, 200, 300, 400] as const;

// Issue #7: the Courses search could show "Searching…" skeletons
// indefinitely if the backend's Timetable Builder call hangs or is
// unreachable. `api.getCourses` (frontend/src/api/client.ts) doesn't accept
// an AbortSignal, so this is a soft client-side timeout: if nothing comes
// back within `SEARCH_TIMEOUT_MS`, treat it as failed and show a retryable
// error instead of waiting forever -- if the real request does eventually
// resolve after that, its result still replaces the timeout message (see the
// search effect below), so a slow-but-eventually-successful call self-heals
// instead of getting stuck on a stale error.
const SEARCH_TIMEOUT_MS = 10_000;

// How many proactive suggestions to fetch details for on the default view.
// Ranked by how many programs each course advances, so the cap keeps the
// highest-value picks; each entry is one live `getCourse` call.
const SUGGEST_LIMIT = 24;

// Session code = 4-digit year + 1 term digit (AGENTS.md glossary): 1=Winter, 5=Summer, 9=Fall.
const TERM_DIGIT_LABEL: Record<string, string> = { "1": "Winter", "5": "Summer", "9": "Fall" };

function sessionLabel(session: SessionCode): string {
  const year = session.slice(0, 4);
  const digit = session.slice(4);
  return `${TERM_DIGIT_LABEL[digit] ?? "Session"} ${year}`;
}

/** "Society and Its Institutions (3)" -> "BR3". */
function breadthKeyFromLabel(label: string): BreadthKey | undefined {
  const m = /\((\d)\)\s*$/.exec(label);
  if (!m) return undefined;
  const key = `BR${m[1]}`;
  return (BREADTH_KEYS as readonly string[]).includes(key) ? (key as BreadthKey) : undefined;
}

const DAYS = ["", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
function fmtMin(min: number): string {
  const h = Math.floor(min / 60);
  const m = String(min % 60).padStart(2, "0");
  return `${String(h).padStart(2, "0")}:${m}`;
}

/** First lecture meeting, formatted for the card's compact meet-time line. */
function meetingSummary(course: Course): { meetTime?: string; location?: string; instructor?: string } {
  const lec = course.sections.find((s) => s.teachMethod === "LEC") ?? course.sections[0];
  if (!lec) return {};
  const mt = lec.meetingTimes[0];
  const meetTime = mt ? `${DAYS[mt.day]} ${fmtMin(mt.startMin)}–${fmtMin(mt.endMin)}` : undefined;
  const instructor = lec.instructors[0] ? `${lec.instructors[0].first} ${lec.instructors[0].last}` : undefined;
  return { meetTime, location: mt?.building, instructor };
}

type LoadState = "loading" | "ready" | "error";

export default function Courses() {
  const navigate = useNavigate();

  const [qInput, setQInput] = React.useState("");
  const [q, setQ] = React.useState("");
  const [level, setLevel] = React.useState("");
  const [breadth, setBreadth] = React.useState("");
  const [term, setTerm] = React.useState("");
  const [hasSeats, setHasSeats] = React.useState(false);

  const [sessions, setSessions] = React.useState<SessionCode[]>([]);
  const [courses, setCourses] = React.useState<Course[]>([]);
  const [state, setState] = React.useState<LoadState>("loading");
  const [error, setError] = React.useState<string | null>(null);
  const [record, setRecord] = React.useState<StudentRecord | null>(null);
  const [toast, setToast] = React.useState<string | null>(null);
  const [retryNonce, setRetryNonce] = React.useState(0);

  // ---- Proactive default: courses that fill still-open requirements --------
  const [programDetails, setProgramDetails] = React.useState<Program[]>([]);
  const [programsResolved, setProgramsResolved] = React.useState(false);
  const [suggestions, setSuggestions] = React.useState<Course[]>([]);
  const [suggestState, setSuggestState] = React.useState<LoadState>("loading");

  // The default view (nothing typed, no filters) leads with suggestions rather
  // than a catalog dump. Any query or filter switches to normal catalog search.
  const browsingDefault = !q && !level && !breadth && !term && !hasSeats;

  // Debounce free-text search so every keystroke doesn't refetch.
  React.useEffect(() => {
    const t = setTimeout(() => setQ(qInput.trim()), 300);
    return () => clearTimeout(t);
  }, [qInput]);

  // Reference data — never hard-code sessions; fetch at runtime (AGENTS.md).
  React.useEffect(() => {
    api.getSessions().then(setSessions).catch(() => {
      // Non-fatal: the Term filter just has no options.
    });
  }, []);

  // My transcript, to badge result status (completed/planned). Non-fatal — guests browse fine without it.
  React.useEffect(() => {
    api
      .getMyRecord()
      .then(setRecord)
      .catch(() => {});
  }, []);

  // Enrolled program requirements, to know what still counts toward the degree.
  React.useEffect(() => {
    if (!record) return;
    if (record.programs.length === 0) {
      setProgramDetails([]);
      setProgramsResolved(true);
      return;
    }
    let cancelled = false;
    setProgramsResolved(false);
    Promise.all(record.programs.map((p) => api.getProgram(p.code).catch(() => null))).then((res) => {
      if (cancelled) return;
      setProgramDetails(res.filter((p): p is Program => p != null));
      setProgramsResolved(true);
    });
    return () => {
      cancelled = true;
    };
  }, [record]);

  // Completed/in-progress transcript codes -- "taken" for both requirement-line
  // accounting (remainingMatches below) and exclusion filtering (the
  // suggestions effect below).
  const takenCodes = React.useMemo(() => {
    if (!record) return new Set<string>();
    return new Set(
      record.transcript.filter((t) => t.status === "completed" || t.status === "in_progress").map((t) => t.code),
    );
  }, [record]);

  // Ranked courses that fill a still-open requirement (multi-program first),
  // and a per-code "counts toward ..." phrase for any course we display.
  const remainingMatches = React.useMemo(() => {
    if (!record) return [];
    return remainingRequirementMatches(programDetails, record.requirementProgress, takenCodes);
  }, [record, programDetails, takenCodes]);

  const countsTowardByCode = React.useMemo(() => {
    const map: Record<string, string> = {};
    for (const m of remainingMatches) {
      const phrase = countsTowardPhrase(m.programs);
      if (phrase) map[m.code] = phrase;
    }
    return map;
  }, [remainingMatches]);

  // Fetch details for the top-ranked suggestions, in rank order. Only runs on
  // the default view; typing/filtering hands off to the catalog search below.
  React.useEffect(() => {
    if (!browsingDefault) return;
    if (!record) return; // keep showing the loading state until we know the programs
    if (record.programs.length > 0 && !programsResolved) return; // wait for requirement data
    const top = remainingMatches.slice(0, SUGGEST_LIMIT);
    if (top.length === 0) {
      setSuggestions([]);
      setSuggestState("ready");
      return;
    }
    let cancelled = false;
    setSuggestState("loading");
    Promise.all(
      top.map((m) =>
        api
          .getCourse(m.code)
          .then((c) => [m.code, c] as const)
          .catch(() => [m.code, null] as const),
      ),
    ).then((pairs) => {
      if (cancelled) return;
      const byCode = new Map(pairs);
      // Drop formal Calendar exclusions (e.g. ECO105Y1 excluded by a completed
      // ECO101H1/ECO102H1) -- a hard rule, checked independently of the
      // requirement-line satisfaction remainingRequirementMatches already applied.
      setSuggestions(
        top
          .map((m) => byCode.get(m.code))
          .filter((c): c is Course => Boolean(c))
          .filter((c) => !isExcludedByTaken(c.exclusions, takenCodes)),
      );
      setSuggestState("ready");
    });
    return () => {
      cancelled = true;
    };
  }, [browsingDefault, record, programsResolved, remainingMatches, takenCodes]);

  React.useEffect(() => {
    // The default view is driven by the suggestions effect above, not a
    // catalog fetch -- skip it so we never fall back to the alphabetical dump.
    if (browsingDefault) return;
    let cancelled = false;
    setState("loading");
    setError(null);
    const params: CourseSearchParams = {
      q: q || undefined,
      breadth: breadth ? BREADTH_LABELS[breadth as BreadthKey] : undefined,
      term: term || undefined,
      hasSeats: hasSeats || undefined,
    };
    // Soft client-side timeout (see SEARCH_TIMEOUT_MS) -- stop showing an
    // indefinite skeleton if the backend hasn't answered within a few
    // seconds. The underlying request keeps running; if it resolves after
    // this fires, its result still lands below and replaces this message.
    const timeoutId = window.setTimeout(() => {
      if (cancelled) return;
      setError("Course search is taking longer than expected. The Timetable Builder service may be slow or unreachable right now.");
      setState("error");
    }, SEARCH_TIMEOUT_MS);
    api
      .getCourses(params)
      .then((results) => {
        if (cancelled) return;
        window.clearTimeout(timeoutId);
        setCourses(results);
        setError(null);
        setState("ready");
      })
      .catch((e) => {
        if (cancelled) return;
        window.clearTimeout(timeoutId);
        setError(e instanceof Error ? e.message : "Failed to search courses.");
        setState("error");
      });
    return () => {
      cancelled = true;
      window.clearTimeout(timeoutId);
    };
  }, [q, breadth, term, hasSeats, retryNonce, browsingDefault]);

  // Level isn't a mock/backend filter param — applied client-side (idempotent
  // if a real backend already filtered it, since courseLevel() is deterministic).
  const filtered = React.useMemo(() => {
    if (!level) return courses;
    const lvl = Number(level);
    return courses.filter((c) => courseLevel(c.code) === lvl);
  }, [courses, level]);

  const hasFilters = Boolean(q || level || breadth || term || hasSeats);

  const clearAll = () => {
    setQInput("");
    setQ("");
    setLevel("");
    setBreadth("");
    setTerm("");
    setHasSeats(false);
  };

  const statusFor = (course: Course): "completed" | "planned" | "available" => {
    const entry = record?.transcript.find((t) => t.code === course.code);
    if (!entry) return "available";
    if (entry.status === "completed") return "completed";
    if (entry.status === "planned" || entry.status === "in_progress") return "planned";
    return "available";
  };

  const activeState: LoadState = browsingDefault ? suggestState : state;
  const activeList = browsingDefault ? suggestions : filtered;
  const searchError = browsingDefault ? null : error; // catalog-search errors don't apply to the suggestions view
  const hasPrograms = (record?.programs.length ?? 0) > 0;
  const subtitle = browsingDefault
    ? activeState === "loading"
      ? "Finding courses for you…"
      : suggestions.length > 0
        ? "Suggested for your programs, best picks first"
        : "Search by code or title to explore the catalog"
    : state === "loading"
      ? "Searching…"
      : `${filtered.length} course${filtered.length === 1 ? "" : "s"} found`;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <PageHeader title="Courses" subtitle={subtitle} />

      <FilterBar onClear={hasFilters ? clearAll : undefined}>
        <div style={{ minWidth: 220, flex: "1 1 220px" }}>
          <Input
            label="Search"
            placeholder="Code or title"
            icon="search"
            value={qInput}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setQInput(e.target.value)}
          />
        </div>
        <div style={{ minWidth: 130 }}>
          <Select
            label="Level"
            value={level}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setLevel(e.target.value)}
            options={[
              { value: "", label: "Any level" },
              ...LEVELS.map((l) => ({ value: String(l), label: `${l}+` })),
            ]}
          />
        </div>
        <div style={{ minWidth: 220 }}>
          <Select
            label="Breadth"
            value={breadth}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setBreadth(e.target.value)}
            options={[
              { value: "", label: "Any breadth" },
              ...BREADTH_KEYS.map((k) => ({ value: k, label: `${k} · ${BREADTH_LABELS[k]}` })),
            ]}
          />
        </div>
        <div style={{ minWidth: 170 }}>
          <Select
            label="Term"
            value={term}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setTerm(e.target.value)}
            options={[
              { value: "", label: "Any term" },
              ...sessions.map((s) => ({ value: s, label: sessionLabel(s) })),
            ]}
          />
        </div>
        <div style={{ paddingBottom: 9 }}>
          <Checkbox label="Has seats" checked={hasSeats} onChange={setHasSeats} />
        </div>
      </FilterBar>

      {searchError && (
        <Callout tone="danger" title="Couldn't load courses">
          <span style={{ display: "inline-flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            {error}
            <Button type="button" variant="link" size="sm" onClick={() => setRetryNonce((n) => n + 1)}>
              Retry
            </Button>
          </span>
        </Callout>
      )}

      {activeState === "loading" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }} aria-busy="true">
          {Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-lg)", padding: 16 }}
            >
              <Skeleton width={110} height={13} />
              <div style={{ marginTop: 8 }}>
                <Skeleton width="55%" height={20} />
              </div>
              <div style={{ marginTop: 10 }}>
                <Skeleton width="35%" height={13} />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Default view has suggestions but nothing to suggest: guide the student
          to the action that would produce some, rather than an empty prompt. */}
      {browsingDefault && activeState !== "loading" && activeList.length === 0 && (
        <EmptyState
          title={hasPrograms ? "Nothing left to suggest right now" : "Add a program for tailored suggestions"}
          description={
            hasPrograms
              ? "Your enrolled programs' listed courses are all accounted for. Search by code or title above to explore the full catalog."
              : "Once you add a program from Requirements, this page leads with the courses that count toward what you still need. For now, search by code or title above."
          }
          icon={hasPrograms ? "circle-check" : "graduation-cap"}
          action={
            hasPrograms ? undefined : (
              <Button variant="primary" onClick={() => navigate("/requirements")}>
                Go to Requirements
              </Button>
            )
          }
        />
      )}

      {!browsingDefault && state !== "loading" && !searchError && filtered.length === 0 && (
        <EmptyState
          title="No courses match your filters"
          description="Try widening the search: clear a filter or search a different code or title."
          icon="search"
          action={
            hasFilters ? (
              <Button variant="secondary" onClick={clearAll}>
                Clear filters
              </Button>
            ) : undefined
          }
        />
      )}

      {activeState !== "loading" && !searchError && activeList.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {activeList.map((course) => {
            const { meetTime, location, instructor } = meetingSummary(course);
            return (
              <CourseCard
                key={course.code}
                code={course.code}
                title={course.title}
                credit={course.credit}
                breadth={course.breadth.map(breadthKeyFromLabel).filter((b): b is BreadthKey => Boolean(b))}
                countsToward={countsTowardByCode[course.code]}
                fall={course.sectionCode === "F" || course.sectionCode === "Y"}
                winter={course.sectionCode === "S" || course.sectionCode === "Y"}
                status={statusFor(course)}
                meetTime={meetTime}
                location={location}
                instructor={instructor}
                onDetails={() => navigate(`/courses/${course.code}`)}
                onAdd={() => setToast(`${course.code}: plan integration is coming soon.`)}
              />
            );
          })}
        </div>
      )}

      {toast && (
        <div style={{ position: "fixed", bottom: 24, right: 24, zIndex: 200 }}>
          <Toast tone="info" onClose={() => setToast(null)}>
            {toast}
          </Toast>
        </div>
      )}
    </div>
  );
}
