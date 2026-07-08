import * as React from "react";
import { useNavigate, useParams } from "react-router-dom";

import {
  PageHeader,
  ProgramHeader,
  RequirementGroupCard,
  POStCombinationValidator,
  Callout,
  EmptyState,
  Skeleton,
  Button,
} from "@/ds";
import { api, creditFromCode } from "@/api";
import type { Program, ProgramType, RequirementGroup, RequirementProgress } from "@/api";

/**
 * Screen — routed at "/programs/:code" (design/screens/03-programs-and-courses.md,
 * "Program detail").
 */

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

export default function ProgramDetail() {
  const { code = "" } = useParams<{ code: string }>();
  const navigate = useNavigate();

  const [program, setProgram] = React.useState<Program | null | undefined>(undefined); // undefined = loading
  const [loadError, setLoadError] = React.useState<string | null>(null);

  const [reparsing, setReparsing] = React.useState(false);
  const [reparseError, setReparseError] = React.useState<string | null>(null);

  const [enrolled, setEnrolled] = React.useState(false);
  const [enrolledPrograms, setEnrolledPrograms] = React.useState<Program[]>([]);
  const [progressByCode, setProgressByCode] = React.useState<Record<string, RequirementProgress[]>>({});
  const [comboLoading, setComboLoading] = React.useState(true);

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
      .catch(() => setReparseError("Couldn't load the full requirement breakdown. Try again."))
      .finally(() => setReparsing(false));
  }

  function handleAdd() {
    if (!program) return;
    setEnrolled(true);
    setEnrolledPrograms((prev) => (prev.some((p) => p.code === program.code) ? prev : [...prev, program]));
  }

  function handleRemove() {
    if (!program) return;
    setEnrolled(false);
    setEnrolledPrograms((prev) => prev.filter((p) => p.code !== program.code));
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
  const earnedCredits = myProgress.reduce((s, g) => s + g.earned, 0);

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
        <ProgramHeader
          code={program.code}
          name={program.title}
          programType={(program.programType || "major") as ProgramType}
          department={program.department}
          totalCredits={program.totalCredits}
          earned={enrolled ? earnedCredits : undefined}
          enrolmentRequirements={program.enrolmentRequirements || undefined}
          needsReparse={!program.requirementsLoaded}
          reparsing={reparsing}
          onReparse={handleReparse}
          onAdd={enrolled ? undefined : handleAdd}
          enrolled={enrolled}
        />
        {enrolled && (
          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: -12 }}>
            <Button variant="ghost" size="sm" icon="x" onClick={handleRemove}>
              Remove from my programs
            </Button>
          </div>
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
