import * as React from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { AuthCard, Button, Callout, Input, PasswordField, StrengthMeter } from "@/ds";
import { authApi } from "@/api";

/**
 * Password reset (design/screens/01-auth-and-onboarding.md "recovery").
 * Three modes, one route:
 *
 * - `/reset`             — request a reset link by email (always "sent" — the
 *                          backend never reveals whether an account exists),
 *                          with a switch to the recovery-code path.
 * - `/reset` (code mode) — email + recovery code + new password; preserves
 *                          encrypted data via the recovery-wrapped key.
 * - `/reset?token=...`   — redeem an emailed link: choose a new password.
 *                          The response's `dataPreserved` says whether the
 *                          encrypted academic data survived (it does when the
 *                          account has a passkey — ADR-0006); the warning is
 *                          shown up front for the common (no-passkey) case.
 */

export default function ResetPassword() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";

  const [mode, setMode] = React.useState<"email" | "code">("email");
  const [email, setEmail] = React.useState("");
  const [code, setCode] = React.useState("");
  const [newPassword, setNewPassword] = React.useState("");
  const [confirm, setConfirm] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [requested, setRequested] = React.useState(false);

  function validNewPassword(): boolean {
    if (newPassword.length < 10) {
      setError("Choose a password of at least 10 characters.");
      return false;
    }
    if (confirm !== newPassword) {
      setError("Passwords don't match.");
      return false;
    }
    return true;
  }

  async function submitRequest(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    if (!/^\S+@\S+\.\S+$/.test(email)) {
      setError("Enter a valid email address.");
      return;
    }
    setError(null);
    setBusy(true);
    try {
      await authApi.requestPasswordResetEmail(email);
      setRequested(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't request a reset. Try again.");
    } finally {
      setBusy(false);
    }
  }

  async function submitCode(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    if (!/^\S+@\S+\.\S+$/.test(email)) {
      setError("Enter a valid email address.");
      return;
    }
    if (!code.trim()) {
      setError("Enter your recovery code.");
      return;
    }
    if (!validNewPassword()) return;
    setError(null);
    setBusy(true);
    try {
      await authApi.resetPasswordWithRecoveryCode(email, code, newPassword);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reset failed. Check your code and try again.");
    } finally {
      setBusy(false);
    }
  }

  async function submitToken(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    if (!validNewPassword()) return;
    setError(null);
    setBusy(true);
    try {
      const { dataPreserved } = await authApi.confirmPasswordReset(token, newPassword);
      navigate("/dashboard", {
        replace: true,
        state: dataPreserved ? undefined : { resetLostData: true },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "This reset link didn't work — request a new one.");
    } finally {
      setBusy(false);
    }
  }

  const footer = (
    <>
      Remembered it after all?{" "}
      <Link to="/signin" style={{ color: "var(--accent)", fontWeight: 600 }}>
        Sign in
      </Link>
    </>
  );

  if (token) {
    return (
      <AuthCard title="Choose a new password" footer={footer}>
        <form onSubmit={submitToken} style={{ display: "flex", flexDirection: "column", gap: 16 }} noValidate>
          {error && <Callout tone="danger">{error}</Callout>}
          <Callout tone="warning" title="About your encrypted data">
            If this account has a passkey, your encrypted transcript and plan data carries over.
            Otherwise it can't be unlocked without your old password or a recovery code and will be
            cleared.
          </Callout>
          <PasswordField
            label="New password"
            value={newPassword}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewPassword(e.target.value)}
            showStrength
          />
          <StrengthMeter password={newPassword} />
          <PasswordField
            label="Confirm new password"
            value={confirm}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setConfirm(e.target.value)}
          />
          <Button type="submit" variant="primary" fullWidth loading={busy}>
            Reset password
          </Button>
        </form>
      </AuthCard>
    );
  }

  if (mode === "code") {
    return (
      <AuthCard title="Reset with a recovery code" footer={footer}>
        <form onSubmit={submitCode} style={{ display: "flex", flexDirection: "column", gap: 16 }} noValidate>
          {error && <Callout tone="danger">{error}</Callout>}
          <Callout tone="info">
            Your recovery code unlocks your encrypted data, so nothing is lost.
          </Callout>
          <Input
            label="Email"
            type="email"
            icon="mail"
            value={email}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmail(e.target.value)}
            disabled={busy}
          />
          <Input
            label="Recovery code"
            placeholder="XXXX-XXXX-XXXX-XXXX"
            value={code}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCode(e.target.value)}
            disabled={busy}
          />
          <PasswordField
            label="New password"
            value={newPassword}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewPassword(e.target.value)}
            showStrength
          />
          <PasswordField
            label="Confirm new password"
            value={confirm}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setConfirm(e.target.value)}
          />
          <Button type="submit" variant="primary" fullWidth loading={busy}>
            Reset password
          </Button>
          <Button type="button" variant="link" size="sm" onClick={() => setMode("email")}>
            Email me a reset link instead
          </Button>
        </form>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Reset your password" footer={footer}>
      {requested ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Callout tone="info" title="Check your email">
            If <strong>{email}</strong> has an account, a reset link is on its way. It works for 1
            hour — check spam if it doesn't arrive.
          </Callout>
          <Button variant="secondary" fullWidth onClick={() => setRequested(false)}>
            Send another link
          </Button>
        </div>
      ) : (
        <form onSubmit={submitRequest} style={{ display: "flex", flexDirection: "column", gap: 16 }} noValidate>
          {error && <Callout tone="danger">{error}</Callout>}
          <Input
            label="Email"
            type="email"
            icon="mail"
            placeholder="you@mail.utoronto.ca"
            value={email}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmail(e.target.value)}
            disabled={busy}
          />
          <Button type="submit" variant="primary" fullWidth loading={busy}>
            Email me a reset link
          </Button>
          <Button type="button" variant="link" size="sm" onClick={() => setMode("code")}>
            I have a recovery code
          </Button>
        </form>
      )}
    </AuthCard>
  );
}
