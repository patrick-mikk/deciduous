import * as React from "react";
import { useNavigate } from "react-router-dom";

import { api, loadGuestProfile, saveGuestProfile } from "@/api";
import type { Program, SessionCode } from "@/api";
import {
  Button,
  Callout,
  Card,
  Combobox,
  EmptyState,
  PageHeader,
  POStCombinationValidator,
  ProgramCard,
  Select,
  Skeleton,
  Stepper,
  Wordmark,
} from "@/ds";
import "./Onboarding.css";

/**
 * Onboarding wizard (`/onboarding`) — no account required to start or
 * finish. Public route (see App.tsx), chrome-free like Landing.tsx (own
 * header, no AppLayout) since a pre-account visitor has no session for
 * TopBar/SideNav to reflect.
 *
 * 3 steps in one Stepper:
 *  1. "What are you studying?" — search the (public, unauthenticated)
 *     program catalog via `api.getPrograms()`/`api.getProgram()` and add
 *     Specialists/Majors/Minors, validated live by `validateCombination`
 *     below — a pure function of `Program.programType`/`.code` only, so it
 *     runs instantly with no network/account dependency (design/09-uoft-
 *     degree-rules.md sec. 1-2: combo shape + one-type-per-subject).
 *  2. Current term — `api.getSessions()` for a live session Select.
 *  3. A brief "how it works" tour, plus a soft/dismissible nudge to create
 *     an account to sync across devices — never a hard requirement.
 *
 * Finish always saves to `guestProfile` (localStorage, see api/guestProfile.ts)
 * and lands on /dashboard — saving is optional by default; SignUp.tsx picks
 * up this same guest profile and best-effort syncs it into a new account
 * via the existing `api.addMyProgram()` if the visitor later decides to
 * create one from the soft nudge here (or from the "Sign in" link below,
 * for a *returning* visitor who already has an account).
 */

const STEP_LABELS = ["What are you studying?", "Current term", "How it works"];

const FALLBACK_SESSIONS: SessionCode[] = ["20265", "20269", "20271"];

/** "20271" -> "Winter 2027" (AGENTS.md glossary: last digit 1=Winter, 5=Summer, 9=Fall). */
function formatSession(code: SessionCode): string {
  const year = code.slice(0, 4);
  const term = code.slice(4);
  const label = term === "1" ? "Winter" : term === "5" ? "Summer" : term === "9" ? "Fall" : "Session";
  return `${label} ${year}`;
}

/** "ASMAJ2660" -> "2660" (the 4-digit subject id design/09 sec.2's one-type-per-subject rule keys on). */
function subjectKey(code: string): string | null {
  const m = /^AS(?:SPE|MAJ|MIN|FOC|CER)(\d{4})/.exec(code);
  return m ? m[1] : null;
}

interface ComboResult {
  valid: boolean;
  message: string;
  notes: string[];
}

