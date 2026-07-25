import * as React from "react";
import { useNavigate, useParams } from "react-router-dom";

import {
  Button,
  Callout,
  Card,
  CourseDetailPanel,
  CreditMeter,
  Drawer,
  EmptyState,
  PageHeader,
  ProgramHeader,
  RequirementGroupCard,
  Skeleton,
  Switch,
  Toast,
} from "@/ds";
import type { CourseDetail } from "@/ds";
import { api, courseLevel, creditFromCode } from "@/api";
import type { Course, Program, RequirementGroup, RequirementProgress, TranscriptCourse } from "@/api";

/**
 * Program requirement detail — routed at "/requirements/:code"
 * (design/screens/02-dashboard-and-progress.md "Program requirements detail").
 *
 * ProgramHeader (on-demand Gemini requirement grouping, async spinner + toast)
 * + an "only what's left" toggle + a legend + one RequirementGroupCard per
 * group (per-course credits/notes/status), plus each enrolled program's
 * 300+/400 upper-level sub-progress (design/09 §2 per-type minimums).
 */

type ChipStatus = "complete" | "planned" | "available" | "blocked";

interface GroupCourseVM {
  code: string;
  credits?: number;
  status: ChipStatus;
  note?: string;
}

interface GroupVM {
  key: string;
  heading: string;
  required: number;
  earned: number;
  note?: string;
  courses: GroupCourseVM[];
}

// design/09 §2 — Specialist ≥4.0 at 300+ (≥1.0 at 400) · Major ≥2.0 (≥0.5 at 400) · Minor ≥1.0.
const UPPER_LEVEL_MINIMUMS: Record<string, { l300: number; l400: number } | undefined> = {
  specialist: { l300: 4.0, l400: 1.0 },
  major: { l300: 2.0, l400: 0.5 },
  minor: { l300: 1.0, l400: 0 },
};

function courseStatus(code: string, transcript: TranscriptCourse[]): ChipStatus {
  const t = transcript.find((c) => c.code === code);
  if (!t) return "available";
  if (t.status === "completed") return "complete";
  if (t.status === "planned" || t.status === "in_progress") return "planned";
  return "available";
}

function buildGroupVMs(
  groups: RequirementGroup[],
  progressRows: RequirementProgress[],
  transcript: TranscriptCourse[],
): GroupVM[] {
  return groups.map((g, i) => {
    const key = g.heading ? g.heading.toLowerCase().replace(/\s+/g, "-") : `group-${i}`;
    const progressRow = progressRows.find((r) => r.key === key);
    // Per-course credits/notes only exist once the Gemini grouper has run
    // (design/06: "Per-course credits + notes only appear after LLM
    // grouping") — fall back to the heuristic `courseCodes` list otherwise.
    const courses: GroupCourseVM[] =
      g.courses.length > 0
        ? g.courses.map((c) => ({
            code: c.code,
            credits: c.credits,
            status: courseStatus(c.code, transcript),
            note: c.notes || undefined,
          }))
        : g.courseCodes.map((code) => ({ code, status: courseStatus(code, transcript) }));
    const earned = progressRow
      ? progressRow.earned
      : courses.reduce((s, c) => (c.status === "complete" ? s + (c.credits ?? 0) : s), 0);
    return { key, heading: g.heading || "Requirements", required: g.credits, earned, note: g.notes || undefined, courses };
  });
}

function parseBreadthKeys(breadth: string[]): NonNullable<CourseDetail["breadth"]> {
  const out: NonNullable<CourseDetail["breadth"]> = [];
  for (const b of breadth) {
    const m = b.match(/\((\d)\)/);
    if (m) out.push(`BR${m[1]}` as NonNullable<CourseDetail["breadth"]>[number]);
  }
  return out;
}

