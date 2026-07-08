import * as React from "react";
import { useNavigate } from "react-router-dom";

import {
  PageHeader,
  Tabs,
  FilterBar,
  Input,
  Select,
  Button,
  IconButton,
  ProgramCard,
  Skeleton,
  EmptyState,
  Callout,
  POStCombinationValidator,
} from "@/ds";
import { api, creditFromCode } from "@/api";
import type { Program, ProgramType, RequirementProgress } from "@/api";

/**
 * Screen — routed at "/programs" (design/screens/03-programs-and-courses.md,
 * "Program search / browse" + "My programs").
 *
 * `/programs/mine` isn't in the route table (frontend/src/App.tsx owns
 * routing, out of this screen's ownership), so "My programs" is folded in
 * here as the doc's own `Tabs: [ Browse ] [ My programs ]` — same content,
 * no extra route needed.
 */

const PAGE_SIZE = 20;

type TabKey = "browse" | "mine";

const TYPE_OPTIONS: { value: ProgramType; label: string }[] = [
  { value: "", label: "All types" },
  { value: "specialist", label: "Specialist" },
  { value: "major", label: "Major" },
  { value: "minor", label: "Minor" },
];

/**
 * design/09-uoft-degree-rules.md §1 + §2: valid combo shapes (1 Specialist,
 * OR 2 Majors, OR 1 Major + 2 Minors), "one-type-per-subject", and the
 * ≥12.0-distinct-credits rule. A lightweight client-side approximation for
 * the UI banner — the backend validator is authoritative (see AGENTS.md).
 */
function evaluateCombination(
  programs: Program[],
  progressByCode: Record<string, RequirementProgress[]>,
): { valid: boolean; message: string; notes: string[] } {
  if (programs.length === 0) {
    return { valid: true, message: "No programs enrolled yet", notes: [] };
  }
  const notes: string[] = [];
  const specialists = programs.filter((p) => p.programType === "specialist");
  const majors = programs.filter((p) => p.programType === "major");
  const minors = programs.filter((p) => p.programType === "minor");
  const shapeValid = specialists.length >= 1 || majors.length >= 2 || (majors.length >= 1 && minors.length >= 2);
  if (!shapeValid) {
    notes.push("The degree program requirement needs 1 Specialist, 2 Majors, or 1 Major + 2 Minors.");
  }

  const bySubject = new Map<string, Program[]>();
  for (const p of programs) {
    const subject = p.code.match(/(\d{4})[A-Z]?$/)?.[1] ?? p.code;
    bySubject.set(subject, [...(bySubject.get(subject) ?? []), p]);
  }
  let oneTypePerSubject = true;
  for (const group of bySubject.values()) {
    if (group.length > 1) {
      oneTypePerSubject = false;
      notes.push(`Same subject area in multiple programs: ${group.map((p) => p.code).join(" / ")}.`);
    }
  }

  const applied = new Set<string>();
  for (const p of programs) {
    for (const group of progressByCode[p.code] ?? []) {
      for (const code of group.appliedCourses) applied.add(code);
    }
  }
  const distinctCredits = Array.from(applied).reduce((sum, code) => sum + creditFromCode(code), 0);
  const distinctOk = programs.length < 2 || distinctCredits >= 12.0;
  if (!distinctOk) {
    notes.push(`Only ${distinctCredits.toFixed(1)} distinct credits shared across programs — need ≥12.0.`);
  }

  const valid = shapeValid && oneTypePerSubject && distinctOk;
  const shapeLabel =
    specialists.length >= 1
      ? "Specialist"
      : majors.length >= 2
        ? `${majors.length} Majors`
        : majors.length >= 1 && minors.length >= 2
          ? "Major + 2 Minors"
          : `${programs.length} program${programs.length === 1 ? "" : "s"}`;
  return {
    valid,
    message: valid ? `Valid combination — ${shapeLabel}` : "Program combination needs attention",
    notes,
  };
}

