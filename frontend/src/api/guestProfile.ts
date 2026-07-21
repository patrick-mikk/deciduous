import type { Program, SessionCode } from "./types";

/**
 * Onboarding no longer requires an account (see Onboarding.tsx) — the
 * programs and term a guest picks during the tutorial are stored here so
 * "saving is optional" is real, not just a UI claim. Same versioned-key +
 * try/catch + shape-guard idiom as `Plan.tsx`'s `PLAN_STORAGE_KEY` and
 * `ThemeProvider`'s `STORAGE_KEY` — centralized here (rather than kept
 * private to one screen, as those are) because both Onboarding.tsx (writes)
 * and SignUp.tsx (reads, to sync into a new account) need it.
 */

const STORAGE_KEY = "deciduous:guest-profile:v1";

export interface GuestProfile {
  programs: Program[];
  /** The session (term) the student *started* at UofT — see Onboarding.tsx's term step. */
  startSession: SessionCode | null;
  /**
   * @deprecated Pre-startSession profiles stored the student's *current* term
   * here instead. No longer written by `saveGuestProfile`, but the field (and
   * `loadGuestProfile`'s fallback below) stay so an already-saved v1 profile
   * keeps loading instead of crashing.
   */
  session?: SessionCode | null;
}

export function loadGuestProfile(): GuestProfile | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || !Array.isArray(parsed.programs)) return null;
    return {
      programs: parsed.programs,
      // Older saved profiles have `session` but no `startSession` yet — fall
      // back to it rather than losing the student's choice on next load.
      startSession: parsed.startSession ?? parsed.session ?? null,
      session: parsed.session ?? null,
    };
  } catch {
    return null;
  }
}

export function saveGuestProfile(profile: GuestProfile): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(profile));
  } catch {
    // Best-effort only — storage may be unavailable (private browsing, quota).
  }
}

export function clearGuestProfile(): void {
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // ignore
  }
}
