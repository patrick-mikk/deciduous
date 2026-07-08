import * as React from "react";

import {
  Badge,
  Button,
  Callout,
  Card,
  Chip,
  DataExportMenu,
  DataTable,
  Dialog,
  EmptyState,
  IconButton,
  Input,
  PageHeader,
  Select,
  Skeleton,
  Sparkline,
  StatTile,
  Toast,
} from "@/ds";
import { api, GRADE_SCALE, markToGradePoint } from "@/api";
import type { StudentRecord, TranscriptCourse, TranscriptCourseStatus } from "@/api";

/**
 * Transcript (design/screens/05-transcript-settings-share.md "Transcript"):
 * GPA summary (StatTile row + trend) -> DataTable grouped by session, newest
 * first, with per-row edit/remove -> GPA projector for in-progress/planned
 * courses. Row edits/adds are local-only (StudentRecord has no PATCH/POST
 * verbs on the typed ApiClient yet) so they demo the interaction without
 * pretending to persist to a backend that doesn't exist.
 */

type LoadStatus = "loading" | "ready" | "error";

// Special (non-GPA) grades — design: "render as chips, excluded from GPA."
const SPECIAL_GRADES = new Set(["CR", "NCR", "P", "LWD", "FZ", "SDF", "INC", "DNW"]);
const GRADE_OPTIONS = [...GRADE_SCALE.map((g) => g.letter), ...SPECIAL_GRADES].map((g) => ({ label: g, value: g }));
const STATUS_OPTIONS: { label: string; value: TranscriptCourseStatus }[] = [
  { label: "Completed", value: "completed" },
  { label: "In progress", value: "in_progress" },
  { label: "Planned", value: "planned" },
  { label: "Extra", value: "extra" },
];
const LETTER_TO_GP: Record<string, number> = Object.fromEntries(GRADE_SCALE.map((g) => [g.letter, g.gp]));

const TERM_LABEL: Record<string, string> = { "1": "Winter", "5": "Summer", "9": "Fall" };
function formatSession(code: string): string {
  return code
    .split("-")
    .map((part) => `${TERM_LABEL[part.slice(4)] ?? "?"} ${part.slice(0, 4)}`)
    .join(" – ");
}

function courseKey(c: Pick<TranscriptCourse, "session" | "code">): string {
  return `${c.session}::${c.code}`;
}

function isGpaEligible(c: TranscriptCourse): boolean {
  return c.status === "completed" && c.mark != null && !SPECIAL_GRADES.has(c.grade);
}

function computeGpa(list: TranscriptCourse[]): number | null {
  const eligible = list.filter(isGpaEligible);
  if (eligible.length === 0) return null;
  const totalCredits = eligible.reduce((s, c) => s + c.credits, 0);
  const totalPoints = eligible.reduce((s, c) => s + c.credits * markToGradePoint(c.mark as number), 0);
  return totalCredits > 0 ? totalPoints / totalCredits : null;
}

interface SessionGroup {
  session: string;
  label: string;
  courses: TranscriptCourse[];
  sessionalGpa: number | null;
  cumGpa: number | null;
}

interface EditState {
  key: string;
  mark: string;
  grade: string;
  status: TranscriptCourseStatus;
}

interface AddState {
  code: string;
  title: string;
  credits: string;
  session: string;
  status: TranscriptCourseStatus;
}

const BLANK_ADD: AddState = { code: "", title: "", credits: "0.5", session: "", status: "planned" };