/** design/09-uoft-degree-rules.md sec. 1-2: combo type (1 Specialist / 2 Majors / 1 Major+2 Minors) + one-type-per-subject. */
function validateCombination(programs: Program[]): ComboResult {
  if (programs.length === 0) {
    return { valid: false, message: "Add at least one program to continue.", notes: [] };
  }

  const counts = { specialist: 0, major: 0, minor: 0 };
  for (const p of programs) {
    if (p.programType === "specialist") counts.specialist++;
    else if (p.programType === "major") counts.major++;
    else if (p.programType === "minor") counts.minor++;
  }
  const comboOk = counts.specialist >= 1 || counts.major >= 2 || (counts.major >= 1 && counts.minor >= 2);

  const bySubject = new Map<string, Set<string>>();
  for (const p of programs) {
    const key = subjectKey(p.code);
    if (!key) continue;
    const set = bySubject.get(key) ?? new Set<string>();
    set.add(p.programType);
    bySubject.set(key, set);
  }
  const subjectConflicts: string[] = [];
  for (const [key, types] of bySubject) {
    if (types.size > 1) {
      const names = programs
        .filter((p) => subjectKey(p.code) === key)
        .map((p) => p.title)
        .join(" & ");
      subjectConflicts.push(`${names} share subject area ${key} — only one Specialist/Major/Minor per subject is allowed.`);
    }
  }

  const valid = comboOk && subjectConflicts.length === 0;
  const notes: string[] = [];
  if (!comboOk) notes.push("A degree needs 1 Specialist, or 2 Majors, or 1 Major + 2 Minors.");
  notes.push(...subjectConflicts);

  const parts: string[] = [];
  if (counts.specialist) parts.push(`${counts.specialist} Specialist`);
  if (counts.major) parts.push(`${counts.major} Major${counts.major > 1 ? "s" : ""}`);
  if (counts.minor) parts.push(`${counts.minor} Minor${counts.minor > 1 ? "s" : ""}`);
  const summary = parts.join(" + ") || "No programs yet";
  const message = valid
    ? `Valid combination — ${summary}.`
    : comboOk
      ? "Subject conflict in this combination."
      : `${summary} isn't a complete combination yet.`;

  return { valid, message, notes };
}

const sectionTitleStyle: React.CSSProperties = {
  margin: "0 0 4px",
  fontFamily: "var(--font-serif)",
  fontSize: "var(--text-h3)",
  fontWeight: "var(--weight-semibold)",
  color: "var(--text)",
};

const mutedStyle: React.CSSProperties = {
  margin: 0,
  color: "var(--text-secondary)",
  fontSize: "var(--text-body-sm)",
  lineHeight: "var(--leading-body)",
};

const footerRowStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  marginTop: 24,
};

const TOUR_ITEMS = [
  {
    icon: "layout-list",
    title: "Plan term by term",
    desc: "Drag courses into Fall/Winter/Summer columns — prereqs, exclusions, and offering availability are checked as you go.",
  },
  {
    icon: "list-checks",
    title: "Track what's left",
    desc: "A live degree audit rolls up credits, breadth categories, and program minimums against the real degree rules.",
  },
  {
    icon: "calendar-check-2",
    title: "Build your timetable",
    desc: "Turn a planned term into a conflict-free weekly schedule, with alternatives ranked around the times you want.",
  },
] as const;

