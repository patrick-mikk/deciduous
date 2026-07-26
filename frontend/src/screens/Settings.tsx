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
import { api, authApi } from "@/api";
import type { ActiveSession, Passkey, Profile, SessionCode } from "@/api";
import { useTheme } from "@/theme/ThemeProvider";

/**
 * Settings (design/screens/05-transcript-settings-share.md "Settings"),
 * tabbed: Profile / Security / Data / Appearance / Notifications.
 *
 * Profile, Security (password change, recovery code, passkeys, active
 * sessions), and account deletion are wired to the real backend through
 * `src/api/auth.ts` (`authApi`) — in mock mode (`VITE_API_BASE=mock`) that
 * module simulates every round trip, so the screen still works offline.
 * Appearance and Notifications persist to localStorage (client-side
 * preferences by design).
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

function formatWhen(iso: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

/** "Chrome on Windows"-style summary from a raw User-Agent string. */
function describeUserAgent(ua: string): string {
  if (!ua) return "Unknown device";
  const browser = /Edg\//.test(ua)
    ? "Edge"
    : /OPR\//.test(ua)
      ? "Opera"
      : /Firefox\//.test(ua)
        ? "Firefox"
        : /Chrome\//.test(ua)
          ? "Chrome"
          : /Safari\//.test(ua)
            ? "Safari"
            : "Browser";
  const os = /Windows/.test(ua)
    ? "Windows"
    : /Mac OS X|Macintosh/.test(ua)
      ? "macOS"
      : /iPhone|iPad/.test(ua)
        ? "iOS"
        : /Android/.test(ua)
          ? "Android"
          : /Linux/.test(ua)
            ? "Linux"
            : "";
  return os ? `${browser} on ${os}` : browser;
}

const cardTitleStyle: React.CSSProperties = {
  fontSize: "var(--text-h3)",
  fontWeight: "var(--weight-bold)" as React.CSSProperties["fontWeight"],
  color: "var(--text)",
  marginBottom: 12,
};