export default function Transcript() {
  const [status, setStatus] = React.useState<LoadStatus>("loading");
  const [error, setError] = React.useState<string | null>(null);
  const [record, setRecord] = React.useState<StudentRecord | null>(null);
  const [courses, setCourses] = React.useState<TranscriptCourse[]>([]);
  const [editing, setEditing] = React.useState<EditState | null>(null);
  const [adding, setAdding] = React.useState<AddState | null>(null);
  const [projectedGrades, setProjectedGrades] = React.useState<Record<string, string>>({});
  const [toast, setToast] = React.useState<string | null>(null);

  const load = React.useCallback(() => {
    setStatus("loading");
    setError(null);
    api
      .getMyRecord()
      .then((r) => {
        setRecord(r);
        setCourses(r.transcript);
        setStatus("ready");
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : "Failed to load transcript.");
        setStatus("error");
      });
  }, []);

  React.useEffect(() => load(), [load]);

  React.useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 2600);
    return () => clearTimeout(t);
  }, [toast]);

  const ascendingGroups = React.useMemo<SessionGroup[]>(() => {
    const bySession = new Map<string, TranscriptCourse[]>();
    for (const c of courses) {
      const arr = bySession.get(c.session) ?? [];
      arr.push(c);
      bySession.set(c.session, arr);
    }
    const sessions = [...bySession.keys()].sort((a, b) => Number(a.split("-")[0]) - Number(b.split("-")[0]));
    let running: TranscriptCourse[] = [];
    return sessions.map((s) => {
      const list = bySession.get(s) as TranscriptCourse[];
      running = [...running, ...list];
      return {
        session: s,
        label: formatSession(s),
        courses: list,
        sessionalGpa: computeGpa(list),
        cumGpa: computeGpa(running),
      };
    });
  }, [courses]);

  const sessionGroups = React.useMemo(() => [...ascendingGroups].reverse(), [ascendingGroups]);

  const thisSessionGroup = sessionGroups.find((g) => g.sessionalGpa != null) ?? null;
  const creditsEarned = courses.filter((c) => c.status === "completed").reduce((s, c) => s + c.credits, 0);
  const trendValues = ascendingGroups.filter((g) => g.sessionalGpa != null).map((g) => g.sessionalGpa as number);

  const plannedCourses = courses.filter((c) => c.status === "planned" || c.status === "in_progress");
  const baseCredits = courses.filter(isGpaEligible).reduce((s, c) => s + c.credits, 0);
  const basePoints = courses
    .filter(isGpaEligible)
    .reduce((s, c) => s + c.credits * markToGradePoint(c.mark as number), 0);

  const projectedCgpa = React.useMemo(() => {
    let credits = baseCredits;
    let points = basePoints;
    for (const c of plannedCourses) {
      const letter = projectedGrades[courseKey(c)] ?? "B";
      const gp = LETTER_TO_GP[letter] ?? 3.0;
      credits += c.credits;
      points += c.credits * gp;
    }
    return credits > 0 ? points / credits : null;
  }, [baseCredits, basePoints, plannedCourses, projectedGrades]);

  function updateCourse(key: string, patch: Partial<TranscriptCourse>) {
    setCourses((prev) => prev.map((c) => (courseKey(c) === key ? { ...c, ...patch } : c)));
  }

  function removeCourse(key: string) {
    setCourses((prev) => prev.filter((c) => courseKey(c) !== key));
    setToast("Course removed.");
  }

  function saveEdit() {
    if (!editing) return;
    const mark = editing.mark.trim() === "" ? null : Number(editing.mark);
    updateCourse(editing.key, {
      mark: mark != null && !Number.isNaN(mark) ? mark : null,
      grade: editing.grade,
      status: editing.status,
    });
    setEditing(null);
    setToast("Course updated.");
  }

  function saveAdd() {
    if (!adding || !adding.code.trim() || !adding.session.trim()) return;
    const next: TranscriptCourse = {
      code: adding.code.trim().toUpperCase(),
      title: adding.title.trim() || adding.code.trim().toUpperCase(),
      credits: Number(adding.credits) || 0.5,
      mark: null,
      grade: "",
      session: adding.session.trim(),
      status: adding.status,
    };
    setCourses((prev) => [...prev, next]);
    setAdding(null);
    setToast("Course added.");
  }

  function columnsFor(): { key: string; header: string; align?: string; mono?: boolean; sortable?: boolean; render?: (v: unknown, row: TranscriptCourse) => React.ReactNode }[] {
    return [
      { key: "code", header: "Course", mono: true },
      { key: "title", header: "Title" },
      { key: "credits", header: "Cr", align: "right", mono: true, render: (v) => (v as number).toFixed(1) },
      {
        key: "mark",
        header: "Mark",
        align: "right",
        mono: true,
        render: (v) => (v == null ? "—" : String(v)),
      },
      {
        key: "grade",
        header: "Grade",
        render: (v, row) => {
          const grade = v as string;
          if (!grade) return "—";
          if (SPECIAL_GRADES.has(grade)) return <Chip tone="info">{grade}</Chip>;
          return (
            <>
              {grade}
              {row.status === "extra" && (
                <span style={{ marginLeft: 6 }}>
                  <Badge tone="neutral">Extra</Badge>
                </span>
              )}
            </>
          );
        },
      },
      {
        key: "actions",
        header: "",
        sortable: false,
        render: (_v, row) => (
          <div style={{ display: "flex", gap: 4, justifyContent: "flex-end" }}>
            <IconButton
              icon="pencil"
              label={`Edit ${row.code}`}
              onClick={() =>
                setEditing({
                  key: courseKey(row),
                  mark: row.mark != null ? String(row.mark) : "",
                  grade: row.grade,
                  status: row.status,
                })
              }
            />
            <IconButton icon="trash-2" label={`Remove ${row.code}`} onClick={() => removeCourse(courseKey(row))} />
          </div>
        ),
      },
    ];
  }

  if (status === "loading") {
    return (
      <>
        <PageHeader title="Transcript" subtitle="Loading your academic record…" />
        <div style={{ display: "flex", gap: 16, marginBottom: 24 }}>
          {[0, 1, 2, 3].map((i) => (
            <div key={i} style={{ flex: 1 }}>
              <Skeleton height={90} />
            </div>
          ))}
        </div>
        <Skeleton height={280} />
      </>
    );
  }

  if (status === "error") {
    return (
      <>
        <PageHeader title="Transcript" />
        <Callout
          tone="danger"
          title="Couldn't load your transcript"
          action={
            <Button size="sm" variant="secondary" onClick={load}>
              Retry
            </Button>
          }
        >
          {error}
        </Callout>
      </>
    );
  }

  return (
    <>
      <PageHeader
        title="Transcript"
        subtitle={record ? `${courses.length} course${courses.length === 1 ? "" : "s"} on record` : undefined}
        actions={
          <>
            <Button variant="secondary" icon="upload" onClick={() => setToast("Import flow lives on Onboarding — see /onboarding.")}>
              Import
            </Button>
            <Button variant="secondary" icon="plus" onClick={() => setAdding(BLANK_ADD)}>
              Add course
            </Button>
            <DataExportMenu onExport={(kind: string) => setToast(`Exported as ${kind.toUpperCase()} (demo — no backend export yet).`)} />
          </>
        }
      />

      {courses.length === 0 ? (
        <EmptyState
          icon="file-text"
          title="No courses on record yet"
          description="Import your Degree Explorer record or add a course manually to get started."
          action={
            <Button icon="plus" onClick={() => setAdding(BLANK_ADD)}>
              Add course
            </Button>
          }
        />
      ) : (
        <>
          <div style={{ display: "flex", gap: 16, marginBottom: 24, flexWrap: "wrap" }}>
            <StatTile label="CGPA" value={(record?.cgpa ?? 0).toFixed(2)} accent="var(--primary)" />
            <StatTile
              label="This session"
              value={thisSessionGroup?.sessionalGpa != null ? thisSessionGroup.sessionalGpa.toFixed(2) : "—"}
              sub={thisSessionGroup?.label}
            />
            <StatTile label="Credits earned" value={creditsEarned.toFixed(1)} />
            <Card padding="16px 18px" style={{ flex: 1, minWidth: 180 }}>
              <div
                style={{
                  fontSize: "var(--text-label)",
                  fontWeight: "var(--weight-semibold)",
                  letterSpacing: "var(--tracking-label)",
                  textTransform: "uppercase",
                  color: "var(--text-tertiary)",
                  marginBottom: 8,
                }}
              >
                Trend
              </div>
              {trendValues.length >= 2 ? (
                <Sparkline values={trendValues} width={160} height={44} />
              ) : (
                <div style={{ fontSize: "var(--text-body-sm)", color: "var(--text-tertiary)" }}>
                  Not enough sessions yet.
                </div>
              )}
            </Card>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 20, marginBottom: 24 }}>
            {sessionGroups.map((g) => (
              <div key={g.session}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "baseline",
                    justifyContent: "space-between",
                    marginBottom: 8,
                  }}
                >
                  <span style={{ fontSize: "var(--text-h3)", fontWeight: "var(--weight-bold)", color: "var(--text)" }}>
                    {g.label}
                  </span>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: "var(--text-body-sm)", color: "var(--text-tertiary)" }}>
                    {g.sessionalGpa != null ? `Sessional GPA ${g.sessionalGpa.toFixed(2)}` : "No graded courses"}
                    {g.cumGpa != null ? ` · Cum ${g.cumGpa.toFixed(2)}` : ""}
                  </span>
                </div>
                <DataTable columns={columnsFor()} rows={g.courses} emptyText="No courses this session." />
              </div>
            ))}
          </div>

          <Card>
            <div style={{ fontSize: "var(--text-h3)", fontWeight: "var(--weight-bold)", color: "var(--text)", marginBottom: 4 }}>
              GPA projector
            </div>
            <p style={{ margin: "0 0 14px", fontSize: "var(--text-body-sm)", color: "var(--text-secondary)" }}>
              Enter a target grade for each in-progress or planned course to see a projected CGPA.
            </p>
            {plannedCourses.length === 0 ? (
              <div style={{ fontSize: "var(--text-body-sm)", color: "var(--text-tertiary)" }}>
                No in-progress or planned courses to project.
              </div>
            ) : (
              <>
                <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 16 }}>
                  {plannedCourses.map((c) => {
                    const key = courseKey(c);
                    return (
                      <div key={key} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                        <span style={{ fontFamily: "var(--font-mono)", fontSize: "var(--text-body-sm)", width: 90 }}>{c.code}</span>
                        <span style={{ flex: 1, fontSize: "var(--text-body-sm)", color: "var(--text-secondary)" }}>{c.title}</span>
                        <div style={{ width: 120 }}>
                          <Select
                            value={projectedGrades[key] ?? "B"}
                            onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
                              setProjectedGrades((prev) => ({ ...prev, [key]: e.target.value }))
                            }
                            options={GRADE_SCALE.map((g) => ({ label: g.letter, value: g.letter }))}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
                <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
                  <span style={{ fontSize: "var(--text-label)", textTransform: "uppercase", letterSpacing: "var(--tracking-label)", color: "var(--text-tertiary)" }}>
                    Projected CGPA
                  </span>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 28, fontWeight: "var(--weight-semibold)", color: "var(--primary)" }}>
                    {projectedCgpa != null ? projectedCgpa.toFixed(2) : "—"}
                  </span>
                </div>
              </>
            )}
          </Card>
        </>
      )}

      <Dialog open={editing != null} title={editing ? `Edit ${editing.key.split("::")[1]}` : ""} onClose={() => setEditing(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setEditing(null)}>
              Cancel
            </Button>
            <Button onClick={saveEdit}>Save</Button>
          </>
        }
      >
        {editing && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <Input
              label="Mark (%)"
              type="number"
              value={editing.mark}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEditing({ ...editing, mark: e.target.value })}
            />
            <Select
              label="Grade"
              value={editing.grade}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setEditing({ ...editing, grade: e.target.value })}
              options={[{ label: "—", value: "" }, ...GRADE_OPTIONS]}
            />
            <Select
              label="Status"
              value={editing.status}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
                setEditing({ ...editing, status: e.target.value as TranscriptCourseStatus })
              }
              options={STATUS_OPTIONS}
            />
          </div>
        )}
      </Dialog>

      <Dialog open={adding != null} title="Add course" onClose={() => setAdding(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setAdding(null)}>
              Cancel
            </Button>
            <Button onClick={saveAdd}>Add</Button>
          </>
        }
      >
        {adding && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <Input
              label="Course code"
              placeholder="POL208H1"
              value={adding.code}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setAdding({ ...adding, code: e.target.value })}
            />
            <Input
              label="Title"
              value={adding.title}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setAdding({ ...adding, title: e.target.value })}
            />
            <Input
              label="Credits"
              type="number"
              value={adding.credits}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setAdding({ ...adding, credits: e.target.value })}
            />
            <Input
              label="Session"
              placeholder="20269"
              value={adding.session}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setAdding({ ...adding, session: e.target.value })}
            />
            <Select
              label="Status"
              value={adding.status}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
                setAdding({ ...adding, status: e.target.value as TranscriptCourseStatus })
              }
              options={STATUS_OPTIONS}
            />
          </div>
        )}
      </Dialog>

      {toast && (
        <div style={{ position: "fixed", right: 20, bottom: 20, zIndex: 200 }}>
          <Toast tone="info" onClose={() => setToast(null)}>
            {toast}
          </Toast>
        </div>
      )}
    </>
  );
}