export default function Programs() {
  const navigate = useNavigate();
  const [tab, setTab] = React.useState<TabKey>("browse");

  // ---- Browse -------------------------------------------------------------
  const [q, setQ] = React.useState("");
  const [type, setType] = React.useState<ProgramType>("");
  const [subject, setSubject] = React.useState("");
  const [subjectOptions, setSubjectOptions] = React.useState<string[]>([]);
  const [page, setPage] = React.useState(1);
  const [programs, setPrograms] = React.useState<Program[]>([]);
  const [hasMore, setHasMore] = React.useState(false);
  const [loading, setLoading] = React.useState(true);
  const [loadingMore, setLoadingMore] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // ---- My programs (enrolled list, in saved order, + per-program progress) -
  const [progressByCode, setProgressByCode] = React.useState<Record<string, RequirementProgress[]>>({});
  const [myPrograms, setMyPrograms] = React.useState<Program[]>([]);
  const [myLoading, setMyLoading] = React.useState(true);
  const [myError, setMyError] = React.useState<string | null>(null);
  const [myActionError, setMyActionError] = React.useState<string | null>(null);
  const [dragCode, setDragCode] = React.useState<string | null>(null);

  // Enrolled programs (in the student's saved order, `GET /api/me/programs`)
  // + requirement progress, once — drives every card's enrolled/Add-vs-Remove
  // state and the "My programs" tab.
  React.useEffect(() => {
    let cancelled = false;
    setMyLoading(true);
    Promise.all([api.getMyPrograms(), api.getMyRequirementProgress()])
      .then(([enrolled, progress]) => {
        if (cancelled) return;
        setProgressByCode(progress);
        setMyError(null);
        // allSettled: one enrolled program's catalog lookup failing (stale
        // code, transient network blip) shouldn't take down the whole list —
        // show what resolved and drop the rest, rather than erroring out.
        return Promise.allSettled(enrolled.map((p) => api.getProgram(p.code))).then((results) => {
          if (cancelled) return;
          setMyPrograms(
            results
              .map((r) => (r.status === "fulfilled" ? r.value : null))
              .filter((p): p is Program => p !== null),
          );
        });
      })
      .catch(() => {
        if (!cancelled) setMyError("Couldn't load your enrolled programs.");
      })
      .finally(() => {
        if (!cancelled) setMyLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Subject filter options: distinct departments across the unfiltered catalog.
  React.useEffect(() => {
    let cancelled = false;
    api
      .getPrograms({})
      .then((all) => {
        if (cancelled) return;
        setSubjectOptions(Array.from(new Set(all.map((p) => p.department).filter(Boolean))).sort());
      })
      .catch(() => {
        // Non-fatal: the subject dropdown just stays at "All subjects".
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const fetchPrograms = React.useCallback(
    (targetPage: number, append: boolean) => {
      (append ? setLoadingMore : setLoading)(true);
      setError(null);
      api
        .getPrograms({ q: q || undefined, type: type || undefined, subject: subject || undefined, page: targetPage })
        .then((results) => {
          setPrograms((prev) => (append ? [...prev, ...results] : results));
          setHasMore(results.length >= PAGE_SIZE);
        })
        .catch(() => setError("Couldn't load programs. Check your connection and try again."))
        .finally(() => (append ? setLoadingMore : setLoading)(false));
    },
    [q, type, subject],
  );

  React.useEffect(() => {
    setPage(1);
    // Small debounce on free-text search only; type/subject changes refetch immediately.
    const handle = setTimeout(() => fetchPrograms(1, false), q ? 300 : 0);
    return () => clearTimeout(handle);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, type, subject]);

  function loadMore() {
    const next = page + 1;
    setPage(next);
    fetchPrograms(next, true);
  }

  async function addProgram(program: Program) {
    setMyActionError(null);
    try {
      await api.addMyProgram(program.code);
      setMyPrograms((prev) => (prev.some((p) => p.code === program.code) ? prev : [...prev, program]));
    } catch {
      setMyActionError(`Couldn't add ${program.code}. It may conflict with a program you're already enrolled in.`);
    }
  }

  async function removeProgram(code: string) {
    setMyActionError(null);
    try {
      await api.removeMyProgram(code);
      setMyPrograms((prev) => prev.filter((p) => p.code !== code));
    } catch {
      setMyActionError(`Couldn't remove ${code}. Try again.`);
    }
  }

  // Optimistic reorder: apply locally first (drag/keyboard both feel instant),
  // then persist; roll back to the prior order if the save fails.
  async function persistOrder(next: Program[]) {
    const previous = myPrograms;
    setMyPrograms(next);
    setMyActionError(null);
    try {
      await api.reorderMyPrograms(next.map((p) => p.code));
    } catch {
      setMyPrograms(previous);
      setMyActionError("Couldn't save the new order. Try again.");
    }
  }

  /** Keyboard/touch alternative to dragging (also usable with a mouse). */
  function moveProgram(code: string, direction: -1 | 1) {
    const index = myPrograms.findIndex((p) => p.code === code);
    const target = index + direction;
    if (index < 0 || target < 0 || target >= myPrograms.length) return;
    const next = [...myPrograms];
    [next[index], next[target]] = [next[target], next[index]];
    persistOrder(next);
  }

  function dropProgramOn(code: string) {
    if (!dragCode || dragCode === code) {
      setDragCode(null);
      return;
    }
    const from = myPrograms.findIndex((p) => p.code === dragCode);
    const to = myPrograms.findIndex((p) => p.code === code);
    setDragCode(null);
    if (from < 0 || to < 0) return;
    const next = [...myPrograms];
    const [moved] = next.splice(from, 1);
    next.splice(to, 0, moved);
    persistOrder(next);
  }

  function clearFilters() {
    setQ("");
    setType("");
    setSubject("");
  }

  const myProgramCodes = React.useMemo(() => new Set(myPrograms.map((p) => p.code)), [myPrograms]);
  const combo = evaluateCombination(myPrograms, progressByCode);
  const filtersActive = Boolean(q || type || subject);

  function creditsFor(program: Program): { earned: number; total: number } | undefined {
    const groups = progressByCode[program.code];
    if (!groups) return undefined;
    return { earned: groups.reduce((s, g) => s + g.earned, 0), total: program.totalCredits };
  }

  return (
    <>
      <PageHeader
        title="Programs"
        subtitle="Browse Specialists, Majors, and Minors, or manage the ones you've enrolled in."
      />
      <Tabs
        tabs={[
          { value: "browse", label: "Browse" },
          { value: "mine", label: `My programs${myPrograms.length ? ` (${myPrograms.length})` : ""}` },
        ]}
        active={tab}
        onChange={(v: TabKey) => setTab(v)}
      />

      <div style={{ marginTop: 20, display: "flex", flexDirection: "column", gap: 16 }}>
        {tab === "browse" ? (
          <>
            <FilterBar onClear={filtersActive ? clearFilters : undefined}>
              <div style={{ minWidth: 240, flex: "1 1 260px" }}>
                <Input
                  label="Search"
                  icon="search"
                  placeholder="Program name or code"
                  value={q}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setQ(e.target.value)}
                />
              </div>
              <div style={{ minWidth: 160 }}>
                <Select
                  label="Type"
                  value={type}
                  onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setType(e.target.value as ProgramType)}
                  options={TYPE_OPTIONS}
                />
              </div>
              <div style={{ minWidth: 200 }}>
                <Select
                  label="Subject"
                  value={subject}
                  onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSubject(e.target.value)}
                  options={[
                    { value: "", label: "All subjects" },
                    ...subjectOptions.map((s) => ({ value: s, label: s })),
                  ]}
                />
              </div>
            </FilterBar>

            {error && (
              <Callout
                tone="danger"
                title="Couldn't load programs"
                action={
                  <Button variant="secondary" size="sm" onClick={() => fetchPrograms(1, false)}>
                    Retry
                  </Button>
                }
              >
                {error}
              </Callout>
            )}

            {loading ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {Array.from({ length: 4 }).map((_, i) => (
                  <div
                    key={i}
                    style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-lg)", padding: 18 }}
                  >
                    <Skeleton width={70} height={16} style={{ marginBottom: 10 }} />
                    <Skeleton width="55%" height={22} style={{ marginBottom: 8 }} />
                    <Skeleton width="35%" height={14} />
                  </div>
                ))}
              </div>
            ) : !error && programs.length === 0 ? (
              <EmptyState
                icon="search-x"
                title="No programs found"
                description={
                  filtersActive
                    ? "Try a different search term or clear your filters."
                    : "The program catalog is empty right now."
                }
                action={
                  filtersActive ? (
                    <Button variant="secondary" onClick={clearFilters}>
                      Clear filters
                    </Button>
                  ) : undefined
                }
              />
            ) : (
              !error && (
                <>
                  <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                    {programs.map((p) => {
                      const cr = creditsFor(p);
                      return (
                        <ProgramCard
                          key={p.code}
                          code={p.code}
                          name={p.title}
                          programType={p.programType || "major"}
                          department={p.department}
                          earned={cr?.earned}
                          total={cr?.total}
                          enrolled={myProgramCodes.has(p.code)}
                          onView={() => navigate(`/programs/${p.code}`)}
                          onAdd={() => addProgram(p)}
                          onRemove={() => removeProgram(p.code)}
                        />
                      );
                    })}
                  </div>
                  {hasMore && (
                    <div style={{ display: "flex", justifyContent: "center" }}>
                      <Button variant="secondary" loading={loadingMore} onClick={loadMore}>
                        Load more
                      </Button>
                    </div>
                  )}
                </>
              )
            )}
          </>
        ) : (
          <>
            {myError && (
              <Callout tone="danger" title="Couldn't load your programs">
                {myError}
              </Callout>
            )}
            {myActionError && (
              <Callout tone="danger" title="Couldn't update your programs">
                {myActionError}
              </Callout>
            )}
            {!myError && myPrograms.length > 0 && (
              <POStCombinationValidator valid={combo.valid} message={combo.message} notes={combo.notes} />
            )}
            {myLoading ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {Array.from({ length: 2 }).map((_, i) => (
                  <Skeleton key={i} height={78} />
                ))}
              </div>
            ) : !myError && myPrograms.length === 0 ? (
              <EmptyState
                icon="graduation-cap"
                title="No programs yet"
                description="Add a Specialist, Major, or Minor from Browse to start tracking your degree combination."
                action={<Button onClick={() => setTab("browse")}>Browse programs</Button>}
              />
            ) : (
              !myError && (
                <div
                  style={{ display: "flex", flexDirection: "column", gap: 12 }}
                  role="status"
                  aria-live="polite"
                >
                  {myPrograms.map((p, i) => {
                    const cr = creditsFor(p);
                    return (
                      <div
                        key={p.code}
                        draggable
                        onDragStart={() => setDragCode(p.code)}
                        onDragOver={(e) => e.preventDefault()}
                        onDrop={() => dropProgramOn(p.code)}
                        onDragEnd={() => setDragCode(null)}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 4,
                          cursor: "grab",
                          opacity: dragCode === p.code ? 0.5 : 1,
                        }}
                      >
                        <div style={{ display: "flex", flexDirection: "column" }}>
                          <IconButton
                            icon="chevron-up"
                            label={`Move ${p.code} up in priority`}
                            disabled={i === 0}
                            onClick={() => moveProgram(p.code, -1)}
                          />
                          <IconButton
                            icon="chevron-down"
                            label={`Move ${p.code} down in priority`}
                            disabled={i === myPrograms.length - 1}
                            onClick={() => moveProgram(p.code, 1)}
                          />
                        </div>
                        <div style={{ flex: 1 }}>
                          <ProgramCard
                            code={p.code}
                            name={p.title}
                            programType={p.programType || "major"}
                            department={p.department}
                            earned={cr?.earned}
                            total={cr?.total}
                            enrolled
                            onView={() => navigate(`/programs/${p.code}`)}
                            onRemove={() => removeProgram(p.code)}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )
            )}
          </>
        )}
      </div>
    </>
  );
}
