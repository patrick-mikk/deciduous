import * as React from "react";
import { useNavigate } from "react-router-dom";

import {
  Button,
  Callout,
  Card,
  DangerZone,
  DataExportMenu,
  DensityToggle,
  Dialog,
  Divider,
  Input,
  PageHeader,
  PasswordField,
  RecoveryCodeCard,
  Select,
  ShareLinkDialog,
  Skeleton,
  StrengthMeter,
  Switch,
  Tabs,
  ThemeToggle,
  Toast,
} from "@/ds";
import { api, isAuthError } from "@/api";
import type { SessionCode } from "@/api";
import { GuestCallout } from "@/components/GuestCallout";
import { useTheme } from "@/theme/ThemeProvider";

/**
 * Settings (design/screens/05-transcript-settings-share.md "Settings"),
 * tabbed: Profile / Security / Data / Appearance / Notifications. Only
 * Appearance (theme/density/leaf-motion) and Notifications persist anywhere
 * real (localStorage) — the typed ApiClient has no profile/password/
 * notification-preference endpoints yet, so those tabs demo the interaction
 * with local component state and a confirmation Toast rather than pretending
 * to call a backend that doesn't exist.
 */

type TabKey = "profile" | "security" | "data" | "appearance" | "notifications";

function useLocalStorage<T>(key: string, initial: T): [T, (v: T) => void] {
  const [value, setValue] = React.useState<T>(() => {
    try {
      const raw = window.localStorage.getItem(key);
      return raw != null ? (JSON.parse(raw) as T) : initial;
    } catch {
      return initial;
    }
  });
  const set = React.useCallback(
    (v: T) => {
      setValue(v);
      try {
        window.localStorage.setItem(key, JSON.stringify(v));
      } catch {
        // ignore quota / privacy-mode failures — appearance/notification prefs are non-critical
      }
    },
    [key],
  );
  return [value, set];
}

function randomRecoveryCode(): string {
  const groups = Array.from({ length: 3 }, () => Math.random().toString(36).slice(2, 6).toUpperCase());
  return groups.join("-");
}