export default function Settings() {
  const navigate = useNavigate();
  const { theme, isExplicit, setTheme, followSystem } = useTheme();

  const [tab, setTab] = React.useState<TabKey>("profile");
  const [toast, setToast] = React.useState<string | null>(null);

  // ---- Profile -------------------------------------------------------------
  const [profile, setProfile] = React.useState<Profile | null>(null);
  const [profileError, setProfileError] = React.useState<string | null>(null);
  const [profileSaving, setProfileSaving] = React.useState(false);
  const [sessions, setSessions] = React.useState<SessionCode[] | null>(null);
  const [signingOut, setSigningOut] = React.useState(false);
  const [verifyBusy, setVerifyBusy] = React.useState(false);

  // ---- Security ------------------------------------------------------------
  const [currentPassword, setCurrentPassword] = React.useState("");
  const [newPassword, setNewPassword] = React.useState("");
  const [passwordBusy, setPasswordBusy] = React.useState(false);
  const [passwordError, setPasswordError] = React.useState<string | null>(null);

  const [recoveryCode, setRecoveryCode] = React.useState<string | null>(null);
  const [recoveryBusy, setRecoveryBusy] = React.useState(false);

  const [passkeys, setPasskeys] = React.useState<Passkey[] | null>(null);
  const [passkeyLabel, setPasskeyLabel] = React.useState("");
  const [passkeyBusy, setPasskeyBusy] = React.useState(false);
  const [passkeyError, setPasskeyError] = React.useState<string | null>(null);

  const [activeSessions, setActiveSessions] = React.useState<ActiveSession[] | null>(null);
  const [sessionsBusy, setSessionsBusy] = React.useState(false);

  // ---- Data ----------------------------------------------------------------
  const [shareOpen, setShareOpen] = React.useState(false);
  const [shareUrl, setShareUrl] = React.useState<string | null>(null);
  const [deleteOpen, setDeleteOpen] = React.useState(false);
  const [deletePassword, setDeletePassword] = React.useState("");
  const [deleteBusy, setDeleteBusy] = React.useState(false);
  const [deleteError, setDeleteError] = React.useState<string | null>(null);

  // ---- Appearance / notifications (localStorage by design) -----------------
  const [density, setDensity] = useLocalStorage<"comfortable" | "compact">("deciduous:density", "comfortable");
  const [leafMotion, setLeafMotion] = useLocalStorage<boolean>("deciduous:leaf-motion", true);
  const [notifyDeadlines, setNotifyDeadlines] = useLocalStorage<boolean>("deciduous:notify-deadlines", true);
  const [notifyPrereq, setNotifyPrereq] = useLocalStorage<boolean>("deciduous:notify-prereq", true);
  const [notifySeats, setNotifySeats] = useLocalStorage<boolean>("deciduous:notify-seats", false);

  React.useEffect(() => {
    let cancelled = false;
    authApi
      .getProfile()
      .then((p) => !cancelled && setProfile(p))
      .catch((e: unknown) => !cancelled && setProfileError(e instanceof Error ? e.message : "Failed to load profile."));
    api
      .getSessions()
      .then((s) => !cancelled && setSessions(s))
      .catch(() => !cancelled && setSessions([]));
    return () => {
      cancelled = true;
    };
  }, []);

  const refreshSecurity = React.useCallback(() => {
    authApi.listPasskeys().then(setPasskeys).catch(() => setPasskeys([]));
    authApi.listSessions().then(setActiveSessions).catch(() => setActiveSessions([]));
  }, []);

  React.useEffect(() => {
    if (tab === "security" && (passkeys === null || activeSessions === null)) refreshSecurity();
  }, [tab, passkeys, activeSessions, refreshSecurity]);

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
    if (!shareUrl) {
      api
        .createShareLink()
        .then((r) => setShareUrl(r.url))
        .catch(() => setToast("Couldn't generate a share link."));
    }
  }

  async function saveProfile() {
    if (!profile || profileSaving) return;
    setProfileSaving(true);
    setProfileError(null);
    try {
      const saved = await authApi.updateProfile({
        displayName: profile.displayName,
        currentSession: profile.currentSession,
        expectedGrad: profile.expectedGrad,
      });
      setProfile(saved);
      setToast("Profile updated.");
    } catch (e) {
      setProfileError(e instanceof Error ? e.message : "Couldn't save your profile.");
    } finally {
      setProfileSaving(false);
    }
  }

  async function resendVerification() {
    if (verifyBusy) return;
    setVerifyBusy(true);
    try {
      const { alreadyVerified } = await authApi.resendVerificationEmail();
      if (alreadyVerified) {
        setProfile((p) => (p ? { ...p, verified: true } : p));
        setToast("You're already verified.");
      } else {
        setToast("Verification email sent — check your inbox.");
      }
    } catch (e) {
      setToast(e instanceof Error ? e.message : "Couldn't send the verification email.");
    } finally {
      setVerifyBusy(false);
    }
  }

  async function handleSignOut() {
    if (signingOut) return;
    setSigningOut(true);
    try {
      await authApi.signOut();
      navigate("/signin", { replace: true });
    } catch {
      setSigningOut(false);
      setToast("Couldn't sign out. Try again.");
    }
  }

  async function submitPasswordChange() {
    if (passwordBusy || !currentPassword || !newPassword) return;
    setPasswordBusy(true);
    setPasswordError(null);
    try {
      await authApi.changePassword(currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setToast("Password updated. Other devices were signed out.");
    } catch (e) {
      setPasswordError(e instanceof Error ? e.message : "Couldn't update your password.");
    } finally {
      setPasswordBusy(false);
    }
  }

  async function generateRecovery() {
    if (recoveryBusy) return;
    setRecoveryBusy(true);
    try {
      setRecoveryCode(await authApi.generateRecoveryCode());
      setToast("Recovery code generated. Save it now — it won't be shown again.");
    } catch (e) {
      setToast(e instanceof Error ? e.message : "Couldn't generate a recovery code.");
    } finally {
      setRecoveryBusy(false);
    }
  }

  async function addPasskey() {
    if (passkeyBusy) return;
    setPasskeyBusy(true);
    setPasskeyError(null);
    try {
      await authApi.registerPasskey(passkeyLabel.trim() || "Passkey");
      setPasskeyLabel("");
      setToast("Passkey added.");
      refreshSecurity();
    } catch (e) {
      const name = (e as { name?: string } | null)?.name;
      if (name !== "NotAllowedError" && name !== "AbortError") {
        setPasskeyError(e instanceof Error ? e.message : "Couldn't add a passkey.");
      }
    } finally {
      setPasskeyBusy(false);
    }
  }

  async function removePasskey(id: number) {
    try {
      await authApi.deletePasskey(id);
      setToast("Passkey removed.");
      refreshSecurity();
    } catch (e) {
      setToast(e instanceof Error ? e.message : "Couldn't remove that passkey.");
    }
  }

  async function revokeSession(id: string, isCurrent: boolean) {
    try {
      await authApi.revokeSession(id);
      if (isCurrent) {
        navigate("/signin", { replace: true });
        return;
      }
      setToast("Session revoked.");
      refreshSecurity();
    } catch (e) {
      setToast(e instanceof Error ? e.message : "Couldn't revoke that session.");
    }
  }

  async function revokeOthers() {
    if (sessionsBusy) return;
    setSessionsBusy(true);
    try {
      await authApi.revokeOtherSessions();
      setToast("Signed out everywhere else.");
      refreshSecurity();
    } catch (e) {
      setToast(e instanceof Error ? e.message : "Couldn't revoke other sessions.");
    } finally {
      setSessionsBusy(false);
    }
  }

  async function confirmDeleteAccount() {
    if (deleteBusy || !deletePassword) return;
    setDeleteBusy(true);
    setDeleteError(null);
    try {
      await authApi.deleteAccount(deletePassword);
      navigate("/", { replace: true });
    } catch (e) {
      setDeleteError(e instanceof Error ? e.message : "Couldn't delete your account.");
      setDeleteBusy(false);
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
            {profileError && (
              <div style={{ marginBottom: 12 }}>
                <Callout tone="danger">{profileError}</Callout>
              </div>
            )}
            {profile == null ? (
              <Skeleton height={220} />
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 14, maxWidth: 420 }}>
                <Input label="Email" type="email" value={profile.email} disabled hint="Your sign-in email can't be changed here." />
                {profile.verified ? (
                  <Callout tone="success">Email verified.</Callout>
                ) : (
                  <Callout
                    tone="warning"
                    title="Email not verified"
                    action={
                      <Button variant="secondary" size="sm" loading={verifyBusy} onClick={resendVerification}>
                        Resend email
                      </Button>
                    }
                  >
                    Check your inbox for the verification link, or resend it.
                  </Callout>
                )}
                <Input
                  label="Name"
                  value={profile.displayName}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    setProfile({ ...profile, displayName: e.target.value })
                  }
                />
                {sessions == null ? (
                  <Skeleton height={62} />
                ) : (
                  <Select
                    label="Current session"
                    value={profile.currentSession}
                    onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
                      setProfile({ ...profile, currentSession: e.target.value })
                    }
                    options={[
                      { label: "Not set", value: "" },
                      ...sessions
                        .filter((s) => s === profile.currentSession || true)
                        .map((s) => ({ label: s, value: s })),
                    ]}
                  />
                )}
                <Input
                  label="Expected graduation"
                  type="month"
                  value={profile.expectedGrad}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    setProfile({ ...profile, expectedGrad: e.target.value })
                  }
                />
                <div style={{ display: "flex", gap: 10 }}>
                  <Button onClick={saveProfile} loading={profileSaving}>
                    Save profile
                  </Button>
                  <Button variant="secondary" icon="log-out" onClick={handleSignOut} loading={signingOut}>
                    Sign out
                  </Button>
                </div>
              </div>
            )}
          </Card>
        )}

        {tab === "security" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <Card>
              <div style={cardTitleStyle}>Change password</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 12, maxWidth: 360 }}>
                {passwordError && <Callout tone="danger">{passwordError}</Callout>}
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
                  Your encrypted academic data is re-locked under the new password automatically — nothing
                  is lost. Every other signed-in device is signed out.
                </Callout>
                <div>
                  <Button disabled={!currentPassword || !newPassword} loading={passwordBusy} onClick={submitPasswordChange}>
                    Update password
                  </Button>
                </div>
              </div>
            </Card>

            {recoveryCode ? (
              <div>
                <RecoveryCodeCard
                  code={recoveryCode}
                  onCopy={() => setToast("Recovery code copied.")}
                  onRegenerate={generateRecovery}
                />
                <div style={{ marginTop: 8 }}>
                  <Callout tone="warning" title="Save this code now">
                    This is the only time it's shown — only a hash is stored. With it, a forgotten
                    password can be reset without losing your encrypted data.
                  </Callout>
                </div>
              </div>
            ) : (
              <Card>
                <div style={cardTitleStyle}>Recovery code</div>
                <p style={{ margin: "0 0 12px", fontSize: "var(--text-body-sm)", color: "var(--text-secondary)" }}>
                  A recovery code lets you reset a forgotten password without losing access to your
                  encrypted transcript and plan data. Generate one and keep it somewhere safe — it's
                  shown only once.
                </p>
                <Button variant="secondary" icon="key-round" loading={recoveryBusy} onClick={generateRecovery}>
                  Generate recovery code
                </Button>
              </Card>
            )}

            <Card>
              <div style={cardTitleStyle}>Passkeys</div>
              {!authApi.passkeysSupported() ? (
                <Callout tone="info">This browser doesn't support passkeys.</Callout>
              ) : (
                <>
                  <p style={{ margin: "0 0 12px", fontSize: "var(--text-body-sm)", color: "var(--text-secondary)" }}>
                    Sign in with Face ID, Touch ID, Windows Hello, or a security key — no password
                    needed.
                  </p>
                  {passkeyError && (
                    <div style={{ marginBottom: 10 }}>
                      <Callout tone="danger">{passkeyError}</Callout>
                    </div>
                  )}
                  {passkeys == null ? (
                    <Skeleton height={40} />
                  ) : (
                    passkeys.map((p) => (
                      <div
                        key={p.id}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          padding: "8px 0",
                          borderBottom: "1px solid var(--border)",
                        }}
                      >
                        <div>
                          <div style={{ fontSize: "var(--text-body)", color: "var(--text)" }}>{p.label}</div>
                          <div style={{ fontSize: "var(--text-body-sm)", color: "var(--text-tertiary)" }}>
                            Added {formatWhen(p.createdAt)}
                            {p.lastUsedAt ? ` · last used ${formatWhen(p.lastUsedAt)}` : ""}
                          </div>
                        </div>
                        <Button variant="secondary" size="sm" onClick={() => removePasskey(p.id)}>
                          Remove
                        </Button>
                      </div>
                    ))
                  )}
                  <div style={{ display: "flex", gap: 10, alignItems: "flex-end", marginTop: 12, maxWidth: 420 }}>
                    <div style={{ flex: 1 }}>
                      <Input
                        label="Name this device"
                        placeholder="e.g. MacBook Touch ID"
                        value={passkeyLabel}
                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPasskeyLabel(e.target.value)}
                      />
                    </div>
                    <Button icon="key" loading={passkeyBusy} onClick={addPasskey}>
                      Add passkey
                    </Button>
                  </div>
                </>
              )}
            </Card>

            <Card>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
                <div style={{ ...cardTitleStyle, marginBottom: 0 }}>Active sessions</div>
                <Button variant="secondary" size="sm" loading={sessionsBusy} onClick={revokeOthers}>
                  Sign out other devices
                </Button>
              </div>
              {activeSessions == null ? (
                <Skeleton height={60} />
              ) : activeSessions.length === 0 ? (
                <Callout tone="info">No active sessions found.</Callout>
              ) : (
                activeSessions.map((s) => (
                  <div
                    key={s.id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "10px 0",
                      borderBottom: "1px solid var(--border)",
                    }}
                  >
                    <div>
                      <div style={{ fontSize: "var(--text-body)", color: "var(--text)" }}>
                        {describeUserAgent(s.userAgent)}
                        {s.current ? " — this device" : ""}
                      </div>
                      <div style={{ fontSize: "var(--text-body-sm)", color: "var(--text-tertiary)" }}>
                        Signed in {formatWhen(s.createdAt)} · expires {formatWhen(s.expiresAt)}
                        {s.ipAddress ? ` · ${s.ipAddress}` : ""}
                      </div>
                    </div>
                    <Button variant="secondary" size="sm" onClick={() => revokeSession(s.id, s.current)}>
                      {s.current ? "Sign out" : "Revoke"}
                    </Button>
                  </div>
                ))
              )}
            </Card>
          </div>
        )}

        {tab === "data" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <Card>
              <div style={cardTitleStyle}>Import & export</div>
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
              description="Deletes your account and every transcript entry, plan, and share link under it. This cannot be undone."
              onDelete={() => {
                setDeleteError(null);
                setDeletePassword("");
                setDeleteOpen(true);
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

      <Dialog open={deleteOpen} title="Confirm account deletion" onClose={() => !deleteBusy && setDeleteOpen(false)}>
        <div style={{ display: "flex", flexDirection: "column", gap: 12, minWidth: 320 }}>
          {deleteError && <Callout tone="danger">{deleteError}</Callout>}
          <Callout tone="danger" title="This is permanent">
            Your account and all encrypted academic data will be deleted immediately.
          </Callout>
          <PasswordField
            label="Enter your password to confirm"
            value={deletePassword}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setDeletePassword(e.target.value)}
          />
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Button variant="secondary" onClick={() => setDeleteOpen(false)} disabled={deleteBusy}>
              Cancel
            </Button>
            <Button variant="danger" loading={deleteBusy} disabled={!deletePassword} onClick={confirmDeleteAccount}>
              Delete my account
            </Button>
          </div>
        </div>
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
