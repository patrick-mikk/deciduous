import * as React from "react";
import { useNavigate, useParams } from "react-router-dom";

import {
  PageHeader,
  ProgramHeader,
  RequirementGroupCard,
  POStCombinationValidator,
  Callout,
  Card,
  EmptyState,
  Skeleton,
  Button,
} from "@/ds";
import { api, creditFromCode, isAuthError } from "@/api";
import type { EnrolledProgramRef, Program, ProgramType, RequirementGroup, RequirementProgress } from "@/api";
import { GuestCallout } from "@/components/GuestCallout";

/**
 * Screen — routed at "/programs/:code" (design/screens/03-programs-and-courses.md,
 * "Program detail").
 */

/**
 * `httpClient`'s `http()` helper (frontend/src/api/client.ts) throws a bare
 * `Error(`API error ${status}: ${bodyText}`)` on a non-2xx response -- it
 * doesn't parse the backend's `{"error": "..."}` JSON body itself. Without
 * this, every reparse failure showed the same fixed "Couldn't load..."
 * string regardless of *why* it failed (issue #1) -- a missing server-side
 * Gemini API key, a Gemini-side rejection, and an unparseable Gemini response
 * are now distinct 503/502/502 errors with distinct messages
 * (backend/data_sources/llm_grouper.py's exception hierarchy +
 * backend/api/programs.py's `reparse_requirements`), so surface the real one.
 */
function backendErrorMessage(err: unknown, fallback: string): string {
  if (!(err instanceof Error)) return fallback;
  const match = err.message.match(/^API error \d+: ([\s\S]*)$/);
  if (!match) return err.message || fallback;
  try {
    const parsed = JSON.parse(match[1]);
    if (parsed && typeof parsed.error === "string" && parsed.error.trim()) {
      return parsed.error;
    }
  } catch {
    // Body wasn't JSON (e.g. a dev-proxy plain-text 5xx) -- fall through to the raw text.
  }
  return match[1].trim() || fallback;
}