export default function Onboarding() {
  const navigate = useNavigate();
  const [step, setStep] = React.useState(0);

  // ---- Step 1: what are you studying? --------------------------------------
  const [myPrograms, setMyPrograms] = React.useState<Program[]>(() => loadGuestProfile()?.programs ?? []);
  const [catalog, setCatalog] = React.useState<Program[]>([]);
  const [catalogLoading, setCatalogLoading] = React.useState(false);
  const [catalogError, setCatalogError] = React.useState<string | null>(null);
  const [addValue, setAddValue] = React.useState<string | undefined>(undefined);
  const catalogFetched = React.useRef(false);

  async function loadCatalog() {
    setCatalogLoading(true);
    setCatalogError(null);
    try {
      setCatalog(await api.getPrograms());
    } catch {
      setCatalogError("Couldn't load the program catalog search.");
    } finally {
      setCatalogLoading(false);
    }
  }

  React.useEffect(() => {
    if (catalogFetched.current) return;
    catalogFetched.current = true;
    void loadCatalog();
  }, []);

  function handleAddProgram(code: string | null) {
    if (!code) return;
    const program = catalog.find((p) => p.code === code);
    if (!program) return;
    setMyPrograms((prev) => (prev.some((p) => p.code === code) ? prev : [...prev, program]));
    setAddValue(undefined);
  }

  function handleRemoveProgram(code: string) {
    setMyPrograms((prev) => prev.filter((p) => p.code !== code));
  }

  const combo = React.useMemo(() => validateCombination(myPrograms), [myPrograms]);

  // ---- Step 2: current term ------------------------------------------------
  const [sessions, setSessions] = React.useState<SessionCode[]>([]);
  const [sessionsLoading, setSessionsLoading] = React.useState(false);
  const [sessionsError, setSessionsError] = React.useState<string | null>(null);
  const [session, setSession] = React.useState(() => loadGuestProfile()?.session ?? "");
  const sessionsFetched = React.useRef(false);

  async function loadSessions() {
    setSessionsLoading(true);
    setSessionsError(null);
    try {
      const list = await api.getSessions();
      setSessions(list);
      setSession((prev) => prev || list[0] || "");
    } catch {
      setSessionsError("Couldn't load live sessions — showing defaults.");
      // The Select below still renders FALLBACK_SESSIONS on error, so the
      // tracked value must default too, or "Next" (gated on `!session`)
      // stays disabled forever despite a session visibly being selected.
      setSession((prev) => prev || FALLBACK_SESSIONS[0]);
    } finally {
      setSessionsLoading(false);
    }
  }

  React.useEffect(() => {
    if (step !== 1 || sessionsFetched.current) return;
    sessionsFetched.current = true;
    void loadSessions();
  }, [step]);

  const effectiveSessions = sessions.length > 0 ? sessions : FALLBACK_SESSIONS;

  // ---- Step 3: tour + finish ------------------------------------------------
  const [syncPromptDismissed, setSyncPromptDismissed] = React.useState(false);

  function persistGuestProfile() {
    saveGuestProfile({ programs: myPrograms, session: session || null });
  }

  function handleFinish() {
    persistGuestProfile();
    navigate("/dashboard");
  }

  /** The sync-nudge's "Create account" also needs the in-progress selections
   * saved first — SignUp.tsx reads this same guest profile to sync it into
   * the new account, and this button navigates away before "Start planning"
   * (handleFinish) would otherwise have saved it. */
  function handleCreateAccount() {
    persistGuestProfile();
    navigate("/signup");
  }

  // ---- Render ---------------------------------------------------------------

  function renderProgramsStep() {
    const addOptions = catalog
      .filter((p) => !myPrograms.some((mp) => mp.code === p.code))
      .map((p) => ({ value: p.code, label: `${p.title} (${p.code})` }));

    return (
      <Card>
        <h2 style={sectionTitleStyle}>What are you studying?</h2>
        <p style={mutedStyle}>
          Search and add every Specialist, Major, and Minor you're pursuing (or exploring) — we'll flag
          combination issues as you go.
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: 12, margin: "16px 0" }}>
          {catalogLoading && myPrograms.length === 0 && [0, 1].map((i) => <Skeleton key={i} height={78} radius="var(--radius-lg)" />)}
          {myPrograms.length === 0 && !catalogLoading && (
            <EmptyState
              icon="search"
              title="No programs yet"
              description="Search below to add your Specialist, Major, or Minor."
            />
          )}
          {myPrograms.map((p) => (
            <ProgramCard
              key={p.code}
              code={p.code}
              name={p.title}
              programType={p.programType || "major"}
              department={p.department}
              enrolled
              onRemove={() => handleRemoveProgram(p.code)}
            />
          ))}
        </div>

        {catalogError && (
          <div style={{ marginBottom: 12 }}>
            <Callout
              tone="warning"
              title="Program search unavailable"
              action={
                <Button size="sm" variant="secondary" onClick={() => void loadCatalog()}>
                  Retry
                </Button>
              }
            >
              {catalogError} You can still continue with the programs above.
            </Callout>
          </div>
        )}
        <Combobox
          label="Add a program"
          options={addOptions}
          value={addValue}
          onChange={handleAddProgram}
          placeholder={catalogLoading ? "Loading programs…" : "Search programs…"}
          clearable
        />

        {myPrograms.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <POStCombinationValidator valid={combo.valid} message={combo.message} notes={combo.notes} />
          </div>
        )}

        <div style={footerRowStyle}>
          <div />
          <Button variant="primary" disabled={myPrograms.length === 0} onClick={() => setStep(1)}>
            Next
          </Button>
        </div>
      </Card>
    );
  }

  function renderTermStep() {
    return (
      <Card>
        <h2 style={sectionTitleStyle}>What term are you in?</h2>
        <p style={mutedStyle}>We'll use this to show what's enrolling now and to plan your remaining terms.</p>

        {sessionsError && (
          <div style={{ marginTop: 12 }}>
            <Callout
              tone="warning"
              title="Using default sessions"
              action={
                <Button size="sm" variant="secondary" onClick={() => void loadSessions()}>
                  Retry
                </Button>
              }
            >
              {sessionsError}
            </Callout>
          </div>
        )}

        <div style={{ marginTop: 16, maxWidth: 360 }}>
          {sessionsLoading ? (
            <Skeleton height={62} radius="var(--radius-md)" />
          ) : (
            <Select
              label="Current session"
              value={session}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSession(e.target.value)}
              options={effectiveSessions.map((s) => ({ value: s, label: formatSession(s) }))}
            />
          )}
        </div>

        <div style={footerRowStyle}>
          <Button variant="ghost" onClick={() => setStep(0)}>
            Back
          </Button>
          <Button variant="primary" disabled={!session} onClick={() => setStep(2)}>
            Next
          </Button>
        </div>
      </Card>
    );
  }

  function renderTourStep() {
    return (
      <Card>
        <h2 style={sectionTitleStyle}>How Deciduous works</h2>
        <p style={mutedStyle}>A quick look at what you can do next.</p>

        <div style={{ display: "flex", flexDirection: "column", gap: 16, margin: "20px 0" }}>
          {TOUR_ITEMS.map((item) => (
            <div key={item.title} style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
              <div
                style={{
                  width: 40,
                  height: 40,
                  flexShrink: 0,
                  borderRadius: "var(--radius-md)",
                  background: "var(--primary-bg)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <i data-lucide={item.icon} style={{ width: 20, height: 20, color: "var(--primary)" }} />
              </div>
              <div>
                <div style={{ fontSize: "var(--text-body)", fontWeight: "var(--weight-semibold)", color: "var(--text)" }}>
                  {item.title}
                </div>
                <p style={{ ...mutedStyle, marginTop: 2 }}>{item.desc}</p>
              </div>
            </div>
          ))}
        </div>

        {!syncPromptDismissed && (
          <Callout
            tone="info"
            title="Create a free account to sync across devices"
            action={
              <div style={{ display: "flex", gap: 8 }}>
                <Button size="sm" variant="secondary" onClick={() => setSyncPromptDismissed(true)}>
                  Not now
                </Button>
                <Button size="sm" variant="primary" onClick={handleCreateAccount}>
                  Create account
                </Button>
              </div>
            }
          >
            Your programs and term are saved on this device only. Creating a free account keeps them
            backed up and synced everywhere you sign in — entirely optional.
          </Callout>
        )}

        <div style={footerRowStyle}>
          <Button variant="ghost" onClick={() => setStep(1)}>
            Back
          </Button>
          <Button variant="primary" trailingIcon="arrow-right" onClick={handleFinish}>
            Start planning
          </Button>
        </div>
      </Card>
    );
  }

  return (
    <div className="dc-onboarding">
      <header className="dc-onboarding__header">
        <Wordmark size={22} />
        <Button variant="link" size="sm" onClick={() => navigate("/signin")}>
          Already have a saved plan? Sign in to restore it
        </Button>
      </header>
      <div className="dc-onboarding__body">
        <PageHeader title="Get started" subtitle="Tell us what you're studying, then take a quick look around." />
        <Stepper steps={STEP_LABELS} current={step} />
        {step === 0 && renderProgramsStep()}
        {step === 1 && renderTermStep()}
        {step === 2 && renderTourStep()}
      </div>
    </div>
  );
}
