import * as React from "react";
import { useNavigate } from "react-router-dom";

import {
  Wordmark,
  Button,
  Badge,
  Chip,
  Skeleton,
  Callout,
  DegreeProgressCard,
  BreadthTracker,
} from "@/ds";
import { api } from "@/api";
import type { BreadthData, SessionCode } from "@/api";
import "./Landing.css";

/**
 * Landing (`/`) — the one marketing/editorial page (design/screens/01-auth-and-onboarding.md).
 * Public, no AppLayout chrome. Hero uses the serif/display treatment; the
 * right-hand visual is real DegreeProgressCard + BreadthTracker components
 * fed illustrative sample data (clearly labelled "Sample data" — this is a
 * logged-out page, there is no real record to show yet).
 */

const SAMPLE_BREADTH: BreadthData = { BR1: 1.0, BR2: 1.0, BR3: 1.0, BR4: 1.0, BR5: 0.5 };

const FEATURES = [
  {
    icon: "upload",
    title: "Import in seconds",
    desc: "Drop in your Academic History PDF from ACORN or run the bookmarklet. Your programs and transcript populate automatically, encrypted at rest.",
  },
  {
    icon: "list-checks",
    title: "See what's left",
    desc: "A live degree audit tracks credits, breadth, and program minimums against the real UofT Arts & Science rules, not a guess.",
  },
  {
    icon: "calendar-check-2",
    title: "Optimize your timetable",
    desc: "Build a conflict-free weekly schedule, then let the optimizer rank alternatives around the times you actually want.",
  },
] as const;

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

  const scrollToFeatures = () => {
    document.getElementById("features")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="dc-landing">
      <header className="dc-landing__header">
        <Wordmark size={22} />
        <nav className="dc-landing__header-nav">
          <Button type="button" variant="ghost" size="sm" onClick={scrollToFeatures}>
            Features
          </Button>
          <Button type="button" variant="secondary" size="sm" onClick={() => navigate("/signin")}>
            Sign in
          </Button>
        </nav>
      </header>

      <section className="dc-landing__hero">
        <div>
          <p className="dc-landing__eyebrow">For UofT Arts &amp; Science students</p>
          <h1 className="dc-landing__headline">
            Plan your whole degree: requirements, courses, and a conflict-free timetable.
          </h1>
          <p className="dc-landing__subtitle">
            Deciduous pulls in your transcript, tracks every credit and breadth requirement against
            the real degree rules, and builds a schedule that actually fits together.
          </p>

          <div className="dc-landing__cta-row">
            <Button type="button" variant="primary" size="lg" onClick={() => navigate("/onboarding")}>
              Get started
            </Button>
            <Button type="button" variant="secondary" size="lg" onClick={scrollToFeatures}>
              See how it works
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
            Unofficial · not affiliated with the University of Toronto.
          </p>
        </div>

        <div className="dc-landing__visual" aria-hidden="true">
          <div className="dc-landing__visual-badge">
            <Badge tone="neutral">Sample data</Badge>
          </div>
          <DegreeProgressCard
            degreeName="B.A., Public Policy Major"
            degreePct={67}
            earned={13.5}
            requiredCredits={20}
            onTrack
            expectedGrad="Spring 2027"
          />
          <div className="dc-landing__breadth-card">
            <BreadthTracker data={SAMPLE_BREADTH} />
          </div>
        </div>
      </section>

      <section id="features" className="dc-landing__features">
        <h2 className="dc-landing__features-heading">Everything a degree audit should be</h2>
        <div className="dc-landing__feature-grid">
          {FEATURES.map((f) => (
            <div key={f.title}>
              <div className="dc-landing__feature-icon">
                <i data-lucide={f.icon} style={{ width: 20, height: 20, color: "var(--primary)" }} />
              </div>
              <h3 className="dc-landing__feature-title">{f.title}</h3>
              <p className="dc-landing__feature-desc">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
