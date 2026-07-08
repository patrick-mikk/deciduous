import * as React from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";

import { AuthCard, Input, PasswordField, Button, Divider, Callout } from "@/ds";
import { ensureCsrfToken, isMockApi } from "@/api";

/**
 * Sign in (design/screens/01-auth-and-onboarding.md, flow F2).
 *
 * There's no `/api/auth/*` surface on the shared `ApiClient` yet (design/06
 * lists it, but `src/api/client.ts` — owned by a different agent — doesn't
 * implement it). This screen therefore talks to `${VITE_API_BASE}/auth/signin`
 * directly when a backend is configured, and otherwise falls back to a local
 * simulation (same "offline-renders" contract `mockClient` gives every other
 * screen) so the flow is fully exercisable without a backend.
 */

const API_BASE = import.meta.env.VITE_API_BASE as string | undefined;
const RATE_LIMIT_ATTEMPTS = 3;

async function signIn(email: string, password: string): Promise<void> {
  if (API_BASE) {
    const res = await fetch(`${API_BASE}/auth/signin`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": await ensureCsrfToken() },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error((body && body.message) || "Incorrect email or password.");
    }
    return;
  }
  // Offline / no backend configured yet: simulate the round trip so loading
  // and success states are still exercisable (mirrors src/api/mock.ts's delay()).
  await new Promise((resolve) => setTimeout(resolve, 400));
  if (!email.trim() || !password) {
    throw new Error("Incorrect email or password.");
  }
}

export default function SignIn() {
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? "/dashboard";

  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [fieldErrors, setFieldErrors] = React.useState<{ email?: string; password?: string }>({});
  const [formError, setFormError] = React.useState<string | null>(null);
  const [attempts, setAttempts] = React.useState(0);
  const [loading, setLoading] = React.useState(false);
  const [showRecoveryNote, setShowRecoveryNote] = React.useState(false);

  const rateLimited = attempts >= RATE_LIMIT_ATTEMPTS;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (rateLimited || loading) return;

    const nextErrors: { email?: string; password?: string } = {};
    if (!email.trim()) nextErrors.email = "Enter your email.";
    if (!password) nextErrors.password = "Enter your password.";
    setFieldErrors(nextErrors);
    setFormError(null);
    if (Object.keys(nextErrors).length > 0) return;

    setLoading(true);
    try {
      await signIn(email, password);
      navigate(from, { replace: true });
    } catch (err) {
      setAttempts((n) => n + 1);
      setFormError(err instanceof Error ? err.message : "Sign in failed. Try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthCard
      title="Sign in to your planner"
      subtitle={isMockApi ? "Demo mode — any email + password signs you in." : undefined}
      footer={
        <>
          New here?{" "}
          <Link to="/signup" style={{ color: "var(--accent)", fontWeight: 600 }}>
            Create an account
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }} noValidate>
        {rateLimited && (
          <Callout tone="danger" title="Too many attempts">
            Sign-in is temporarily locked after {RATE_LIMIT_ATTEMPTS} failed tries. Wait a moment and try
            again, or reset your password.
          </Callout>
        )}
        {!rateLimited && formError && (
          <Callout tone="danger" title="Couldn't sign you in">
            {formError}
          </Callout>
        )}

        <Input
          label="Email"
          type="email"
          icon="mail"
          placeholder="you@mail.utoronto.ca"
          value={email}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmail(e.target.value)}
          error={fieldErrors.email}
          disabled={loading || rateLimited}
        />

        <div>
          <PasswordField
            label="Password"
            value={password}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPassword(e.target.value)}
            error={fieldErrors.password}
          />
          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 6 }}>
            <Button
              type="button"
              variant="link"
              size="sm"
              onClick={() => setShowRecoveryNote((v) => !v)}
            >
              Forgot password?
            </Button>
          </div>
          {showRecoveryNote && (
            <Callout tone="warning" title="You'll need your recovery code">
              Resetting your password re-wraps your encrypted academic data — have the recovery code
              from Settings ready before you start. Password reset isn't wired up in this preview yet.
            </Callout>
          )}
        </div>

        <Button type="submit" variant="primary" fullWidth loading={loading} disabled={rateLimited}>
          Sign in
        </Button>

        <Divider label="or" />

        <Button
          type="button"
          variant="secondary"
          fullWidth
          onClick={() => navigate("/signup")}
        >
          Create an account
        </Button>
      </form>
    </AuthCard>
  );
}
