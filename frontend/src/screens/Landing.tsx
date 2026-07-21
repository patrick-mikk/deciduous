import * as React from "react";
import { useNavigate } from "react-router-dom";

import { Wordmark, Button, Chip, Skeleton, Callout } from "@/ds";
import { api } from "@/api";
import type { SessionCode } from "@/api";
import "./Landing.css";

/**
 * Landing (`/`) — the one public page (design/screens/01-auth-and-onboarding.md).
 * Plain header bar + a one-line description of the tool, modelled on UofT's
 * Timetable Builder: no illustration, no sample-data preview, minimal color.
 */

function sessionLabel(code: SessionCode): string {
  const year = code.slice(0, 4);
  const digit = code.slice(4);
  const term = digit === "9" ? "Fall" : digit === "1" ? "Winter" : digit === "5" ? "Summer" : "Session";
  return `${term} ${year}`;
}

type SessionsState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; sessions: SessionCode[] };

export default function Landing() {
  const navigate = useNavigate();
  const [sessionsState, setSessionsState] = React.useState<SessionsState>({ status: "loading" });
  const [retryKey, setRetryKey] = React.useState(0);

  React.useEffect(() => {
    let cancelled = false;
    setSessionsState({ status: "loading" });
    api
      .getSessions()
      .then((sessions) => {
        if (!cancelled) setSessionsState({ status: "ready", sessions });
      })
      .catch(() => {
        if (!cancelled) setSessionsState({ status: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, [retryKey]);

  return (
    <div className="dc-landing">
      <header className="dc-landing__header">
        <Wordmark size={22} />
        <nav className="dc-landing__header-nav">
          <Button type="button" variant="secondary" size="sm" onClick={() => navigate("/signin")}>
            Sign in
          </Button>
        </nav>
      </header>

      <section className="dc-landing__hero">
        <h1 className="dc-landing__headline">Deciduous</h1>
        <p className="dc-landing__subtitle">
          Search UofT Arts &amp; Science courses, track your degree progress against the real
          program rules, and build a conflict-free timetable.
        </p>

        <div className="dc-landing__cta-row">
          <Button type="button" variant="primary" size="lg" onClick={() => navigate("/onboarding")}>
            Get started
          </Button>
        </div>

        <div className="dc-landing__live" aria-live="polite">
          {sessionsState.status === "loading" && (
            <>
              <Skeleton width={96} height={22} radius="var(--radius-pill)" />
              <Skeleton width={110} height={22} radius="var(--radius-pill)" />
              <Skeleton width={88} height={22} radius="var(--radius-pill)" />
            </>
          )}
          {sessionsState.status === "error" && (
            <Callout tone="warning" title="Couldn't load live session data">
              <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                The timetable feed didn't respond.
                <Button type="button" variant="link" size="sm" onClick={() => setRetryKey((k) => k + 1)}>
                  Retry
                </Button>
              </span>
            </Callout>
          )}
          {sessionsState.status === "ready" &&
            (sessionsState.sessions.length > 0 ? (
              sessionsState.sessions.map((s) => (
                <Chip key={s} tone="accent" dot>
                  {sessionLabel(s)}
                </Chip>
              ))
            ) : (
              <span style={{ fontSize: "var(--text-body-sm)", color: "var(--text-tertiary)" }}>
                No live sessions published right now.
              </span>
            ))}
        </div>

        <p className="dc-landing__disclaimer">
          Unofficial, not affiliated with the University of Toronto.
        </p>
      </section>
    </div>
  );
}
