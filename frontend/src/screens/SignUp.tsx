import * as React from "react";
import { useNavigate, Link } from "react-router-dom";

import { AuthCard, Input, PasswordField, Button, Checkbox, Callout } from "@/ds";
import { isMockApi } from "@/api";

/**
 * Sign up (design/screens/01-auth-and-onboarding.md, flow F1 step 1-2).
 *
 * Same "no auth endpoint on ApiClient yet" situation as SignIn.tsx: posts to
 * `${VITE_API_BASE}/auth/signup` when a backend is configured, otherwise
 * simulates the round trip so the flow renders and completes offline.
 * On success, lands on /onboarding (F1 step 4) — email verification (F1
 * step 3) isn't wired up in this preview.
 */

const API_BASE = import.meta.env.VITE_API_BASE as string | undefined;

function scorePassword(pw: string): number {
  let s = 0;
  if (pw.length >= 8) s++;
  if (pw.length >= 12) s++;
  if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) s++;
  if (/\d/.test(pw)) s++;
  if (/[^A-Za-z0-9]/.test(pw)) s++;
  return Math.min(4, s);
}

async function signUp(email: string, password: string): Promise<void> {
  if (API_BASE) {
    const res = await fetch(`${API_BASE}/auth/signup`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error((body && body.message) || "Couldn't create your account.");
    }
    return;
  }
  await new Promise((resolve) => setTimeout(resolve, 500));
}

export default function SignUp() {
  const navigate = useNavigate();

  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [confirm, setConfirm] = React.useState("");
  const [agreed, setAgreed] = React.useState(false);
  const [fieldErrors, setFieldErrors] = React.useState<{
    email?: string;
    password?: string;
    confirm?: string;
    agreed?: string;
  }>({});
  const [formError, setFormError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (loading) return;

    const nextErrors: typeof fieldErrors = {};
    if (!/^\S+@\S+\.\S+$/.test(email)) nextErrors.email = "Enter a valid email address.";
    if (scorePassword(password) < 2) nextErrors.password = "Choose a stronger password (8+ characters).";
    if (confirm !== password) nextErrors.confirm = "Passwords don't match.";
    if (!agreed) nextErrors.agreed = "You must agree to continue.";
    setFieldErrors(nextErrors);
    setFormError(null);
    if (Object.keys(nextErrors).length > 0) return;

    setLoading(true);
    try {
      await signUp(email, password);
      navigate("/onboarding", { replace: true });
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Couldn't create your account. Try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthCard
      title="Create your account"
      subtitle={isMockApi ? "Demo mode — no email is actually sent." : "Plan your degree, courses, and timetable."}
      footer={
        <>
          Already have an account?{" "}
          <Link to="/signin" style={{ color: "var(--accent)", fontWeight: 600 }}>
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }} noValidate>
        {formError && (
          <Callout tone="danger" title="Couldn't create your account">
            {formError}
          </Callout>
        )}

        <Callout tone="info" title="Your academic data is encrypted">
          Transcript and plan data are encrypted at rest and unlocked only with your password.
        </Callout>

        <Input
          label="Email"
          type="email"
          icon="mail"
          placeholder="you@mail.utoronto.ca"
          value={email}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmail(e.target.value)}
          error={fieldErrors.email}
          disabled={loading}
        />

        <PasswordField
          label="Password"
          value={password}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPassword(e.target.value)}
          error={fieldErrors.password}
          showStrength
          hint={!fieldErrors.password ? "At least 8 characters; mix letters, numbers, and symbols." : undefined}
        />

        <PasswordField
          label="Confirm password"
          value={confirm}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => setConfirm(e.target.value)}
          error={fieldErrors.confirm}
        />

        <div>
          <Checkbox
            label="I agree to the Terms of Service and Privacy Policy"
            checked={agreed}
            onChange={(v: boolean) => {
              setAgreed(v);
              if (v) setFieldErrors((prev) => ({ ...prev, agreed: undefined }));
            }}
            disabled={loading}
          />
          {fieldErrors.agreed && (
            <div style={{ fontSize: "var(--text-caption)", color: "var(--danger)", marginTop: 4 }}>
              {fieldErrors.agreed}
            </div>
          )}
        </div>

        <Button type="submit" variant="primary" fullWidth loading={loading}>
          Create account
        </Button>

        <p
          style={{
            margin: 0,
            fontSize: "var(--text-caption)",
            color: "var(--text-tertiary)",
            textAlign: "center",
          }}
        >
          Unofficial · not affiliated with the University of Toronto.
        </p>
      </form>
    </AuthCard>
  );
}