export default function Settings() {
  const navigate = useNavigate();
  const { theme, isExplicit, setTheme, followSystem } = useTheme();

  const [tab, setTab] = React.useState<TabKey>("profile");
  const [toast, setToast] = React.useState<string | null>(null);

  const [sessions, setSessions] = React.useState<SessionCode[] | null>(null);
  const [sessionsError, setSessionsError] = React.useState<string | null>(null);

  const [name, setName] = React.useState("Priya Sharma");
  const [email, setEmail] = React.useState("priya.sharma@mail.utoronto.ca");
  const [currentSession, setCurrentSession] = React.useState("");
  const [expectedGrad, setExpectedGrad] = React.useState("2027-06");

  const [currentPassword, setCurrentPassword] = React.useState("");
  const [newPassword, setNewPassword] = React.useState("");
  const [recoveryCode, setRecoveryCode] = React.useState(() => randomRecoveryCode());

  const [shareOpen, setShareOpen] = React.useState(false);
  const [shareUrl, setShareUrl] = React.useState<string | null>(null);
  /** `POST /api/share` is `@require_auth` — a guest gets a 401. Shown as the
   * shared sign-up nudge on the Data tab, not as "couldn't generate a link". */
  const [shareNeedsAccount, setShareNeedsAccount] = React.useState(false);

  const [density, setDensity] = useLocalStorage<"comfortable" | "compact">("deciduous:density", "comfortable");
  const [leafMotion, setLeafMotion] = useLocalStorage<boolean>("deciduous:leaf-motion", true);
  const [notifyDeadlines, setNotifyDeadlines] = useLocalStorage<boolean>("deciduous:notify-deadlines", true);
  const [notifyPrereq, setNotifyPrereq] = useLocalStorage<boolean>("deciduous:notify-prereq", true);
  const [notifySeats, setNotifySeats] = useLocalStorage<boolean>("deciduous:notify-seats", false);

  React.useEffect(() => {
    api
      .getSessions()
      .then((s) => {
        setSessions(s);
        setCurrentSession((prev) => prev || s[s.length - 1] || "");
      })
      .catch((e: unknown) => setSessionsError(e instanceof Error ? e.message : "Failed to load sessions."));
  }, []);

  React.useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 2600);
    return () => clearTimeout(t);
  }, [toast]);

  function themeToggleValue(): "light" | "dark" | "system" {
    return isExplicit ? theme : "system";
  }

  function onThemeChange(v: string) {
    if (v === "system") followSystem();
    else setTheme(v as "light" | "dark");
  }

  function openShare() {
    setShareOpen(true);
    setShareNeedsAccount(false);
    if (!shareUrl) {
      api
        .createShareLink()
        .then((r) => setShareUrl(r.url))
        .catch((err: unknown) => {
          if (isAuthError(err)) {
            // Don't strand the visitor in a dialog showing an empty link —
            // close it and explain on the tab behind it.
            setShareOpen(false);
            setShareNeedsAccount(true);
            return;
          }
          setToast("Couldn't generate a share link.");
        });
    }
  }

  return (
    <>
      <PageHeader title="Settings" subtitle="Account, data, appearance, and notification preferences." />

      <Tabs
        tabs={[
          { label: "Profile", value: "profile" },
          { label: "Security", value: "security" },
          { label: "Data", value: "data" },
          { label: "Appearance", value: "appearance" },
          { label: "Notifications", value: "notifications" },
        ]}
        active={tab}
        onChange={(v: string) => setTab(v as TabKey)}
      />

      <div style={{ marginTop: 20 }}>
        {tab === "profile" && (
          <Card>
            <div style={{ display: "flex", flexDirection: "column", gap: 14, maxWidth: 420 }}>
              <Input label="Name" value={name} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setName(e.target.value)} />
              <Input label="Email" type="email" value={email} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmail(e.target.value)} />
              {sessionsError ? (
                <Callout tone="danger">{sessionsError}</Callout>
              ) : sessions == null ? (
                <Skeleton height={62} />
              ) : (
                <Select
                  label="Current session"
                  value={currentSession}
                  onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setCurrentSession(e.target.value)}
                  options={sessions.map((s) => ({ label: s, value: s }))}
                />
              )}
              <Input
                label="Expected graduation"
                type="month"
                value={expectedGrad}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setExpectedGrad(e.target.value)}
              />
              <div>
                <Button onClick={() => setToast("Profile updated.")}>Save profile</Button>
              </div>
            </div>
          </Card>
        )}

        {tab === "security" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <Card>
              <div style={{ fontSize: "var(--text-h3)", fontWeight: "var(--weight-bold)", color: "var(--text)", marginBottom: 12 }}>
                Change password
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 12, maxWidth: 360 }}>
                <PasswordField
                  label="Current password"
                  value={currentPassword}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCurrentPassword(e.target.value)}
                />
                <PasswordField
                  label="New password"
                  value={newPassword}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewPassword(e.target.value)}
                  showStrength
                />
                <StrengthMeter password={newPassword} />
                <Callout tone="info">
                  Changing your password re-encrypts your academic data with your recovery code. Keep it somewhere safe first.
                </Callout>
                <div>
                  <Button
                    disabled={!currentPassword || !newPassword}
                    onClick={() => {
                      setCurrentPassword("");
                      setNewPassword("");
                      setToast("Password updated.");
                    }}
                  >
                    Update password
                  </Button>
                </div>
              </div>
            </Card>

            <RecoveryCodeCard
              code={recoveryCode}
              onCopy={() => setToast("Recovery code copied.")}
              onRegenerate={() => {
                setRecoveryCode(randomRecoveryCode());
                setToast("Recovery code regenerated. The old code no longer works.");
              }}
            />

            <Card>
              <div style={{ fontSize: "var(--text-h3)", fontWeight: "var(--weight-bold)", color: "var(--text)", marginBottom: 12 }}>
                Active sessions
              </div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 0" }}>
                <div>
                  <div style={{ fontSize: "var(--text-body)", color: "var(--text)" }}>This device</div>
                  <div style={{ fontSize: "var(--text-body-sm)", color: "var(--text-tertiary)" }}>Current session</div>
                </div>
                <Button variant="secondary" size="sm" disabled>
                  Current
                </Button>
              </div>
            </Card>
          </div>
        )}

        {tab === "data" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            {shareNeedsAccount && (
              <GuestCallout title="Create an account to share your plan">
                A share link points at a saved plan, so there's nothing to publish while you're browsing as a guest.
              </GuestCallout>
            )}
            <Card>
              <div style={{ fontSize: "var(--text-h3)", fontWeight: "var(--weight-bold)", color: "var(--text)", marginBottom: 12 }}>
                Import & export
              </div>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                <Button variant="secondary" icon="upload" onClick={() => navigate("/onboarding")}>
                  Re-import record
                </Button>
                <DataExportMenu onExport={(kind: string) => setToast(`Exported as ${kind.toUpperCase()} (demo, no backend export yet).`)} />
                <Button variant="secondary" icon="link" onClick={openShare}>
                  Share plan
                </Button>
              </div>
            </Card>

            <Divider label="Danger zone" />

            <DangerZone
              onDelete={() => {
                setToast("Account deletion requested (demo).");
                navigate("/");
              }}
            />
          </div>
        )}

        {tab === "appearance" && (
          <Card>
            <div style={{ display: "flex", flexDirection: "column", gap: 20, maxWidth: 420 }}>
              <div>
                <div style={{ fontSize: "var(--text-body-sm)", fontWeight: "var(--weight-medium)", color: "var(--text-secondary)", marginBottom: 8 }}>
                  Theme
                </div>
                <ThemeToggle value={themeToggleValue()} onChange={onThemeChange} showLabels />
              </div>
              <div>
                <div style={{ fontSize: "var(--text-body-sm)", fontWeight: "var(--weight-medium)", color: "var(--text-secondary)", marginBottom: 8 }}>
                  Density
                </div>
                <DensityToggle value={density} onChange={(v: "comfortable" | "compact") => setDensity(v)} />
              </div>
              <Switch label="Leaf-canopy motion in progress cards" checked={leafMotion} onChange={setLeafMotion} />
            </div>
          </Card>
        )}

        {tab === "notifications" && (
          <Card>
            <div style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 420 }}>
              <Switch label="Enrolment & deadline reminders" checked={notifyDeadlines} onChange={setNotifyDeadlines} />
              <Switch label="Prerequisite / exclusion breaks" checked={notifyPrereq} onChange={setNotifyPrereq} />
              <Switch label="Seat-opened alerts" checked={notifySeats} onChange={setNotifySeats} />
            </div>
          </Card>
        )}
      </div>

      <Dialog open={shareOpen} title="Share your plan" onClose={() => setShareOpen(false)}>
        <ShareLinkDialog
          url={shareUrl ?? ""}
          onGenerate={openShare}
          onRevoke={() => {
            setShareUrl(null);
            setToast("Share link revoked.");
          }}
        />
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
