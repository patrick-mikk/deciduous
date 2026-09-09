import * as React from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";

import { AuthCard, Input, PasswordField, Button, Divider, Callout, Checkbox } from "@/ds";
import { authApi, isMockApi } from "@/api";

/**
 * Sign in (design/screens/01-auth-and-onboarding.md, flow F2).
 *
 * Talks to the backend through `src/api/auth.ts` (`authApi`) — password
 * sign-in with a "remember me for 30 days" option, plus passkey (WebAuthn)
 * sign-in when the browser supports it. In mock/offline mode `authApi`
 * simulates the round trips so the flow stays fully exercisable.
 */

const RATE_LIMIT_ATTEMPTS = 3;

export default function SignIn() {
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? "/dashboard";

  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [remember, setRemember] = React.useState(true);
  const [fieldErrors, setFieldErrors] = React.useState<{ email?: string; password?: string }>({});
  const [formError, setFormError] = React.useState<string | null>(null);
  const [attempts, setAttempts] = React.useState(0);
  const [loading, setLoading] = React.useState(false);
  const [passkeyLoading, setPasskeyLoading] = React.useState(false);

  const rateLimited = attempts >= RATE_LIMIT_ATTEMPTS;
  const passkeysAvailable = authApi.passkeysSupported();

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
      await authApi.signIn(email, password, remember);
      navigate(from, { replace: true });
    } catch (err) {
      setAttempts((n) => n + 1);
      setFormError(err instanceof Error ? err.message : "Sign in failed. Try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handlePasskeySignIn() {
    if (passkeyLoading || loading) return;
    setFormError(null);
    setPasskeyLoading(true);
    try {
      await authApi.signInWithPasskey(remember);
      navigate(from, { replace: true });
    } catch (err) {
      // A user dismissing the browser's passkey sheet surfaces as an
      // AbortError/NotAllowedError — that's a cancel, not a failure worth a
      // red callout.
      const name = (err as { name?: string } | null)?.name;
      if (name !== "NotAllowedError" && name !== "AbortError") {
        setFormError(err instanceof Error ? err.message : "Passkey sign-in failed.");
      }
    } finally {
      setPasskeyLoading(false);
    }
  }

  return (
    <AuthCard
      title="Sign in to your planner"
      subtitle={isMockApi ? "Demo mode: any email + password signs you in." : undefined}
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
              onClick={() => navigate("/reset")}
            >
              Forgot password?
            </Button>
          </div>
        </div>

        <Checkbox
          label="Keep me signed in for 30 days"
          checked={remember}
          onChange={(v: boolean) => setRemember(v)}
          disabled={loading || rateLimited}
        />

        <Button type="submit" variant="primary" fullWidth loading={loading} disabled={rateLimited}>
          Sign in
        </Button>

        <Divider label="or" />

        {passkeysAvailable && (
          <Button
            type="button"
            variant="secondary"
            fullWidth
            icon="key"
            loading={passkeyLoading}
            onClick={handlePasskeySignIn}
          >
            Sign in with a passkey
          </Button>
        )}

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
