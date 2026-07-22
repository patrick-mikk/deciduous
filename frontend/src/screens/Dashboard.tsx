import * as React from "react";
import { useNavigate } from "react-router-dom";

import {
  PageHeader,
  StatTile,
  DegreeProgressCard,
  DegreeAudit,
  ProgramCard,
  BreadthTracker,
  NotificationPanel,
  Card,
  Button,
  Checkbox,
  EmptyState,
  Skeleton,
  Callout,
} from "@/ds";
import { api } from "@/api";
import type { Alert, BreadthData, BreadthEvaluation, DegreeAuditData, Program, StudentRecord, Summary } from "@/api";
import "./Dashboard.css";

/**
 * Dashboard (`/dashboard`) — the degree-audit home screen
 * (design/screens/02-dashboard-and-progress.md + design/09-uoft-degree-rules.md).
 *
 * "Where am I and what's next?": a StatTile KPI row (credits / CGPA / breadth /
 * standing), the DegreeProgressCard growth-tree hero, a hard-rule DegreeAudit
 * (one row per design/09 §1 rule), the student's enrolled ProgramCard list,
 * the full-width BreadthTracker, an alerts panel, and a derived next-actions
 * checklist. Composed entirely from src/ds (design system) + src/api (typed
 * client, falling back to the mock adapter when VITE_API_BASE is unset).
 */

interface DashboardData {
  summary: Summary;
  audit: DegreeAuditData;
  breadthData: BreadthData;
  breadthEvaluation: BreadthEvaluation;
  record: StudentRecord;
  allPrograms: Program[];
}

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: DashboardData };

interface ProgramRow {
  code: string;
  name: string;
  programType: Program["programType"];
  department: string;
  earned: number;
  total: number;
}

interface NextAction {
  id: string;
  label: string;
}

/** design/09 §6: Good standing requires CGPA ≥ 1.50. Probation/suspension also
 * depend on sessional/annual GPA the dashboard doesn't have on hand — this is
 * the CGPA-only best-effort signal; the authoritative check belongs server-side. */
function standingFor(cgpa: number): { label: string; tone: "success" | "warning" | "danger" } {
  if (cgpa >= 1.5) return { label: "Good standing", tone: "success" };
  if (cgpa >= 1.0) return { label: "At risk", tone: "warning" };
  return { label: "Below minimum", tone: "danger" };
}

const TONE_VAR: Record<"success" | "warning" | "danger", string> = {
  success: "var(--success)",
  warning: "var(--warning)",
  danger: "var(--danger)",
};

function buildProgramRows(record: StudentRecord, allPrograms: Program[]): ProgramRow[] {
  return record.programs.map((enrolled) => {
    const full = allPrograms.find((p) => p.code === enrolled.code);
    // Completion comes from the ONE authoritative source (`GET /api/me`'s
    // `programs[]`, computed by `_audit.program_progress_summary`) — never
    // recomputed here by summing per-group `earned` (that double-counts a
    // course listed under both an umbrella group and its sub-group) or by
    // reading a raw 0.0 `totalCredits`.
    return {
      code: enrolled.code,
      name: full?.title ?? enrolled.name,
      programType: full?.programType ?? "major",
      department: full?.department ?? "",
      earned: enrolled.earnedCredits,
      total: enrolled.totalCredits,
    };
  });
}

function buildNextActions(audit: DegreeAuditData, breadth: BreadthEvaluation, unreadAlerts: number): NextAction[] {
  const actions: NextAction[] = [];
  if (audit.level300 < 6.0) {
    actions.push({ id: "level300", label: `Add ${(6.0 - audit.level300).toFixed(1)} credit(s) at the 300+ level` });
  }
  if (audit.level200 < 13.0) {
    actions.push({ id: "level200", label: `Add ${(13.0 - audit.level200).toFixed(1)} credit(s) at the 200+ level` });
  }
  if (audit.artsciEarned < 10.0) {
    actions.push({ id: "artsci", label: `Add ${(10.0 - audit.artsciEarned).toFixed(1)} Arts & Science credit(s)` });
  }
  if (!breadth.satisfied) {
    actions.push({
      id: "breadth",
      label: `Pick a breadth course: ${breadth.remaining.toFixed(1)} credit(s) still needed`,
    });
  }
  if (audit.topDesignator && audit.topDesignator.credits > 15.0) {
    actions.push({
      id: "same-subject-cap",
      label: `Reduce ${audit.topDesignator.code} credits: over the 15.0 same-subject cap`,
    });
  }
  if (audit.cgpa < 1.85) {
    actions.push({ id: "cgpa", label: "Raise your CGPA toward the 1.85 graduation minimum" });
  }
  if (unreadAlerts > 0) {
    actions.push({ id: "alerts", label: `Resolve ${unreadAlerts} unread alert${unreadAlerts > 1 ? "s" : ""}` });
  }
  if (actions.length === 0) {
    actions.push({ id: "on-track", label: "You're on track, no outstanding actions" });
  }
  return actions;
}