/** Same client-side approximation used on the Programs screen (design/09 §1 + §2). */
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
  } else {
    // A student can declare MORE programs than the minimal valid shape needs
    // (e.g. 4 majors) -- that's nonstandard, not invalid: a subset already
    // satisfies a combination, so say so informationally rather than
    // reporting the combination as broken (design/09-uoft-degree-rules.md §1).
    const minimum = specialists.length >= 1 ? 1 : majors.length >= 2 ? 2 : 3;
    if (programs.length > minimum) {
      const satisfiedBy =
        specialists.length >= 1
          ? "your specialist already satisfies the combination requirement"
          : majors.length >= 2
            ? `2 of your ${majors.length} majors already satisfy the 2-Major pattern`
            : "1 major + 2 minors among your programs already satisfy the Major + 2 Minors pattern";
      notes.push(
        `${programs.length} programs exceeds the standard program combinations (1 Specialist, ` +
          `2 Majors, or 1 Major + 2 Minors); UofT requires at least one valid combination among ` +
          `your programs: ${satisfiedBy}.`,
      );
    }
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

  // A program whose requirements haven't been Gemini/heuristically parsed yet
  // reports zero `appliedCourses` for every group -- NOT because the student
  // hasn't taken anything toward it, but because the parse never completed
  // (issue #1). Folding that silent zero into the shared-credit total would
  // misreport a real "0.0 distinct credits shared" that has nothing to do
  // with the student's actual course history (issue #2) -- so it's excluded
  // from the math here, and called out explicitly instead.
  const unparsed = programs.filter((p) => p.requirementsLoaded !== true);
  for (const p of unparsed) {
    notes.push(`${p.title} requirements not yet parsed. Combination check incomplete.`);
  }

  const applied = new Set<string>();
  for (const p of programs) {
    if (p.requirementsLoaded !== true) continue;
    for (const group of progressByCode[p.code] ?? []) {
      for (const code of group.appliedCourses) applied.add(code);
    }
  }
  const distinctCredits = Array.from(applied).reduce((sum, code) => sum + creditFromCode(code), 0);
  const parsedCount = programs.length - unparsed.length;
  const distinctOk = parsedCount < 2 || distinctCredits >= 12.0;
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

export default function ProgramDetail() {
  const { code = "" } = useParams<{ code: string }>();
  const navigate = useNavigate();

  const [program, setProgram] = React.useState<Program | null | undefined>(undefined); // undefined = loading
  const [loadError, setLoadError] = React.useState<string | null>(null);

  const [reparsing, setReparsing] = React.useState(false);
  const [reparseError, setReparseError] = React.useState<string | null>(null);

  const [enrolled, setEnrolled] = React.useState(false);
  const [myProgramRef, setMyProgramRef] = React.useState<EnrolledProgramRef | null>(null);
  const [enrolledPrograms, setEnrolledPrograms] = React.useState<Program[]>([]);
  const [progressByCode, setProgressByCode] = React.useState<Record<string, RequirementProgress[]>>({});
  const [comboLoading, setComboLoading] = React.useState(true);
  /** Guest nudge / failure text for the Add / Remove buttons below. */
  const [enrolNotice, setEnrolNotice] = React.useState<
    { kind: "guest"; title: string; message: string } | { kind: "error"; message: string } | null
  >(null);
  const [enrolBusy, setEnrolBusy] = React.useState(false);

  // The program itself.
  React.useEffect(() => {
    let cancelled = false;
    setProgram(undefined);
    setLoadError(null);
    api
      .getProgram(code)
      .then((p) => {
        if (!cancelled) setProgram(p);
      })
      .catch(() => {
        if (!cancelled) {
          setProgram(null);
          setLoadError("Couldn't load this program. Check your connection and try again.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [code]);

  // Enrolment state + everything the combination banner needs.
  React.useEffect(() => {
    let cancelled = false;
    setComboLoading(true);
    Promise.all([api.getMyRecord(), api.getMyRequirementProgress()])
      .then(async ([record, progress]) => {
        if (cancelled) return;
        setProgressByCode(progress);
        setMyProgramRef(record.programs.find((p) => p.code === code) ?? null);
        setEnrolled(record.programs.some((p) => p.code === code));
        const resolved = await Promise.all(record.programs.map((p) => api.getProgram(p.code)));
        if (cancelled) return;
        setEnrolledPrograms(resolved.filter((p): p is Program => p != null));
      })
      .catch(() => {
        // Non-fatal: the combination banner just stays hidden.
      })
      .finally(() => {
        if (!cancelled) setComboLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [code]);

  function handleReparse() {
    if (!program) return;
    setReparsing(true);
    setReparseError(null);
    api
      .reparseProgramRequirements(program.code)
      .then((groups) => {
        setProgram((prev) => (prev ? { ...prev, completionRequirements: groups, requirementsLoaded: true } : prev));
      })
      .catch((err: unknown) =>
        setReparseError(
          backendErrorMessage(err, "Couldn't load the full requirement breakdown. Try again."),
        ),
      )
      .finally(() => setReparsing(false));
  }

  /**
   * Enrol / unenrol. These used to flip `enrolled` in local state ONLY, never
   * calling the API — so the header switched to "Enrolled" and the change
   * vanished on the next reload, for signed-in students as much as guests.
   * They now go through the same `api.addMyProgram`/`removeMyProgram` that
   * Programs.tsx uses, applied optimistically and rolled back on failure, with
   * a guest's 401 reported as the shared sign-up nudge rather than as a
   * success (or as a raw `API error 401:` string).
   */
  async function handleAdd() {
    if (!program || enrolBusy) return;
    const target = program;
    setEnrolBusy(true);
    setEnrolNotice(null);
    setEnrolled(true);
    setEnrolledPrograms((prev) => (prev.some((p) => p.code === target.code) ? prev : [...prev, target]));
    try {
      await api.addMyProgram(target.code);
    } catch (err: unknown) {
      setEnrolled(false);
      setEnrolledPrograms((prev) => prev.filter((p) => p.code !== target.code));
      setEnrolNotice(
        isAuthError(err)
          ? {
              kind: "guest",
              title: "Create an account to add programs",
              message: `Anyone can read ${target.code}'s requirements, but adding it to your degree audit needs somewhere to save it.`,
            }
          : {
              kind: "error",
              message: backendErrorMessage(
                err,
                `Couldn't add ${target.code}. It may conflict with a program you're already enrolled in.`,
              ),
            },
      );
    } finally {
      setEnrolBusy(false);
    }
  }

  async function handleRemove() {
    if (!program || enrolBusy) return;
    const target = program;
    setEnrolBusy(true);
    setEnrolNotice(null);
    setEnrolled(false);
    setEnrolledPrograms((prev) => prev.filter((p) => p.code !== target.code));
    try {
      await api.removeMyProgram(target.code);
    } catch (err: unknown) {
      setEnrolled(true);
      setEnrolledPrograms((prev) => (prev.some((p) => p.code === target.code) ? prev : [...prev, target]));
      setEnrolNotice(
        isAuthError(err)
          ? {
              kind: "guest",
              title: "Create an account to manage programs",
              message: "You're browsing as a guest, so there's no saved enrolment to remove yet.",
            }
          : { kind: "error", message: backendErrorMessage(err, `Couldn't remove ${target.code}. Try again.`) },
      );
    } finally {
      setEnrolBusy(false);
    }
  }

  // ---- Loading / not-found / error states ----------------------------------
  if (program === undefined) {
    return (
      <>
        <PageHeader title="Program" breadcrumbs={[{ label: "Programs", onClick: () => navigate("/programs") }, { label: "…" }]} />
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div style={{ display: "flex", gap: 20 }}>
            <Skeleton width={64} height={64} radius="50%" />
            <div style={{ flex: 1 }}>
              <Skeleton width={120} height={14} style={{ marginBottom: 10 }} />
              <Skeleton width="50%" height={28} style={{ marginBottom: 8 }} />
              <Skeleton width="30%" height={16} />
            </div>
          </div>
          <Skeleton height={80} />
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} height={64} />
          ))}
        </div>
      </>
    );
  }

  if (program === null) {
    return (
      <>
        <PageHeader title="Program" breadcrumbs={[{ label: "Programs", onClick: () => navigate("/programs") }]} />
        {loadError ? (
          <Callout
            tone="danger"
            title="Couldn't load this program"
            action={
              <Button variant="secondary" size="sm" onClick={() => navigate(0)}>
                Retry
              </Button>
            }
          >
            {loadError}
          </Callout>
        ) : (
          <EmptyState
            icon="search-x"
            title="Program not found"
            description={`No program matches "${code}". It may have been renamed or retired.`}
            action={<Button onClick={() => navigate("/programs")}>Back to Programs</Button>}
          />
        )}
      </>
    );
  }

  const combo = evaluateCombination(enrolledPrograms, progressByCode);
  const myProgress = enrolled ? progressByCode[program.code] ?? [] : [];
  // The header's earned/total come from the ONE authoritative summary
  // (`record.programs[]` -> `_audit.program_progress_summary`), the same
  // engine the Dashboard and "My Programs" cards use — NOT a per-group sum of
  // `myProgress` (that double-counts courses shared across nested groups). The
  // per-group breakdown below still renders each group's own earned/required.

  function progressFor(group: RequirementGroup) {
    return myProgress.find((p) => p.label === group.heading);
  }

  return (
    <>
      <PageHeader
        title={program.title}
        breadcrumbs={[{ label: "Programs", onClick: () => navigate("/programs") }, { label: program.code }]}
      />

      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        {/* The screen's single highlighted summary card (modernized-ACORN):
            a teal left accent on the program hero only. */}
        <Card style={{ borderLeft: "3px solid var(--accent)" }}>
          <ProgramHeader
            code={program.code}
            name={program.title}
            programType={(program.programType || "major") as ProgramType}
            department={program.department}
            totalCredits={myProgramRef?.totalCredits ?? program.totalCredits}
            earned={enrolled ? myProgramRef?.earnedCredits ?? 0 : undefined}
            enrolmentRequirements={program.enrolmentRequirements || undefined}
            needsReparse={!program.requirementsLoaded}
            reparsing={reparsing}
            onReparse={handleReparse}
            onAdd={enrolled ? undefined : handleAdd}
            enrolled={enrolled}
          />
          {enrolled && (
            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 8 }}>
              <Button variant="ghost" size="sm" icon="x" onClick={handleRemove}>
                Remove from my programs
              </Button>
            </div>
          )}
        </Card>

        {enrolNotice?.kind === "guest" && (
          <GuestCallout title={enrolNotice.title}>{enrolNotice.message}</GuestCallout>
        )}
        {enrolNotice?.kind === "error" && (
          <Callout tone="danger" title="Couldn't update your programs">
            {enrolNotice.message}
          </Callout>
        )}

        {reparseError && <Callout tone="danger" title="Requirement parsing failed">{reparseError}</Callout>}

        {!comboLoading && enrolled && (
          <POStCombinationValidator valid={combo.valid} message={combo.message} notes={combo.notes} />
        )}

        {program.completionRequirements.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {program.completionRequirements.map((group, i) =>
              group.isNote ? (
                <Callout key={i} tone="info" title={group.heading || "Note"}>
                  {group.notes}
                </Callout>
              ) : (
                <RequirementGroupCard
                  key={i}
                  heading={group.heading || "Requirements"}
                  earned={progressFor(group)?.earned ?? 0}
                  required={group.credits}
                  note={group.notes || undefined}
                  courses={group.courses.map((c) => ({
                    code: c.code,
                    credits: c.credits,
                    note: c.notes || undefined,
                    status: progressFor(group)?.appliedCourses.includes(c.code) ? "complete" : "available",
                  }))}
                  onCourseClick={(course: { code: string }) => navigate(`/courses/${course.code}`)}
                />
              ),
            )}
          </div>
        ) : program.requirementsLoaded ? (
          <EmptyState
            icon="list-checks"
            title="No requirement groups"
            description="This program has no structured requirement groups on file."
          />
        ) : (
          <Callout tone="info" title="Full requirement breakdown not yet parsed">
            {program.rawCompletionText ||
              "Detailed requirement groups haven't been generated for this program yet."}
            {" "}
            Use "Load full requirements (Gemini)" above to generate them.
          </Callout>
        )}
      </div>
    </>
  );
}
