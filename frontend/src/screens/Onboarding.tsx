import * as React from "react";
import { useNavigate } from "react-router-dom";

import { api } from "@/api";
import type { Program, SessionCode, StudentRecord } from "@/api";
import {
  Button,
  Callout,
  Card,
  Combobox,
  EmptyState,
  ImportPanel,
  ImportPreview,
  PageHeader,
  POStCombinationValidator,
  ProgramCard,
  Select,
  Skeleton,
  Spinner,
  Stepper,
} from "@/ds";

/**
 * Onboarding wizard (`/onboarding`) — design/screens/01-auth-and-onboarding.md.
 *
 * 3 steps in one Stepper: Import your record -> Confirm programs -> Set your
 * term. Data flow:
 *  - Step 1 hits `POST /api/import/pdf` / `/api/import/capture` (per that
 *    doc) directly via `fetch` when a real backend is configured
 *    (`VITE_API_BASE`, see `parseImport` below) — neither endpoint is on the
 *    shared `ApiClient` (src/api/client.ts) yet. Offline/no-backend dev falls
 *    back to `api.getMyRecord()`, the mock adapter's seeded record, so the
 *    wizard still renders and completes end-to-end.
 *  - Step 2 hydrates full `Program`s for the detected codes via
 *    `api.getProgram`, and searches the catalog via `api.getPrograms` for
 *    "add more". The POSt-combination check below is a lightweight local
 *    read of design/09-uoft-degree-rules.md sec. 1-2 (combo type + one-type-
 *    per-subject) — the authoritative validator lives with the degree-audit
 *    surfaces (Dashboard/Plan), not onboarding.
 *  - Step 3 reads `api.getSessions()` for the current-session Select.
 *  - Finish best-effort POSTs to `/api/me/programs` (same "not in ApiClient
 *    yet" situation as import) and always navigates to /dashboard.
 */

type ImportTab = "pdf" | "bookmarklet" | "manual";

const STEP_LABELS = ["Import your record", "Confirm programs", "Set your term"];

const FALLBACK_SESSIONS: SessionCode[] = ["20265", "20269", "20271"];

const API_BASE = import.meta.env.VITE_API_BASE;

/** "20271" -> "Winter 2027" (AGENTS.md glossary: last digit 1=Winter, 5=Summer, 9=Fall). */
function formatSession(code: SessionCode): string {
  const year = code.slice(0, 4);
  const term = code.slice(4);
  const label = term === "1" ? "Winter" : term === "5" ? "Summer" : term === "9" ? "Fall" : "Session";
  return `${label} ${year}`;
}

async function parseImport(payload: { file?: File; capture?: string }): Promise<StudentRecord> {
  if (API_BASE) {
    const form = new FormData();
    if (payload.file) form.append("file", payload.file);
    if (payload.capture) form.append("capture", payload.capture);
    const path = payload.file ? "/import/pdf" : "/import/capture";
    const res = await fetch(`${API_BASE}${path}`, { method: "POST", credentials: "include", body: form });
    if (!res.ok) throw new Error(`Import failed (${res.status})`);
    return (await res.json()) as StudentRecord;
  }
  // No backend configured — fall back to the mock adapter's seeded record so
  // the wizard still renders and completes end-to-end offline.
  return api.getMyRecord();
}

async function persistOnboarding(body: {
  programCodes: string[];
  session: string;
  expectedGraduation: string;
}): Promise<void> {
  if (!API_BASE) return; // Mock mode has nowhere to persist to — non-fatal, mirrors AppLayout's pattern.
  await fetch(`${API_BASE}/me/programs`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).catch(() => {});
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

const loadingRowStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 10,
  padding: "14px 2px",
  color: "var(--text-secondary)",
  fontSize: "var(--text-body-sm)",
};

const footerRowStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  marginTop: 24,
};