function toCourseDetail(c: Course): CourseDetail {
  return {
    code: c.code,
    title: c.title,
    credit: c.credit,
    campus: c.campus,
    description: c.description,
    breadth: parseBreadthKeys(c.breadth),
    exclusions: c.exclusions || undefined,
    sections: c.sections,
  };
}

function Legend() {
  const items: { icon: string; color: string; label: string }[] = [
    { icon: "check", color: "var(--success)", label: "Done" },
    { icon: "circle-dot", color: "var(--accent)", label: "Planned" },
    { icon: "circle", color: "var(--text-tertiary)", label: "Available" },
    { icon: "triangle-alert", color: "var(--danger)", label: "Blocked" },
  ];
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
      {items.map((it) => (
        <span
          key={it.label}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 5,
            fontSize: "var(--text-caption)",
            color: "var(--text-tertiary)",
          }}
        >
          <i data-lucide={it.icon} style={{ width: 13, height: 13, color: it.color }} />
          {it.label}
        </span>
      ))}
    </div>
  );
}

export default function RequirementDetail() {
  const params = useParams<{ code: string }>();
  const code = params.code ?? "";
  const navigate = useNavigate();

  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [program, setProgram] = React.useState<Program | null>(null);
  const [enrolled, setEnrolled] = React.useState(false);
  const [progressRows, setProgressRows] = React.useState<RequirementProgress[]>([]);
  const [transcript, setTranscript] = React.useState<TranscriptCourse[]>([]);

  const [onlyLeft, setOnlyLeft] = React.useState(false);
  const [reparsing, setReparsing] = React.useState(false);
  const [toast, setToast] = React.useState<{ tone: "success" | "danger"; message: string } | null>(null);

  const [selectedCode, setSelectedCode] = React.useState<string | null>(null);
  const [courseDetail, setCourseDetail] = React.useState<Course | null>(null);
  const [courseLoading, setCourseLoading] = React.useState(false);

  React.useEffect(() => {
    if (!code) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    (async () => {
      try {
        const [prog, rec] = await Promise.all([api.getProgram(code), api.getMyRecord()]);
        if (cancelled) return;
        setProgram(prog);
        setEnrolled(rec.programs.some((p) => p.code === code));
        setProgressRows(rec.requirementProgress[code] ?? []);
        setTranscript(rec.transcript);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load this program.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [code]);

  React.useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 5000);
    return () => clearTimeout(t);
  }, [toast]);

  async function handleReparse() {
    if (!code) return;
    setReparsing(true);
    try {
      const groups = await api.reparseProgramRequirements(code);
      setProgram((p) => (p ? { ...p, completionRequirements: groups, requirementsLoaded: true } : p));
      setToast({ tone: "success", message: "Requirements loaded from the calendar via Gemini." });
    } catch {
      setToast({ tone: "danger", message: "Couldn't load requirements. Try again." });
    } finally {
      setReparsing(false);
    }
  }

  function openCourse(courseCode: string) {
    setSelectedCode(courseCode);
    setCourseDetail(null);
    setCourseLoading(true);
    api
      .getCourse(courseCode)
      .then((c) => setCourseDetail(c))
      .finally(() => setCourseLoading(false));
  }

  const groupVMs = program ? buildGroupVMs(program.completionRequirements, progressRows, transcript) : [];
  const earnedTotal = progressRows.reduce((s, r) => s + r.earned, 0);

  const upperLevelMins = program ? UPPER_LEVEL_MINIMUMS[program.programType] : undefined;
  const appliedCodes = Array.from(new Set(progressRows.flatMap((r) => r.appliedCourses)));
  const credits300 = appliedCodes.filter((c) => courseLevel(c) >= 300).reduce((s, c) => s + creditFromCode(c), 0);
  const credits400 = appliedCodes.filter((c) => courseLevel(c) >= 400).reduce((s, c) => s + creditFromCode(c), 0);

  return (
    <>
      <PageHeader
        title={program?.title ?? "Program requirements"}
        breadcrumbs={[
          { label: "Requirements", onClick: () => navigate("/requirements") },
          { label: program?.title ?? code },
        ]}
      />

      {loading && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Skeleton height={110} />
          <Skeleton height={160} />
          <Skeleton height={160} />
        </div>
      )}

      {!loading && error && (
        <Callout tone="danger" title="Couldn't load this program">
          {error}
        </Callout>
      )}

      {!loading && !error && !program && (
        <EmptyState
          icon="search"
          title="Program not found"
          description={`No program matches "${code}".`}
          action={
            <Button variant="primary" onClick={() => navigate("/programs")}>
              Browse programs
            </Button>
          }
        />
      )}

      {!loading && !error && program && (
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          {/* The screen's single highlighted summary card (modernized-ACORN):
              a teal left accent on the program hero only. */}
          <Card style={{ borderLeft: "3px solid var(--accent)" }}>
            <ProgramHeader
              code={program.code}
              name={program.title}
              programType={program.programType || "major"}
              department={program.department}
              totalCredits={program.totalCredits}
              earned={enrolled ? earnedTotal : undefined}
              enrolmentRequirements={program.enrolmentRequirements}
              needsReparse={!program.requirementsLoaded}
              reparsing={reparsing}
              onReparse={handleReparse}
            />
          </Card>

          {enrolled && upperLevelMins && (
            <Card>
              <div
                style={{
                  fontSize: "var(--text-body-sm)",
                  fontWeight: "var(--weight-semibold)",
                  color: "var(--text-secondary)",
                  marginBottom: 14,
                  textTransform: "uppercase",
                  letterSpacing: "var(--tracking-label)",
                }}
              >
                Upper-level requirement
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 20 }}>
                <CreditMeter earned={credits300} required={upperLevelMins.l300} unit="credits at 300+" />
                {upperLevelMins.l400 > 0 && (
                  <CreditMeter earned={credits400} required={upperLevelMins.l400} unit="credits at 400" />
                )}
              </div>
            </Card>
          )}

          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
            <Switch label="Only what's left" checked={onlyLeft} onChange={setOnlyLeft} />
            <Legend />
          </div>

          {!program.requirementsLoaded && (
            <Callout tone="info" title="Requirements haven't been grouped yet">
              {program.rawCompletionText ||
                "Use “Load requirements (Gemini)” above to parse this program's completion requirements into groups."}
            </Callout>
          )}

          {program.requirementsLoaded && groupVMs.length === 0 && (
            <EmptyState
              icon="inbox"
              title="No requirement groups"
              description="This program has no structured completion requirements on file."
            />
          )}

          {groupVMs.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              {groupVMs.map((g) => (
                <RequirementGroupCard
                  key={g.key}
                  heading={g.heading}
                  earned={g.earned}
                  required={g.required}
                  note={g.note}
                  onlyLeft={onlyLeft}
                  courses={g.courses}
                  onCourseClick={(c: { code: string }) => openCourse(c.code)}
                />
              ))}
            </div>
          )}
        </div>
      )}

      <Drawer open={selectedCode != null} onClose={() => setSelectedCode(null)} title={selectedCode ?? ""} width={440}>
        {courseLoading && <Skeleton height={220} />}
        {!courseLoading && !courseDetail && selectedCode && (
          <EmptyState
            icon="search"
            title="Course not found"
            description={`${selectedCode} isn't in the synced catalog yet.`}
          />
        )}
        {!courseLoading && courseDetail && (
          <CourseDetailPanel
            course={toCourseDetail(courseDetail)}
            onAddPlan={() => navigate("/plan")}
            onAddTimetable={() => navigate("/timetable")}
          />
        )}
      </Drawer>

      {toast && (
        <div style={{ position: "fixed", bottom: 20, right: 20, zIndex: 200 }}>
          <Toast tone={toast.tone} onClose={() => setToast(null)}>
            {toast.message}
          </Toast>
        </div>
      )}
    </>
  );
}
