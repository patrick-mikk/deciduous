import * as React from "react";
import { useNavigate } from "react-router-dom";

import {
  Button,
  Callout,
  Card,
  DegreeAudit,
  EmptyState,
  PageHeader,
  ProgressRing,
  RequirementProgressList,
  Skeleton,
  Switch,
} from "@/ds";
import { api } from "@/api";
import type { DegreeAuditData, StudentRecord } from "@/api";

/**
 * Requirements overview — routed at "/requirements" (design/01-information-architecture.md,
 * design/screens/02-dashboard-and-progress.md "Requirements overview").
 *
 * Degree-level hard-rule audit (design/09 §1/§7, `<DegreeAudit>`) plus a
 * per-program progress summary (`<RequirementProgressList>`) that links into
 * `/requirements/:code` for the full requirement-group breakdown.
 */

interface ProgramSummary {
  code: string;
  label: string;
  earned: number;
  required: number;
  incomplete: number;
}

export default function Requirements() {
  const navigate = useNavigate();

  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [record, setRecord] = React.useState<StudentRecord | null>(null);
  const [audit, setAudit] = React.useState<DegreeAuditData | null>(null);
  const [programSummaries, setProgramSummaries] = React.useState<ProgramSummary[]>([]);
  const [onlyLeft, setOnlyLeft] = React.useState(false);

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    (async () => {
      try {
        const [rec, auditData] = await Promise.all([api.getMyRecord(), api.getMyDegreeAudit()]);
        if (cancelled) return;
        setRecord(rec);
        setAudit(auditData);

        const programs = await Promise.all(rec.programs.map((p) => api.getProgram(p.code)));
        if (cancelled) return;

        const summaries: ProgramSummary[] = rec.programs.map((ref, i) => {
          const prog = programs[i];
          const rows = rec.requirementProgress[ref.code] ?? [];
          const earned = rows.reduce((s, r) => s + r.earned, 0);
          const required = prog?.totalCredits ?? rows.reduce((s, r) => s + r.required, 0);
          const incomplete = rows.filter((r) => r.status === "incomplete").length;
          return { code: ref.code, label: prog?.title ?? ref.name, earned, required, incomplete };
        });
        setProgramSummaries(summaries);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load requirements.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const totalGroupCount = record
    ? Object.values(record.requirementProgress).reduce((s, rows) => s + rows.length, 0)
    : 0;
  const totalIncomplete = record
    ? Object.values(record.requirementProgress).reduce(
        (s, rows) => s + rows.filter((r) => r.status === "incomplete").length,
        0,
      )
    : 0;

  const visibleSummaries = onlyLeft ? programSummaries.filter((p) => p.earned < p.required) : programSummaries;

  return (
    <>
      <PageHeader
        title="Requirements"
        subtitle="Degree and program requirement progress, computed from your transcript and plan."
        actions={
          <>
            <Switch label="Only what's left" checked={onlyLeft} onChange={setOnlyLeft} />
            <Button variant="secondary" icon="download" onClick={() => window.print()}>
              Export
            </Button>
          </>
        }
      />

      {loading && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Skeleton height={150} />
          <Skeleton height={220} />
        </div>
      )}

      {!loading && error && (
        <Callout tone="danger" title="Couldn't load requirements">
          {error}
        </Callout>
      )}

      {!loading && !error && record && record.programs.length === 0 && (
        <EmptyState
          icon="graduation-cap"
          title="No programs yet"
          description="Import your transcript or add a program to start tracking requirement progress."
          action={
            <Button variant="primary" icon="plus" onClick={() => navigate("/programs")}>
              Browse programs
            </Button>
          }
        />
      )}

      {!loading && !error && record && record.programs.length > 0 && audit && (
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <Card>
            <div style={{ display: "flex", alignItems: "center", gap: 20, marginBottom: 18 }}>
              <ProgressRing value={Math.round((audit.totalEarned / 20) * 100)} size="md" tone="primary" sublabel="complete" />
              <div>
                <div style={{ fontSize: "var(--text-h3)", fontWeight: "var(--weight-semibold)", color: "var(--text)" }}>
                  Degree progress
                </div>
                <div
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "var(--text-body-sm)",
                    color: "var(--text-secondary)",
                    marginTop: 4,
                  }}
                >
                  {audit.totalEarned.toFixed(1)} / 20.0 credits · {totalGroupCount} requirement
                  {totalGroupCount === 1 ? "" : "s"} · {totalIncomplete} incomplete
                </div>
              </div>
            </div>
            <DegreeAudit {...audit} />
          </Card>

          <div>
            <div
              style={{
                fontSize: "var(--text-h3)",
                fontWeight: "var(--weight-semibold)",
                color: "var(--text)",
                marginBottom: 8,
              }}
            >
              Your programs
            </div>
            {visibleSummaries.length === 0 ? (
              <Card>
                <EmptyState
                  icon="check"
                  title="Everything's complete"
                  description="No enrolled program has outstanding requirements."
                />
              </Card>
            ) : (
              <Card padding="0 var(--space-5)">
                <RequirementProgressList
                  programs={visibleSummaries}
                  onView={(p: { code: string }) => navigate(`/requirements/${p.code}`)}
                />
              </Card>
            )}
          </div>
        </div>
      )}
    </>
  );
}