export default function Onboarding() {
  const navigate = useNavigate();
  const [step, setStep] = React.useState(0);

  // ---- Step 1: import -------------------------------------------------
  const [tab, setTab] = React.useState<ImportTab>("pdf");
  const [bookmarkletValue, setBookmarkletValue] = React.useState("");
  const [progress, setProgress] = React.useState<number | undefined>(undefined);
  const [parsing, setParsing] = React.useState(false);
  const [importError, setImportError] = React.useState<string | null>(null);
  const [detected, setDetected] = React.useState<StudentRecord | null>(null);
  const progressTimer = React.useRef<number | null>(null);

  React.useEffect(
    () => () => {
      if (progressTimer.current != null) window.clearInterval(progressTimer.current);
    },
    [],
  );

  async function handleImport(payload: { file?: File; capture?: string; blank?: boolean }) {
    setImportError(null);
    if (payload.blank) {
      setDetected({ programs: [], transcript: [], requirementProgress: {}, cgpa: 0 });
      return;
    }
    setParsing(true);
    setProgress(10);
    progressTimer.current = window.setInterval(() => {
      setProgress((p) => (p == null ? 10 : Math.min(90, p + 12)));
    }, 200);
    try {
      const record = await parseImport(payload);
      setProgress(100);
      setDetected(record);
    } catch (err) {
      setImportError(err instanceof Error ? err.message : "Couldn't parse that record. Check the file and try again.");
      setProgress(undefined);
    } finally {
      if (progressTimer.current != null) {
        window.clearInterval(progressTimer.current);
        progressTimer.current = null;
      }
      setParsing(false);
    }
  }

  function onImportTab(nextTab: string) {
    setTab(nextTab as ImportTab);
    setDetected(null);
    setImportError(null);
    setProgress(undefined);
  }

  // ---- Step 2: confirm programs ----------------------------------------
  const [confirmedPrograms, setConfirmedPrograms] = React.useState<Program[]>([]);
  const [programsLoading, setProgramsLoading] = React.useState(false);
  const [programsError, setProgramsError] = React.useState<string | null>(null);
  const [catalog, setCatalog] = React.useState<Program[]>([]);
  const [catalogLoading, setCatalogLoading] = React.useState(false);
  const [catalogError, setCatalogError] = React.useState<string | null>(null);
  const [addValue, setAddValue] = React.useState<string | undefined>(undefined);
  const hydratedFor = React.useRef<StudentRecord | null>(null);
  const catalogFetched = React.useRef(false);

  async function hydrateConfirmedPrograms(record: StudentRecord) {
    setProgramsLoading(true);
    setProgramsError(null);
    try {
      const results = await Promise.all(record.programs.map((p) => api.getProgram(p.code)));
      setConfirmedPrograms(results.filter((p): p is Program => p != null));
    } catch {
      setProgramsError("Couldn't load your programs' details.");
    } finally {
      setProgramsLoading(false);
    }
  }

  React.useEffect(() => {
    if (!detected || hydratedFor.current === detected) return;
    hydratedFor.current = detected;
    void hydrateConfirmedPrograms(detected);
  }, [detected]);

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
    if (step !== 1 || catalogFetched.current) return;
    catalogFetched.current = true;
    void loadCatalog();
  }, [step]);

  function handleAddProgram(code: string | null) {
    if (!code) return;
    const program = catalog.find((p) => p.code === code);
    if (!program) return;
    setConfirmedPrograms((prev) => (prev.some((p) => p.code === code) ? prev : [...prev, program]));
    setAddValue(undefined);
  }

  function handleRemoveProgram(code: string) {
    setConfirmedPrograms((prev) => prev.filter((p) => p.code !== code));
  }

  function earnedFor(code: string): number | undefined {
    const groups = detected?.requirementProgress[code];
    if (!groups) return undefined;
    return groups.reduce((sum, g) => sum + g.earned, 0);
  }

  const combo = React.useMemo(() => validateCombination(confirmedPrograms), [confirmedPrograms]);

  // ---- Step 3: term -----------------------------------------------------
  const [sessions, setSessions] = React.useState<SessionCode[]>([]);
  const [sessionsLoading, setSessionsLoading] = React.useState(false);
  const [sessionsError, setSessionsError] = React.useState<string | null>(null);
  const [session, setSession] = React.useState("");
  const [grad, setGrad] = React.useState("");
  const [finishing, setFinishing] = React.useState(false);
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
    } finally {
      setSessionsLoading(false);
    }
  }

  React.useEffect(() => {
    if (step !== 2 || sessionsFetched.current) return;
    sessionsFetched.current = true;
    void loadSessions();
  }, [step]);

  const effectiveSessions = sessions.length > 0 ? sessions : FALLBACK_SESSIONS;
  const gradOptions = React.useMemo(() => {
    const years = effectiveSessions.map((s) => parseInt(s.slice(0, 4), 10));
    const maxYear = Math.max(...years);
    const opts: { value: string; label: string }[] = [];
    for (let y = maxYear; y <= maxYear + 3; y++) {
      opts.push({ value: `${y}-06`, label: `Spring ${y} Convocation` });
      opts.push({ value: `${y}-11`, label: `Fall ${y} Convocation` });
    }
    return opts;
  }, [effectiveSessions]);

  async function handleFinish() {
    setFinishing(true);
    try {
      await persistOnboarding({ programCodes: confirmedPrograms.map((p) => p.code), session, expectedGraduation: grad });
    } finally {
      setFinishing(false);
      navigate("/dashboard");
    }
  }

  // ---- Render -------------------------------------------------------------

  function renderImportPreview(): React.ReactNode {
    if (importError) {
      return (
        <Callout
          tone="danger"
          title="Couldn't read that record"
          action={
            <Button size="sm" variant="secondary" onClick={() => setImportError(null)}>
              Try again
            </Button>
          }
        >
          {importError}
        </Callout>
      );
    }
    if (parsing) {
      return (
        <div style={loadingRowStyle}>
          <Spinner size={18} />
          <span>Parsing your record…</span>
        </div>
      );
    }
    if (detected) {
      return (
        <ImportPreview
          programs={detected.programs.map((p) => p.name)}
          courseCount={detected.transcript.length}
          cgpa={detected.transcript.length > 0 ? detected.cgpa : undefined}
          onConfirm={() => setStep(1)}
        />
      );
    }
    return null;
  }

  function renderImportStep() {
    return (
      <Card>
        <h2 style={sectionTitleStyle}>Bring in your record</h2>
        <p style={mutedStyle}>
          Import your Degree Explorer PDF, paste a bookmarklet capture, or start blank — parsed locally and encrypted.
        </p>
        <div style={{ marginTop: 16 }}>
          <ImportPanel
            tab={tab}
            onTab={onImportTab}
            onFile={(file) => void handleImport({ file })}
            progress={progress}
            bookmarkletValue={bookmarkletValue}
            onBookmarkletChange={setBookmarkletValue}
            preview={renderImportPreview()}
          />
        </div>
        {tab === "bookmarklet" && !detected && !parsing && (
          <div style={{ marginTop: 12 }}>
            <Button
              variant="primary"
              disabled={!bookmarkletValue.trim()}
              onClick={() => void handleImport({ capture: bookmarkletValue })}
            >
              Parse capture
            </Button>
          </div>
        )}
        {tab === "manual" && !detected && (
          <div style={{ marginTop: 12 }}>
            <Button variant="primary" onClick={() => void handleImport({ blank: true })}>
              Start with an empty record
            </Button>
          </div>
        )}
      </Card>
    );
  }

  function renderProgramsStep() {
    const addOptions = catalog
      .filter((p) => !confirmedPrograms.some((cp) => cp.code === p.code))
      .map((p) => ({ value: p.code, label: `${p.title} (${p.code})` }));

    return (
      <Card>
        <h2 style={sectionTitleStyle}>Confirm your programs</h2>
        <p style={mutedStyle}>These are the programs we found. Remove any that aren't yours, or search to add more.</p>

        {programsError && (
          <div style={{ marginTop: 12 }}>
            <Callout
              tone="danger"
              title="Couldn't load program details"
              action={
                <Button size="sm" variant="secondary" onClick={() => detected && void hydrateConfirmedPrograms(detected)}>
                  Retry
                </Button>
              }
            >
              {programsError}
            </Callout>
          </div>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: 12, margin: "16px 0" }}>
          {programsLoading && [0, 1, 2].map((i) => <Skeleton key={i} height={78} radius="var(--radius-lg)" />)}
          {!programsLoading && confirmedPrograms.length === 0 && (
            <EmptyState
              icon="search"
              title="No programs yet"
              description="Search below to add your Specialist, Major, or Minor."
            />
          )}
          {!programsLoading &&
            confirmedPrograms.map((p) => (
              <ProgramCard
                key={p.code}
                code={p.code}
                name={p.title}
                programType={p.programType || "major"}
                department={p.department}
                earned={earnedFor(p.code)}
                total={p.totalCredits}
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

        {confirmedPrograms.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <POStCombinationValidator valid={combo.valid} message={combo.message} notes={combo.notes} />
          </div>
        )}

        <div style={footerRowStyle}>
          <Button variant="ghost" onClick={() => setStep(0)}>
            Back
          </Button>
          <Button variant="primary" disabled={confirmedPrograms.length === 0} onClick={() => setStep(2)}>
            Next
          </Button>
        </div>
      </Card>
    );
  }

  function renderTermStep() {
    return (
      <Card>
        <h2 style={sectionTitleStyle}>Set your term</h2>
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

        <div style={{ display: "flex", flexDirection: "column", gap: 16, marginTop: 16, maxWidth: 360 }}>
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
          <Select
            label="Expected graduation"
            value={grad}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setGrad(e.target.value)}
            options={gradOptions}
          />
        </div>

        <div style={footerRowStyle}>
          <Button variant="ghost" onClick={() => setStep(1)}>
            Back
          </Button>
          <Button
            variant="primary"
            trailingIcon="arrow-right"
            loading={finishing}
            disabled={!session || !grad}
            onClick={() => void handleFinish()}
          >
            Finish → Dashboard
          </Button>
        </div>
      </Card>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24, maxWidth: 720 }}>
      <PageHeader title="Get started" subtitle="Import your record, confirm your programs, then set your term." />
      <Stepper steps={STEP_LABELS} current={step} />
      {step === 0 && renderImportStep()}
      {step === 1 && renderProgramsStep()}
      {step === 2 && renderTermStep()}
    </div>
  );
}
