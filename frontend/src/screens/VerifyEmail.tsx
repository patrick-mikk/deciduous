import * as React from "react";
import { Link, useSearchParams } from "react-router-dom";

import { AuthCard, Button, Callout, Spinner } from "@/ds";
import { authApi } from "@/api";

/**
 * Email-verification landing page — the `/verify?token=...` link from the
 * signup/resend email lands here. Redeems the token once on mount and shows
 * the outcome. Verifying doesn't sign anyone in (the link may be opened on a
 * different device), so the CTA is "continue" for a live session and
 * "sign in" otherwise.
 */

export default function VerifyEmail() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";

  const [state, setState] = React.useState<"working" | "done" | "failed">(token ? "working" : "failed");
  const [email, setEmail] = React.useState("");

  React.useEffect(() => {
    if (!token) return;
    let cancelled = false;
    authApi
      .verifyEmail(token)
      .then((verified) => {
        if (cancelled) return;
        setEmail(verified);
        setState("done");
      })
      .catch(() => !cancelled && setState("failed"));
    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <AuthCard
      title="Email verification"
      footer={
        <Link to="/signin" style={{ color: "var(--accent)", fontWeight: 600 }}>
          Go to sign in
        </Link>
      }
    >
      {state === "working" && (
        <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 0" }}>
          <Spinner />
          <span style={{ color: "var(--text-secondary)" }}>Verifying your email…</span>
        </div>
      )}
      {state === "done" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Callout tone="success" title="You're verified">
            {email ? <><strong>{email}</strong> is confirmed.</> : "Your email is confirmed."}
          </Callout>
          <Button variant="primary" fullWidth onClick={() => (window.location.href = "/dashboard")}>
            Continue to your planner
          </Button>
        </div>
      )}
      {state === "failed" && (
        <Callout tone="danger" title="This link didn't work">
          It may have expired (links last 3 days) or already been used. Sign in and use
          &ldquo;Resend verification email&rdquo; in Settings → Profile to get a fresh one.
        </Callout>
      )}
    </AuthCard>
  );
}
