import * as React from "react";
import { useParams } from "react-router-dom";

import { Callout, Card, DataTable, DegreeProgressCard, EmptyState, RequirementProgressList, Skeleton, Wordmark } from "@/ds";
import { api, DEGREE_MINIMUMS } from "@/api";
import type { StudentRecord } from "@/api";

type LoadStatus = "loading" | "ready" | "not_found" | "error";

/**
 * Shared plan (design/screens/05-transcript-settings-share.md "Shared plan"):
 * public, read-only, no SideNav/edit affordances. `getShared` returns a
 * `Partial<StudentRecord>` — only render sections the owner's share payload
 * actually included rather than fabricating numbers (e.g. breadth categories
 * and a term-by-term plan board aren't part of the `StudentRecord` shape at
 * all, so this screen surfaces what *is* shared — programs, requirement
 * progress, transcript, CGPA — and says so plainly when something's missing).
 */
export default function Share() {
  const { token } = useParams<{ token: string }>();
  const [status, setStatus] = React.useState<LoadStatus>("loading");
  const [error, setError] = React.useState<string | null>(null);
  const [data, setData] = React.useState<Partial<StudentRecord> | null>(null);

  const load = React.useCallback(() => {
    if (!token) return;
    setStatus("loading");
    setError(null);
    api
      .getShared(token)
      .then((r) => {
        if (!r) {
          setStatus("not_found");
          return;
        }
        setData(r);
        setStatus("ready");
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : "Failed to load this shared plan.");
        setStatus("error");
      });
  }, [token]);

  React.useEffect(() => load(), [load]);

  const creditsEarned = React.useMemo(
    () => data?.transcript?.filter((c) => c.status === "completed").reduce((s, c) => s + c.credits, 0) ?? null,
    [data],
  );

  const programRows = React.useMemo(
    () =>
      (data?.programs ?? []).map((p) => {
        const groups = data?.requirementProgress?.[p.code] ?? [];
        return {
          code: p.code,
          label: p.name,
          earned: groups.reduce((s, g) => s + g.earned, 0),
          required: groups.reduce((s, g) => s + g.required, 0),
        };
      }),
    [data],
  );

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", color: "var(--text)" }}>
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "16px var(--gutter)",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <a href="/" style={{ textDecoration: "none" }}>
          <Wordmark />
        </a>
      </header>

      <main style={{ maxWidth: "var(--content-max)", margin: "0 auto", padding: "var(--gutter)" }}>
        <div style={{ marginBottom: 20 }}>
          <Callout tone="info" title="Read-only shared view">
            You're viewing a snapshot of someone else's degree plan. Nothing here can be edited.
          </Callout>
        </div>

        {status === "loading" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <Skeleton height={140} />
            <Skeleton height={200} />
          </div>
        )}

        {status === "not_found" && (
          <EmptyState
            icon="link-2-off"
            title="This link isn't valid"
            description="It may have been revoked by its owner, or the URL is incomplete. Ask them to send a fresh link."
          />
        )}

        {status === "error" && (
          <Callout tone="danger" title="Something went wrong">
            {error}
          </Callout>
        )}

        {status === "ready" && data && (
          <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
            {creditsEarned != null ? (
              <DegreeProgressCard
                degreePct={Math.min(100, (creditsEarned / DEGREE_MINIMUMS.total) * 100)}
                earned={creditsEarned}
                requiredCredits={DEGREE_MINIMUMS.total}
                degreeName="Shared degree plan"
              />
            ) : data.cgpa != null ? (
              <Card>
                <div style={{ fontSize: "var(--text-label)", textTransform: "uppercase", letterSpacing: "var(--tracking-label)", color: "var(--text-tertiary)" }}>
                  Cumulative GPA
                </div>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 40, fontWeight: "var(--weight-semibold)", color: "var(--text)" }}>
                  {data.cgpa.toFixed(2)}
                </div>
              </Card>
            ) : null}

            {programRows.length > 0 && (
              <Card>
                <div style={{ fontSize: "var(--text-h3)", fontWeight: "var(--weight-bold)", color: "var(--text)", marginBottom: 8 }}>
                  Program requirements
                </div>
                <RequirementProgressList programs={programRows} />
              </Card>
            )}

            {data.transcript && data.transcript.length > 0 && (
              <Card>
                <div style={{ fontSize: "var(--text-h3)", fontWeight: "var(--weight-bold)", color: "var(--text)", marginBottom: 12 }}>
                  Transcript
                </div>
                <DataTable
                  columns={[
                    { key: "code", header: "Course", mono: true },
                    { key: "title", header: "Title" },
                    { key: "credits", header: "Cr", align: "right", mono: true, render: (v: number) => v.toFixed(1) },
                    { key: "grade", header: "Grade" },
                  ]}
                  rows={data.transcript}
                />
              </Card>
            )}

            {(!data.transcript || data.transcript.length === 0) && (
              <Callout tone="info">
                The plan owner didn't include a term-by-term timetable or breadth breakdown in this share link — just program
                progress and GPA.
              </Callout>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