function DashboardSkeleton() {
  return (
    <>
      <div className="dc-dashboard__stats">
        {[0, 1, 2, 3].map((i) => (
          <Card key={i} style={{ flex: 1, minWidth: 150 }}>
            <Skeleton width="60%" height={12} style={{ marginBottom: 10 }} />
            <Skeleton width="45%" height={26} />
          </Card>
        ))}
      </div>
      <div className="dc-dashboard__columns">
        <div className="dc-dashboard__left">
          <Card>
            <Skeleton width={200} height={200} radius="50%" />
          </Card>
          <Card>
            <Skeleton height={14} style={{ marginBottom: 14 }} />
            <Skeleton height={14} style={{ marginBottom: 14 }} />
            <Skeleton height={14} style={{ marginBottom: 14 }} />
            <Skeleton height={14} />
          </Card>
        </div>
        <div className="dc-dashboard__right">
          <Card>
            <Skeleton height={14} style={{ marginBottom: 10 }} />
            <Skeleton height={14} style={{ marginBottom: 10 }} />
            <Skeleton height={14} />
          </Card>
        </div>
      </div>
    </>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [state, setState] = React.useState<LoadState>({ status: "loading" });
  const [alerts, setAlerts] = React.useState<Alert[]>([]);
  const [checkedActions, setCheckedActions] = React.useState<Record<string, boolean>>({});

  const load = React.useCallback(async () => {
    setState({ status: "loading" });
    try {
      const [summary, audit, breadth, record, allPrograms, myAlerts] = await Promise.all([
        api.getMySummary(),
        api.getMyDegreeAudit(),
        api.getMyBreadth(),
        api.getMyRecord(),
        api.getAllPrograms(),
        api.getMyAlerts(),
      ]);
      setAlerts(myAlerts);
      setState({
        status: "ready",
        data: {
          summary,
          audit,
          breadthData: breadth.data,
          breadthEvaluation: breadth.evaluation,
          record,
          allPrograms,
        },
      });
    } catch (err) {
      setState({
        status: "error",
        message: err instanceof Error ? err.message : "Failed to load the dashboard.",
      });
    }
  }, []);

  React.useEffect(() => {
    load();
  }, [load]);

  return (
    <div>
      <PageHeader
        title="Dashboard"
        subtitle="Where you stand toward your degree, and what to do next."
        actions={
          <Button icon="calendar-plus" onClick={() => navigate("/plan")}>
            Plan next term
          </Button>
        }
      />

      {state.status === "loading" && <DashboardSkeleton />}

      {state.status === "error" && (
        <Callout
          tone="danger"
          title="Couldn't load your dashboard"
          action={
            <Button size="sm" variant="secondary" onClick={load}>
              Retry
            </Button>
          }
        >
          {state.message}
        </Callout>
      )}

      {state.status === "ready" && state.data.record.programs.length === 0 && state.data.record.transcript.length === 0 && (
        <EmptyState
          icon="upload"
          title="Import your record"
          description="Connect your transcript to see credits, CGPA, breadth coverage, and program progress here."
          action={<Button onClick={() => navigate("/settings")}>Import transcript</Button>}
        />
      )}

      {state.status === "ready" &&
        (state.data.record.programs.length > 0 || state.data.record.transcript.length > 0) && (
          <ReadyDashboard
            data={state.data}
            alerts={alerts}
            onMarkRead={(id) => setAlerts((prev) => prev.map((a) => (a.id === id ? { ...a, read: true } : a)))}
            onMarkAllRead={() => setAlerts((prev) => prev.map((a) => ({ ...a, read: true })))}
            checkedActions={checkedActions}
            onToggleAction={(id) => setCheckedActions((prev) => ({ ...prev, [id]: !prev[id] }))}
          />
        )}
    </div>
  );
}

function ReadyDashboard({
  data,
  alerts,
  onMarkRead,
  onMarkAllRead,
  checkedActions,
  onToggleAction,
}: {
  data: DashboardData;
  alerts: Alert[];
  onMarkRead: (id: string) => void;
  onMarkAllRead: () => void;
  checkedActions: Record<string, boolean>;
  onToggleAction: (id: string) => void;
}) {
  const navigate = useNavigate();
  const { summary, audit, breadthData, breadthEvaluation, record, allPrograms } = data;
  const standing = standingFor(audit.cgpa);
  const programRows = React.useMemo(() => buildProgramRows(record, allPrograms), [record, allPrograms]);
  const unreadAlertCount = alerts.filter((a) => !a.read).length;
  const nextActions = React.useMemo(
    () => buildNextActions(audit, breadthEvaluation, unreadAlertCount),
    [audit, breadthEvaluation, unreadAlertCount],
  );

  return (
    <>
      {/* KPI row: flat, 1px-bordered tiles — no per-tile accent bar. The single
          teal accent on this screen lives on the degree-progress summary card
          below (modernized-ACORN: one highlighted card, not every card). */}
      <div className="dc-dashboard__stats">
        <StatTile
          label="Credits"
          value={`${summary.creditsEarned.toFixed(1)}/${summary.creditsTotal.toFixed(1)}`}
          sub={`${Math.round(summary.degreePct)}% of degree`}
        />
        <StatTile
          label="CGPA"
          value={audit.cgpa.toFixed(2)}
          sub="Graduate minimum 1.85"
        />
        <StatTile
          label="Breadth"
          value={`${breadthEvaluation.fulls}/5`}
          sub={breadthEvaluation.satisfied ? "Requirement satisfied" : `${breadthEvaluation.remaining.toFixed(1)} cr to go`}
        />
        <StatTile label="Standing" value={standing.label} sub={`CGPA ${audit.cgpa.toFixed(2)}`} />
      </div>

      <div className="dc-dashboard__columns">
        <div className="dc-dashboard__left">
          {/* The one highlighted summary card on this screen: a single subtle
              teal left-accent bar marks the degree-progress hero. */}
          <Card style={{ borderLeft: "3px solid var(--accent)" }}>
            <div className="dc-dashboard__hero">
              <DegreeProgressCard
                degreePct={summary.degreePct}
                earned={audit.totalEarned}
                requiredCredits={20}
                onTrack={audit.cgpa >= 1.85 && breadthEvaluation.satisfied}
                degreeName="Your degree"
              />
            </div>
          </Card>

          <Card>
            <div className="dc-dashboard__section-title">
              <h2>Degree audit</h2>
            </div>
            <DegreeAudit
              totalEarned={audit.totalEarned}
              artsciEarned={audit.artsciEarned}
              level200={audit.level200}
              level300={audit.level300}
              topDesignator={audit.topDesignator}
              cgpa={audit.cgpa}
            />
          </Card>

          <Card>
            <div className="dc-dashboard__section-title">
              <h2>My programs</h2>
              <Button variant="ghost" size="sm" onClick={() => navigate("/requirements")}>
                View requirements
              </Button>
            </div>
            {programRows.length === 0 ? (
              <EmptyState
                icon="graduation-cap"
                title="No programs yet"
                description="Enrol in a Specialist, Major, or Minor to start tracking program-level progress."
                action={
                  <Button variant="secondary" onClick={() => navigate("/programs")}>
                    Browse programs
                  </Button>
                }
              />
            ) : (
              <div className="dc-dashboard__program-list">
                {programRows.map((p) => (
                  <ProgramCard
                    key={p.code}
                    code={p.code}
                    name={p.name}
                    programType={p.programType || "major"}
                    department={p.department}
                    earned={p.earned}
                    total={p.total}
                    enrolled
                    onView={() => navigate(`/requirements/${p.code}`)}
                  />
                ))}
              </div>
            )}
          </Card>
        </div>

        <div className="dc-dashboard__right">
          {/* NotificationPanel (design system) renders at a fixed 320px width — wider than this
              1fr column at narrow viewports. overflowX:auto keeps that scroll inside the card
              instead of the page (screens must never scroll horizontally at the body level). */}
          <Card style={{ overflowX: "auto" }}>
            <div className="dc-dashboard__section-title">
              <h2>Alerts</h2>
            </div>
            {alerts.length === 0 ? (
              <EmptyState icon="bell" title="No alerts" description="You're all caught up." />
            ) : (
              <NotificationPanel items={alerts} onMarkRead={onMarkRead} onMarkAllRead={onMarkAllRead} />
            )}
          </Card>

          <Card>
            <div className="dc-dashboard__section-title">
              <h2>Next actions</h2>
            </div>
            <div className="dc-dashboard__next-actions">
              {nextActions.map((action) => (
                <div className="dc-dashboard__next-action-row" key={action.id}>
                  <Checkbox
                    label={action.label}
                    checked={!!checkedActions[action.id]}
                    onChange={() => onToggleAction(action.id)}
                  />
                </div>
              ))}
              <Button variant="secondary" icon="wand-sparkles" onClick={() => navigate("/timetable/optimize")}>
                Auto-plan
              </Button>
            </div>
          </Card>
        </div>
      </div>

      <Card>
        <BreadthTracker data={breadthData} />
      </Card>
    </>
  );
}
