import * as React from "react";
import { useNavigate } from "react-router-dom";

import { API_BASE, api, ensureCsrfToken, loadGuestProfile, saveGuestProfile } from "@/api";
import type { Program, SessionCode } from "@/api";
import {
  Button,
  Callout,
  Card,
  Combobox,
  Dropzone,
  EmptyState,
  PageHeader,
  POStCombinationValidator,
  ProgramCard,
  Select,
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
 * 4 steps in one Stepper:
 *  1. "What are you studying?" — search the (public, unauthenticated)
 *     program catalog via `api.getPrograms()`/`api.getProgram()` and add
 *     Specialists/Majors/Minors, validated live by `validateCombination`
 *     below — a pure function of `Program.programType`/`.code` only, so it
 *     runs instantly with no network/account dependency (design/09-uoft-
 *     degree-rules.md sec. 1-2: combo shape + one-type-per-subject).
 *  2. "When did you start at UofT?" — a Select of Fall start terms built
 *     purely from today's date (see `fallSessionCode` below), no network
 *     call needed for past years.
 *  3. "Do you have existing credits?" — upload your Academic History PDF
 *     from ACORN (`POST /api/import/pdf`), say you'll enter courses by hand
 *     (routes to /transcript instead of /dashboard on finish), or skip for now.
 *  4. A brief "how it works" tour of the dashboard you're about to land on,
 *     plus a soft/dismissible nudge to create an account to sync across
 *     devices — never a hard requirement.
 *
 * Finish always saves to `guestProfile` (localStorage, see api/guestProfile.ts)
 * and lands on /dashboard (or /transcript, for the "enter manually" choice
 * above) — saving there is unconditional and never fails silently caused by
 * storage errors (see `saveGuestProfile`'s own try/catch).
 *
 * On top of that, finish also best-effort syncs the selected programs to the
 * server via `api.addMyProgram()` (see `syncProgramsToServer` below) — this
 * screen is reachable by a visitor who already has a live, authenticated
 * session (a returning signed-in user landing here again, or the dev-only
 * auth bypass in `backend/dev_auth.py` which auto-authenticates *every*
 * `/api/*` request outside production, including the plain `GET /api/programs`
 * catalog search this screen issues on mount). For that visitor, saving only
 * to `guestProfile` would silently never reach `ProgramEnrolment` — "My
 * Programs" would read back empty even though onboarding "finished" — so
 * finish also POSTs each program to `/api/me/programs`. A 401 there means
 * there really is no session (the common case: a fresh, unauthenticated
 * visitor), and is treated as the normal guest flow with no error shown;
 * `guestProfile` stays the source of truth until `SignUp.tsx` syncs it into a
 * new account the same way, via the same `api.addMyProgram()` call.
 */

const STEP_LABELS = ["What are you studying?", "Start term", "Existing credits", "How it works"];

/** Program-search grouping: the three degree-program types get their own
 * sections (design/09 sec. 2's combination rules only involve these), and
 * everything else — Focus clusters, Certificates, unrecognized types — sits
 * under a collapsed "Other" so it doesn't bury the common choices. */
const PROGRAM_TYPE_GROUPS: Record<string, string> = {
  major: "Majors",
  specialist: "Specialists",
  minor: "Minors",
};
const PROGRAM_GROUP_ORDER = ["Majors", "Specialists", "Minors", "Other"];

/**
 * Session code for the Fall term of a given calendar year, per AGENTS.md's
 * glossary: `20269`=Fall 2026, `20271`=Winter 2027, `20265`=Summer 2026. In
 * each example the first 4 digits are "20" + the *term's own* 2-digit
 * calendar year, and the 5th digit picks the term within that year (1=Winter,
 * 5=Summer, 9=Fall). So Fall of year Y is `20{YY}9` where YY = Y's last two
 * digits — a formula applied to whatever year is passed in, not a hard-coded
 * session.
 */
function fallSessionCode(year: number): SessionCode {
  return `20${String(year).slice(-2)}9`;
}

/** "20271" -> "Winter 2027" (AGENTS.md glossary: last digit 1=Winter, 5=Summer, 9=Fall). */
function formatSession(code: SessionCode): string {
  const year = code.slice(0, 4);
  const term = code.slice(4);
  const label = term === "1" ? "Winter" : term === "5" ? "Summer" : term === "9" ? "Fall" : "Session";
  return `${label} ${year}`;
}

const START_TERM_YEARS_BACK = 7; // Fall {thisYear-7} .. Fall {thisYear}, derived from today's date below.

/** Options for the "When did you start at UofT?" Select — built from `new Date()`, not fetched. */
function buildStartTermOptions(): { value: string; label: string }[] {
  const thisYear = new Date().getFullYear();
  const options = [{ value: "", label: "Starting this year / haven't started yet" }];
  for (let yearsAgo = START_TERM_YEARS_BACK; yearsAgo >= 0; yearsAgo--) {
    const code = fallSessionCode(thisYear - yearsAgo);
    options.push({ value: code, label: formatSession(code) });
  }
  return options;
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
      subjectConflicts.push(`${names} share subject area ${key}. Only one Specialist/Major/Minor per subject is allowed.`);
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
    ? `Valid combination: ${summary}.`
    : comboOk
      ? "Subject conflict in this combination."
      : `${summary} isn't a complete combination yet.`;

  return { valid, message, notes };
}

interface ImportPdfResult {
  courseCount?: number;
}

/**
 * `POST /api/import/pdf` (backend/api/import_.py) — multipart `file` field,
 * same double-submit CSRF header as SignUp.tsx's direct fetch to
 * `/auth/signup`. The route is `@require_auth`, so a guest visitor (the norm
 * on this screen) gets a 401 back; that's surfaced as the "AUTH_REQUIRED"
 * error message so the credits step can show the "create an account" nudge
 * instead of a generic failure.
 */
async function importDegreeExplorerPdf(file: File): Promise<ImportPdfResult> {
  if (!API_BASE) {
    // Mock adapter opted in (`VITE_API_BASE=mock`) — simulate so the step still renders.
    await new Promise((resolve) => setTimeout(resolve, 500));
    return { courseCount: 24 };
  }
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/import/pdf`, {
    method: "POST",
    credentials: "include",
    headers: { "X-CSRF-Token": await ensureCsrfToken() },
    body: form,
  });
  if (res.status === 401) throw new Error("AUTH_REQUIRED");
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error((body && (body.error || body.message)) || "Couldn't import that PDF.");
  }
  return res.json();
}

/**
 * Best-effort push `programs` into the signed-in visitor's account via the
 * existing `POST /api/me/programs` (same call `SignUp.tsx` and `Programs.tsx`
 * already use), so onboarding's selections reach `ProgramEnrolment` whenever
 * there's a live session to attach them to — not just `guestProfile`. Returns
 * a message to surface (non-blocking) if something genuinely failed, or
 * `null` if there's nothing to report (nothing to sync, everything synced,
 * or — the common case — the visitor is a guest with no session at all).
 *
 * `http()` (src/api/client.ts) throws `Error("API error <status>: ...")` on a
 * non-2xx response, so the status is recovered from the message text here
 * rather than needing a client.ts change (out of scope for this fix):
 *  - 401: no session to sync to — this is the normal, account-optional guest
 *    flow (see this module's header comment), not an error.
 *  - 409: already enrolled, or a one-type-per-subject conflict the backend
 *    caught — `validateCombination` above should keep the latter from
 *    happening, and the former is harmless (the program is already there).
 *  - anything else (422 malformed code, 5xx, network failure): a real sync
 *    failure worth telling the signed-in visitor about.
 */
async function syncProgramsToServer(programs: Program[]): Promise<string | null> {
  if (programs.length === 0) return null;

  const results = await Promise.allSettled(programs.map((p) => api.addMyProgram(p.code)));
  const failures = programs
    .map((program, i) => ({ program, result: results[i] }))
    .filter((f): f is { program: Program; result: PromiseRejectedResult } => f.result.status === "rejected");
  if (failures.length === 0) return null;

  const statusOf = (reason: unknown): number | null => {
    const match = reason instanceof Error ? /API error (\d+):/.exec(reason.message) : null;
    return match ? Number(match[1]) : null;
  };

  // Every failure a 401 => no session at all, i.e. a guest visitor — expected,
  // not an error (guestProfile is already saved and is this visitor's source
  // of truth until they create an account).
  if (failures.every((f) => statusOf(f.result.reason) === 401)) return null;

  const realFailures = failures.filter((f) => statusOf(f.result.reason) !== 409);
  if (realFailures.length === 0) return null;

  const names = realFailures.map((f) => f.program.title).join(", ");
  return (
    `Couldn't save ${realFailures.length === 1 ? "one program" : `${realFailures.length} programs`} ` +
    `(${names}) to your account. They're still saved on this device. You can retry from My Programs.`
  );
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
    icon: "graduation-cap",
    title: "Credit progress at a glance",
    desc: "Your dashboard tracks total credits earned toward the 20.0 you need to graduate, alongside your CGPA and standing.",
  },
  {
    icon: "list-checks",
    title: "Breadth coverage, mapped",
    desc: "A breadth spectrum shows how you're doing across all five categories (BR1–5), so gaps are obvious early.",
  },
  {
    icon: "bell",
    title: "Next actions, front and center",
    desc: "Alerts and a next-actions checklist flag deadlines, prereq issues, and seats worth grabbing before they fill.",
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
      setCatalog(await api.getAllPrograms());
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

  // ---- Step 2: when did you start? -----------------------------------------
  const [startSession, setStartSession] = React.useState<string>(() => loadGuestProfile()?.startSession ?? "");
  const startTermOptions = React.useMemo(() => buildStartTermOptions(), []);

  // ---- Step 3: existing credits ---------------------------------------------
  const [creditsChoice, setCreditsChoice] = React.useState<"undecided" | "manual" | "skip">("undecided");
  const [importStatus, setImportStatus] = React.useState<"idle" | "uploading" | "success" | "auth-error" | "error">(
    "idle",
  );
  const [importCourseCount, setImportCourseCount] = React.useState<number | null>(null);
  const [importErrorMessage, setImportErrorMessage] = React.useState<string | null>(null);

  async function handleImportPdf(file: File) {
    setImportStatus("uploading");
    setImportErrorMessage(null);
    try {
      const result = await importDegreeExplorerPdf(file);
      setImportCourseCount(typeof result.courseCount === "number" ? result.courseCount : null);
      setImportStatus("success");
    } catch (err) {
      if (err instanceof Error && err.message === "AUTH_REQUIRED") {
        setImportStatus("auth-error");
      } else {
        setImportErrorMessage(err instanceof Error ? err.message : "Couldn't import that PDF.");
        setImportStatus("error");
      }
    }
  }

  function handleManualEntry() {
    setCreditsChoice("manual");
    setStep(3);
  }

  function handleSkipCredits() {
    setCreditsChoice("skip");
    setStep(3);
  }

  // ---- Step 4: tour + finish --------------------------------------------------
  const [syncPromptDismissed, setSyncPromptDismissed] = React.useState(false);
  const [finishing, setFinishing] = React.useState(false);
  const [syncErrorMessage, setSyncErrorMessage] = React.useState<string | null>(null);

  function persistGuestProfile() {
    saveGuestProfile({ programs: myPrograms, startSession: startSession || null });
  }

  function goToLanding() {
    navigate(creditsChoice === "manual" ? "/transcript" : "/dashboard");
  }

  /** `guestProfile` is saved unconditionally either way (see module doc
   * comment); a signed-in visitor (returning user, or the dev auth bypass —
   * see `syncProgramsToServer`) also gets a best-effort push to the server so
   * "My Programs" isn't silently empty on the very next screen. A real sync
   * failure doesn't block navigation — it's surfaced via `syncErrorMessage`
   * and the visitor can continue past it (see `renderTourStep`) rather than
   * getting stuck here. */
  async function handleFinish() {
    persistGuestProfile();
    setFinishing(true);
    setSyncErrorMessage(null);
    const message = await syncProgramsToServer(myPrograms).catch(() => null);
    setFinishing(false);
    if (message) {
      setSyncErrorMessage(message);
      return;
    }
    goToLanding();
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
    // Group the search results by program type so common choices lead and
    // niche types (Focus clusters, Certificates, anything unrecognized) sit
    // behind a collapsed "Other" section instead of burying the flat list.
    const addOptions = catalog
      .filter((p) => !myPrograms.some((mp) => mp.code === p.code))
      .map((p) => ({
        value: p.code,
        label: `${p.title} (${p.code})`,
        group: PROGRAM_TYPE_GROUPS[p.programType] ?? "Other",
      }))
      .sort((a, b) => a.label.localeCompare(b.label));

    return (
      <Card>
        <h2 style={sectionTitleStyle}>What are you studying?</h2>
        <p style={mutedStyle}>Search and add your programs.</p>

        <div style={{ display: "flex", flexDirection: "column", gap: 12, margin: "16px 0" }}>
          {/* myPrograms is synchronous (localStorage, not a fetch), so there's
              no loading state for it — the empty state shows immediately.
              catalogLoading only gates the "add a program" Combobox below. */}
          {myPrograms.length === 0 && (
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
          groupOrder={PROGRAM_GROUP_ORDER}
          collapsedGroup="Other"
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
        <h2 style={sectionTitleStyle}>When did you start at UofT?</h2>
        <p style={mutedStyle}>We'll use this to figure out what's left and to plan your remaining terms.</p>

        <div style={{ marginTop: 16, maxWidth: 360 }}>
          <Select
            label="Start term"
            value={startSession}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setStartSession(e.target.value)}
            options={startTermOptions}
          />
        </div>

        <div style={footerRowStyle}>
          <Button variant="ghost" onClick={() => setStep(0)}>
            Back
          </Button>
          <Button variant="primary" onClick={() => setStep(2)}>
            Next
          </Button>
        </div>
      </Card>
    );
  }

  function renderCreditsStep() {
    return (
      <Card>
        <h2 style={sectionTitleStyle}>Do you have existing credits?</h2>
        <p style={mutedStyle}>
          Bring in what you've already completed, or skip this for now. You can always import later from Settings.
        </p>

        <div style={{ marginTop: "var(--space-4)" }}>
          <div
            style={{
              fontSize: "var(--text-body)",
              fontWeight: "var(--weight-semibold)",
              color: "var(--text)",
              marginBottom: "var(--space-2)",
            }}
          >
            Upload your Academic History PDF
          </div>
          <Dropzone
            label="Drop your Academic History PDF here"
            hint="from ACORN, parsed and encrypted on import"
            accept="application/pdf"
            onFile={(file: File) => void handleImportPdf(file)}
            progress={importStatus === "uploading" ? 60 : undefined}
          />

          {importStatus === "success" && (
            <div style={{ marginTop: "var(--space-3)" }}>
              <Callout
                tone="success"
                title="Import complete"
                action={
                  <Button size="sm" variant="primary" onClick={() => setStep(3)}>
                    Continue
                  </Button>
                }
              >
                {importCourseCount != null
                  ? `Found ${importCourseCount} course${importCourseCount === 1 ? "" : "s"} on your record.`
                  : "Your record was imported."}
              </Callout>
            </div>
          )}

          {importStatus === "auth-error" && (
            <div style={{ marginTop: "var(--space-3)" }}>
              <Callout
                tone="info"
                title="Create an account to save imported credits"
                action={
                  <Button size="sm" variant="primary" onClick={handleCreateAccount}>
                    Create account
                  </Button>
                }
              >
                You're browsing as a guest, so there's nowhere to save an import yet. Create a free account, then
                re-import from Settings.
              </Callout>
            </div>
          )}

          {importStatus === "error" && (
            <div style={{ marginTop: "var(--space-3)" }}>
              <Callout tone="danger" title="Couldn't import that PDF">
                {importErrorMessage}
              </Callout>
            </div>
          )}
        </div>

        <div style={footerRowStyle}>
          <Button variant="ghost" onClick={() => setStep(1)}>
            Back
          </Button>
          <div style={{ display: "flex", gap: "var(--space-2)" }}>
            <Button variant="secondary" icon="pencil" onClick={handleManualEntry}>
              I'll enter courses manually
            </Button>
            <Button variant="primary" onClick={handleSkipCredits}>
              Skip for now
            </Button>
          </div>
        </div>
      </Card>
    );
  }

  function renderTourStep() {
    return (
      <Card>
        <h2 style={sectionTitleStyle}>How Deciduous works</h2>
        <p style={mutedStyle}>A quick look at what you can do next.</p>

        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)", margin: "var(--space-5) 0" }}>
          {TOUR_ITEMS.map((item) => (
            <div key={item.title} style={{ display: "flex", gap: "var(--space-3)", alignItems: "flex-start" }}>
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
                <p style={{ ...mutedStyle, marginTop: "var(--space-1)" }}>{item.desc}</p>
              </div>
            </div>
          ))}
        </div>

        {syncErrorMessage && (
          <div style={{ marginBottom: "var(--space-4)" }}>
            <Callout
              tone="warning"
              title="Couldn't sync your programs to your account"
              action={
                <Button size="sm" variant="primary" onClick={goToLanding}>
                  Continue anyway
                </Button>
              }
            >
              {syncErrorMessage}
            </Callout>
          </div>
        )}

        {!syncPromptDismissed && (
          <Callout
            tone="info"
            title="Create a free account to sync across devices"
            action={
              <div style={{ display: "flex", gap: "var(--space-2)" }}>
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
            backed up and synced everywhere you sign in, entirely optional.
          </Callout>
        )}

        <div style={footerRowStyle}>
          <Button variant="ghost" onClick={() => setStep(2)}>
            Back
          </Button>
          <Button variant="primary" trailingIcon="arrow-right" loading={finishing} onClick={() => void handleFinish()}>
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
        {step === 2 && renderCreditsStep()}
        {step === 3 && renderTourStep()}
      </div>
    </div>
  );
}
