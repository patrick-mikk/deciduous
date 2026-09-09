import * as React from "react";
import { useNavigate } from "react-router-dom";

import { Button, Callout } from "@/ds";

/**
 * The one "you're browsing as a guest" nudge, shared by every screen whose
 * save/add/share action can only ever 401 for a signed-out visitor.
 *
 * This is NOT a new mechanism — it is the nudge Onboarding.tsx already
 * renders for its `importStatus === "auth-error"` branch (an info-tone
 * `Callout` titled "Create an account to …", body explaining the guest state,
 * and a single primary "Create account" action), factored out so the other
 * ~8 screens that need it can't each drift into their own wording, tone, or
 * (as the Programs "Add" bug showed) into showing nothing at all.
 *
 * Why info tone and not danger: accounts are optional by design in this app
 * (there are no route guards — see frontend/src/App.tsx, and Onboarding.tsx's
 * "saving is optional" flow). A guest hitting a save action has not hit an
 * error; they've hit the edge of what works without an account. Red banners
 * and raw `API error 401: {...}` strings both misreport that.
 *
 * Pair with `isAuthError(err)` from `@/api` — that predicate decides when to
 * render this instead of the screen's normal danger Callout.
 *
 * Onboarding.tsx deliberately keeps its own inline copy: its "Create account"
 * must first flush in-progress selections to the guest profile
 * (`handleCreateAccount` -> `persistGuestProfile`) before navigating, which is
 * specific to that wizard and not something the other screens have.
 */
export function GuestCallout({
  title = "Create an account to save this",
  children,
  actionLabel = "Create account",
}: {
  /** Screen-specific headline, e.g. "Create an account to add programs". */
  title?: string;
  /** One sentence saying what a guest can still do and what needs an account. */
  children?: React.ReactNode;
  actionLabel?: string;
}) {
  const navigate = useNavigate();
  return (
    <Callout
      tone="info"
      title={title}
      action={
        <Button size="sm" variant="primary" onClick={() => navigate("/signup")}>
          {actionLabel}
        </Button>
      }
    >
      {children ?? (
        <>
          You're browsing as a guest, so there's nowhere to save this yet. Create a free account (or sign in) to keep
          it.
        </>
      )}
    </Callout>
  );
}

export default GuestCallout;
