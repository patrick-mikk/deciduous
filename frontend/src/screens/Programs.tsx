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
import { api, creditFromCode, isAuthError } from "@/api";
import type { EnrolledProgramRef, Program, ProgramType, RequirementProgress } from "@/api";
import { GuestCallout } from "@/components/GuestCallout";

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

/** Outcome of an add/remove/reorder attempt, when it's worth telling the user
 * about. `guest` is the account-optional 401 case (friendly nudge, info tone);
 * `error` is a genuine failure (danger tone). */
type ActionNotice =
  | { kind: "guest"; title: string; message: string }
  | { kind: "error"; title: string; message: string };

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
    notes.push(`Only ${distinctCredits.toFixed(1)} distinct credits shared across programs. Need ≥12.0.`);
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
    message: valid ? `Valid combination: ${shapeLabel}` : "Program combination needs attention",
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
  // Authoritative per-program completion, keyed by code, from `GET /api/me`'s
  // `programs[]` (`_audit.program_progress_summary`) — the single source every
  // program card shares, so "My programs" summaries can't disagree with a
  // program's own detail page.
  const [summaryByCode, setSummaryByCode] = React.useState<Record<string, EnrolledProgramRef>>({});
  const [myPrograms, setMyPrograms] = React.useState<Program[]>([]);
  const [myLoading, setMyLoading] = React.useState(true);
  const [myError, setMyError] = React.useState<string | null>(null);
  /**
   * Result of the last add/remove/reorder attempt. Rendered ABOVE the tab
   * switch (not inside the "My programs" branch) — the previous `myActionError`
   * Callout lived only in that branch, so an "Add" pressed on the *Browse* tab
   * set it and then rendered nothing at all: the reported "clicking Add does
   * nothing" bug. Every action a guest can reach from Browse must report back
   * in the view they're actually looking at.
   */
  const [actionNotice, setActionNotice] = React.useState<ActionNotice | null>(null);
  /** No session at all — every `/api/me/*` call 401s. Not an error: accounts
   * are optional (see App.tsx's "no route guard anywhere" note). */
  const [isGuest, setIsGuest] = React.useState(false);
  const [dragCode, setDragCode] = React.useState<string | null>(null);
  // Scopes the aria-label lookup `focusPriorityButton` does after a keyboard
  // reorder — see its comment below for why a DOM query is needed at all.
  const myListRef = React.useRef<HTMLOListElement | null>(null);

  // Enrolled programs (in the student's saved order, `GET /api/me/programs`)
  // + requirement progress, once — drives every card's enrolled/Add-vs-Remove
  // state and the "My programs" tab.
  React.useEffect(() => {
    let cancelled = false;
    setMyLoading(true);
    Promise.all([api.getMyPrograms(), api.getMyRequirementProgress(), api.getMyRecord()])
      .then(([enrolled, progress, record]) => {
        if (cancelled) return;
        setProgressByCode(progress);
        setSummaryByCode(Object.fromEntries(record.programs.map((p) => [p.code, p])));
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
      .catch((err: unknown) => {
        if (cancelled) return;
        // A guest has no session, so all three /api/me calls 401 together.
        // That's the expected signed-out state, not a load failure — show the
        // sign-up nudge instead of a red "couldn't load" banner.
        if (isAuthError(err)) {
          setIsGuest(true);
          setMyError(null);
        } else {
          setMyError("Couldn't load your enrolled programs.");
        }
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
      .getAllPrograms()
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
    setActionNotice(null);
    try {
      await api.addMyProgram(program.code);
      setMyPrograms((prev) => (prev.some((p) => p.code === program.code) ? prev : [...prev, program]));
    } catch (err: unknown) {
      if (isAuthError(err)) {
        setIsGuest(true);
        setActionNotice({
          kind: "guest",
          title: "Create an account to add programs",
          message: `Browsing the catalog doesn't need an account, but ${program.code} has to be saved to one before it can count toward your degree audit.`,
        });
      } else {
        setActionNotice({
          kind: "error",
          title: "Couldn't update your programs",
          message: `Couldn't add ${program.code}. It may conflict with a program you're already enrolled in.`,
        });
      }
    }
  }

  async function removeProgram(code: string) {
    setActionNotice(null);
    try {
      await api.removeMyProgram(code);
      setMyPrograms((prev) => prev.filter((p) => p.code !== code));
    } catch (err: unknown) {
      if (isAuthError(err)) {
        setIsGuest(true);
        setActionNotice({
          kind: "guest",
          title: "Create an account to manage programs",
          message: "You're browsing as a guest, so there are no saved programs to remove yet.",
        });
      } else {
        setActionNotice({ kind: "error", title: "Couldn't update your programs", message: `Couldn't remove ${code}. Try again.` });
      }
    }
  }

  // Optimistic reorder: apply locally first (drag/keyboard both feel instant),
  // then persist; roll back to the prior order if the save fails.
  async function persistOrder(next: Program[]) {
    const previous = myPrograms;
    setMyPrograms(next);
    setActionNotice(null);
    try {
      await api.reorderMyPrograms(next.map((p) => p.code));
    } catch (err: unknown) {
      setMyPrograms(previous);
      if (isAuthError(err)) {
        setIsGuest(true);
        setActionNotice({
          kind: "guest",
          title: "Create an account to save program priority",
          message: "Program order is part of your saved record, so it needs an account to stick.",
        });
      } else {
        setActionNotice({ kind: "error", title: "Couldn't update your programs", message: "Couldn't save the new order. Try again." });
      }
    }
  }

  /** Human-readable name for a "Move X up/down" aria-label — the program
   * title reads better to a screen reader than the raw code. */
  function programDisplayName(program: Program): string {
    return program.title || program.code;
  }

  /**
   * `IconButton` (ds) doesn't forward a `ref` or pass through arbitrary
   * props, so the only stable hook into its rendered `<button>` from this
   * screen is the `aria-label` it already renders — used here, scoped to
   * `myListRef`, to move focus after a keyboard reorder (see `moveProgram`).
   */
  function focusPriorityButton(program: Program, direction: "up" | "down") {
    const label = `Move ${programDisplayName(program)} ${direction} in priority`;
    const button = myListRef.current?.querySelector<HTMLButtonElement>(
      `button[aria-label="${CSS.escape(label)}"]`,
    );
    button?.focus();
  }

  /** Keyboard/touch alternative to dragging (also usable with a mouse). */
  function moveProgram(code: string, direction: -1 | 1) {
    const index = myPrograms.findIndex((p) => p.code === code);
    const target = index + direction;
    if (index < 0 || target < 0 || target >= myPrograms.length) return;
    const next = [...myPrograms];
    [next[index], next[target]] = [next[target], next[index]];
    persistOrder(next);

    // The IconButton the user just activated disables itself once the item
    // lands at that end of the list (top for "up", bottom for "down") — a
    // disabled button can't hold focus, so without this the browser drops
    // keyboard focus to <body> right after the move. Redirect focus to the
    // opposite-direction button on the same row instead, which stays enabled
    // (the list always has >=2 programs whenever a move is possible).
    const reachedTop = direction === -1 && target === 0;
    const reachedBottom = direction === 1 && target === next.length - 1;
    if (reachedTop || reachedBottom) {
      const moved = next[target];
      const oppositeDirection = direction === -1 ? "down" : "up";
      requestAnimationFrame(() => focusPriorityButton(moved, oppositeDirection));
    }
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
    // One source of truth — the server-computed summary — never a per-group
    // sum of `earned` (double-counts shared courses) or a raw 0.0 total.
    const summary = summaryByCode[program.code];
    if (!summary) return undefined;
    return { earned: summary.earnedCredits, total: summary.totalCredits };
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
        {/* Rendered OUTSIDE the tab switch on purpose: "Add" lives on the
            Browse tab, so its result has to be visible there too (see
            `actionNotice`'s declaration). */}
        {actionNotice?.kind === "guest" && (
          <GuestCallout title={actionNotice.title}>{actionNotice.message}</GuestCallout>
        )}
        {actionNotice?.kind === "error" && (
          <Callout tone="danger" title={actionNotice.title}>
            {actionNotice.message}
          </Callout>
        )}

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
              isGuest ? (
                // A guest has no saved record at all — say so plainly instead
                // of implying they simply haven't picked anything yet.
                <GuestCallout title="Create an account to keep a program list">
                  You're browsing as a guest. Search and requirement breakdowns are all open to you, but a saved list
                  of Specialists, Majors, and Minors needs an account.
                </GuestCallout>
              ) : (
                <EmptyState
                  icon="graduation-cap"
                  title="No programs yet"
                  description="Add a Specialist, Major, or Minor from Browse to start tracking your degree combination."
                  action={<Button onClick={() => setTab("browse")}>Browse programs</Button>}
                />
              )
            ) : (
              !myError && (
                // A native <ol> conveys list membership + position ("item 2
                // of 3") to screen readers on its own — `aria-live` still
                // announces reorders without needing `role="status"`, which
                // would otherwise replace the implicit list role.
                <ol
                  ref={myListRef}
                  aria-live="polite"
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: 12,
                    listStyle: "none",
                    margin: 0,
                    padding: 0,
                  }}
                >
                  {myPrograms.map((p, i) => {
                    const cr = creditsFor(p);
                    const name = programDisplayName(p);
                    return (
                      <li
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
                            label={`Move ${name} up in priority`}
                            size={24}
                            disabled={i === 0}
                            onClick={() => moveProgram(p.code, -1)}
                          />
                          <IconButton
                            icon="chevron-down"
                            label={`Move ${name} down in priority`}
                            size={24}
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
                      </li>
                    );
                  })}
                </ol>
              )
            )}
          </>
        )}
      </div>
    </>
  );
}
