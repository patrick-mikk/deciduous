/**
 * Auth + account API module — the typed surface for everything under
 * `/api/auth/*` and `/api/me/profile` (backend/api/auth.py, passkeys.py,
 * me.py). Kept separate from the `ApiClient` in `./client.ts` on purpose:
 * that interface is the data surface every screen shares (courses, plans,
 * transcript), while these calls are auth-lifecycle operations used only by
 * SignIn/SignUp/Settings/AppLayout. Same boundary contract though — raw
 * backend JSON is normalized HERE, never at a call site.
 *
 * Mock mode (`VITE_API_BASE=mock`): every function simulates its round trip
 * locally (small delay + optimistic result), mirroring how SignIn/SignUp
 * already behaved offline, so the whole Settings surface stays exercisable
 * with no backend.
 *
 * WebAuthn passkeys: `registerPasskey`/`signInWithPasskey` drive the browser
 * `navigator.credentials` API against the backend's challenge/verify pairs.
 * The base64url <-> ArrayBuffer plumbing lives here (no external dependency).
 */

import { API_BASE, ensureCsrfToken, isMockApi } from "./client";

export interface AuthUser {
  id: number;
  email: string;
}

export interface Profile {
  email: string;
  verified: boolean;
  displayName: string;
  currentSession: string;
  expectedGrad: string;
}

export interface ActiveSession {
  id: string;
  current: boolean;
  createdAt: string;
  expiresAt: string;
  userAgent: string;
  ipAddress: string;
}

export interface Passkey {
  id: number;
  label: string;
  createdAt: string;
  lastUsedAt: string | null;
}

function delay<T>(value: T, ms = 300): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

async function authFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const method = (init?.method ?? "GET").toUpperCase();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (method !== "GET") headers["X-CSRF-Token"] = await ensureCsrfToken();
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    ...init,
    headers: { ...headers, ...(init?.headers as Record<string, string> | undefined) },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const message =
      (body && typeof body === "object" && ((body as { error?: string }).error || (body as { message?: string }).message)) ||
      `Request failed (${res.status}).`;
    const err = new Error(message) as Error & { status?: number };
    err.status = res.status;
    throw err;
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Mock-mode state (module-local; resets on reload, which is fine for a demo).
// ---------------------------------------------------------------------------

const mockState = {
  user: { id: 1, email: "demo@mail.utoronto.ca" } as AuthUser,
  profile: {
    email: "demo@mail.utoronto.ca",
    verified: true,
    displayName: "Priya Sharma",
    currentSession: "",
    expectedGrad: "2027-06",
  } as Profile,
  passkeys: [] as Passkey[],
  nextPasskeyId: 1,
};

const MOCK_SESSIONS: ActiveSession[] = [
  {
    id: "mock-current",
    current: true,
    createdAt: new Date().toISOString(),
    expiresAt: new Date(Date.now() + 30 * 86400_000).toISOString(),
    userAgent: navigator.userAgent,
    ipAddress: "127.0.0.1",
  },
];

// ---------------------------------------------------------------- passwords
export async function signIn(email: string, password: string, rememberMe: boolean): Promise<AuthUser> {
  if (isMockApi || !API_BASE) {
    await delay(null, 400);
    if (!email.trim() || !password) throw new Error("Incorrect email or password.");
    return { ...mockState.user, email };
  }
  const res = await authFetch<{ user?: AuthUser }>("/auth/signin", {
    method: "POST",
    body: JSON.stringify({ email, password, rememberMe }),
  });
  if (!res.user) throw new Error("Sign in failed. Try again.");
  return res.user;
}

export async function signUp(email: string, password: string, rememberMe: boolean): Promise<AuthUser> {
  if (isMockApi || !API_BASE) {
    await delay(null, 500);
    return { ...mockState.user, email };
  }
  const res = await authFetch<{ user?: AuthUser }>("/auth/signup", {
    method: "POST",
    body: JSON.stringify({ email, password, rememberMe }),
  });
  if (!res.user) throw new Error("Couldn't create your account.");
  return res.user;
}

export async function signOut(): Promise<void> {
  if (isMockApi || !API_BASE) return delay(undefined, 200);
  await authFetch("/auth/signout", { method: "POST" });
}

/** The signed-in user, or `null` when the session is absent/expired. */
export async function getSessionUser(): Promise<AuthUser | null> {
  if (isMockApi || !API_BASE) return delay(mockState.user, 150);
  try {
    const res = await authFetch<{ user?: AuthUser }>("/auth/session");
    return res.user ?? null;
  } catch (e) {
    if ((e as { status?: number }).status === 401) return null;
    throw e;
  }
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  if (isMockApi || !API_BASE) return delay(undefined, 400);
  await authFetch("/auth/change-password", {
    method: "POST",
    body: JSON.stringify({ currentPassword, newPassword }),
  });
}

/** Returns the plaintext recovery code — shown to the user EXACTLY ONCE.
 * Requires the current password (re-auth before minting a recovery credential). */
export async function generateRecoveryCode(password: string): Promise<string> {
  if (isMockApi || !API_BASE) {
    const alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789";
    const group = () =>
      Array.from({ length: 4 }, () => alphabet[Math.floor(Math.random() * alphabet.length)]).join("");
    return delay([group(), group(), group(), group()].join("-"), 300);
  }
  const res = await authFetch<{ recoveryCode?: string }>("/auth/recovery-code", {
    method: "POST",
    body: JSON.stringify({ password }),
  });
  if (!res.recoveryCode) throw new Error("Couldn't generate a recovery code.");
  return res.recoveryCode;
}

export async function resetPasswordWithRecoveryCode(
  email: string,
  recoveryCode: string,
  newPassword: string,
): Promise<void> {
  if (isMockApi || !API_BASE) return delay(undefined, 400);
  await authFetch("/auth/reset", {
    method: "POST",
    body: JSON.stringify({ email, recoveryCode, newPassword }),
  });
}

/** "Email me a reset link" — always resolves (202) whether or not the email
 * has an account, by design (no account enumeration). */
export async function requestPasswordResetEmail(email: string): Promise<void> {
  if (isMockApi || !API_BASE) return delay(undefined, 400);
  await authFetch("/auth/reset", { method: "POST", body: JSON.stringify({ email }) });
}

/** Redeem an emailed reset link. `dataPreserved` tells whether the encrypted
 * academic data survived (true when the account had a passkey — ADR-0006). */
export async function confirmPasswordReset(
  token: string,
  newPassword: string,
): Promise<{ user: AuthUser; dataPreserved: boolean }> {
  if (isMockApi || !API_BASE) {
    await delay(null, 400);
    return { user: { ...mockState.user }, dataPreserved: true };
  }
  const res = await authFetch<{ user?: AuthUser; dataPreserved?: boolean }>("/auth/reset/confirm", {
    method: "POST",
    body: JSON.stringify({ token, newPassword }),
  });
  if (!res.user) throw new Error("Password reset failed.");
  return { user: res.user, dataPreserved: res.dataPreserved === true };
}

/** Redeem an emailed verification link; resolves to the verified address. */
export async function verifyEmail(token: string): Promise<string> {
  if (isMockApi || !API_BASE) return delay(mockState.profile.email, 300);
  const res = await authFetch<{ email?: string }>("/auth/verify", {
    method: "POST",
    body: JSON.stringify({ token }),
  });
  return typeof res.email === "string" ? res.email : "";
}

export async function resendVerificationEmail(): Promise<{ alreadyVerified: boolean }> {
  if (isMockApi || !API_BASE) return delay({ alreadyVerified: true }, 300);
  const res = await authFetch<{ alreadyVerified?: boolean }>("/auth/verify/request", {
    method: "POST",
    body: JSON.stringify({}),
  });
  return { alreadyVerified: res.alreadyVerified === true };
}

export async function deleteAccount(password: string): Promise<void> {
  if (isMockApi || !API_BASE) return delay(undefined, 400);
  await authFetch("/auth/account", { method: "DELETE", body: JSON.stringify({ password }) });
}

// ------------------------------------------------------------------ profile
function normalizeProfile(raw: unknown): Profile {
  const p = (raw && typeof raw === "object" ? raw : {}) as Partial<Profile>;
  return {
    email: typeof p.email === "string" ? p.email : "",
    verified: p.verified === true,
    displayName: typeof p.displayName === "string" ? p.displayName : "",
    currentSession: typeof p.currentSession === "string" ? p.currentSession : "",
    expectedGrad: typeof p.expectedGrad === "string" ? p.expectedGrad : "",
  };
}

export async function getProfile(): Promise<Profile> {
  if (isMockApi || !API_BASE) return delay({ ...mockState.profile }, 200);
  const res = await authFetch<{ profile?: unknown }>("/me/profile");
  return normalizeProfile(res.profile);
}

export async function updateProfile(
  changes: Partial<Pick<Profile, "displayName" | "currentSession" | "expectedGrad">>,
): Promise<Profile> {
  if (isMockApi || !API_BASE) {
    mockState.profile = { ...mockState.profile, ...changes };
    return delay({ ...mockState.profile }, 300);
  }
  const res = await authFetch<{ profile?: unknown }>("/me/profile", {
    method: "PUT",
    body: JSON.stringify(changes),
  });
  return normalizeProfile(res.profile);
}

// ----------------------------------------------------------------- sessions
export async function listSessions(): Promise<ActiveSession[]> {
  if (isMockApi || !API_BASE) return delay([...MOCK_SESSIONS], 200);
  const res = await authFetch<{ sessions?: unknown }>("/auth/sessions");
  return (Array.isArray(res.sessions) ? res.sessions : []).map((s) => {
    const row = (s && typeof s === "object" ? s : {}) as Partial<ActiveSession>;
    return {
      id: typeof row.id === "string" ? row.id : "",
      current: row.current === true,
      createdAt: typeof row.createdAt === "string" ? row.createdAt : "",
      expiresAt: typeof row.expiresAt === "string" ? row.expiresAt : "",
      userAgent: typeof row.userAgent === "string" ? row.userAgent : "",
      ipAddress: typeof row.ipAddress === "string" ? row.ipAddress : "",
    };
  });
}

export async function revokeSession(sessionId: string): Promise<void> {
  if (isMockApi || !API_BASE) return delay(undefined, 200);
  await authFetch(`/auth/sessions/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
}

export async function revokeOtherSessions(): Promise<void> {
  if (isMockApi || !API_BASE) return delay(undefined, 200);
  await authFetch("/auth/sessions/revoke-others", { method: "POST" });
}

// ----------------------------------------------------------------- passkeys
/** Whether this browser can do WebAuthn at all (feature-detect, no network). */
export function passkeysSupported(): boolean {
  return typeof window !== "undefined" && "PublicKeyCredential" in window && !!navigator.credentials;
}

function base64urlToBuffer(value: string): ArrayBuffer {
  const b64 = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = b64 + "=".repeat((4 - (b64.length % 4)) % 4);
  const raw = atob(padded);
  const bytes = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
  return bytes.buffer;
}

function bufferToBase64url(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let raw = "";
  for (let i = 0; i < bytes.length; i++) raw += String.fromCharCode(bytes[i]);
  return btoa(raw).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

interface WireCreationOptions {
  challenge: string;
  user: { id: string; name?: string; displayName?: string };
  excludeCredentials?: { id: string; type?: string; transports?: string[] }[];
  [key: string]: unknown;
}

interface WireRequestOptions {
  challenge: string;
  allowCredentials?: { id: string; type?: string; transports?: string[] }[];
  [key: string]: unknown;
}

function normalizePasskey(raw: unknown): Passkey {
  const p = (raw && typeof raw === "object" ? raw : {}) as Partial<Passkey>;
  return {
    id: typeof p.id === "number" ? p.id : 0,
    label: typeof p.label === "string" ? p.label : "Passkey",
    createdAt: typeof p.createdAt === "string" ? p.createdAt : "",
    lastUsedAt: typeof p.lastUsedAt === "string" ? p.lastUsedAt : null,
  };
}

export async function listPasskeys(): Promise<Passkey[]> {
  if (isMockApi || !API_BASE) return delay([...mockState.passkeys], 200);
  const res = await authFetch<{ passkeys?: unknown }>("/auth/passkeys");
  return (Array.isArray(res.passkeys) ? res.passkeys : []).map(normalizePasskey);
}

export async function deletePasskey(id: number): Promise<void> {
  if (isMockApi || !API_BASE) {
    mockState.passkeys = mockState.passkeys.filter((p) => p.id !== id);
    return delay(undefined, 200);
  }
  await authFetch(`/auth/passkeys/${id}`, { method: "DELETE" });
}

/** Full registration ceremony: options -> navigator.credentials.create ->
 * verify. Requires the current password — the backend re-authenticates at the
 * options step before starting the ceremony. */
export async function registerPasskey(label: string, password: string): Promise<Passkey> {
  if (isMockApi || !API_BASE) {
    const passkey: Passkey = {
      id: mockState.nextPasskeyId++,
      label: label || "Passkey",
      createdAt: new Date().toISOString(),
      lastUsedAt: null,
    };
    mockState.passkeys.push(passkey);
    return delay(passkey, 600);
  }

  const options = await authFetch<WireCreationOptions>("/auth/passkeys/register/options", {
    method: "POST",
    body: JSON.stringify({ password }),
  });
  const publicKey: PublicKeyCredentialCreationOptions = {
    ...(options as unknown as PublicKeyCredentialCreationOptions),
    challenge: base64urlToBuffer(options.challenge),
    user: {
      ...(options.user as unknown as PublicKeyCredentialUserEntity),
      id: base64urlToBuffer(options.user.id),
    },
    excludeCredentials: (options.excludeCredentials ?? []).map((c) => ({
      type: "public-key" as const,
      id: base64urlToBuffer(c.id),
      transports: c.transports as AuthenticatorTransport[] | undefined,
    })),
  };

  const created = (await navigator.credentials.create({ publicKey })) as PublicKeyCredential | null;
  if (!created) throw new Error("Passkey creation was cancelled.");
  const response = created.response as AuthenticatorAttestationResponse;
  const credential = {
    id: created.id,
    rawId: bufferToBase64url(created.rawId),
    type: created.type,
    authenticatorAttachment: created.authenticatorAttachment ?? undefined,
    clientExtensionResults: created.getClientExtensionResults(),
    response: {
      attestationObject: bufferToBase64url(response.attestationObject),
      clientDataJSON: bufferToBase64url(response.clientDataJSON),
      transports:
        typeof response.getTransports === "function" ? response.getTransports() : undefined,
    },
  };

  const res = await authFetch<{ passkey?: unknown }>("/auth/passkeys/register/verify", {
    method: "POST",
    body: JSON.stringify({
      credential,
      label,
      transports: credential.response.transports,
    }),
  });
  return normalizePasskey(res.passkey);
}

/** Full sign-in ceremony (usernameless / discoverable credential). */
export async function signInWithPasskey(rememberMe: boolean): Promise<AuthUser> {
  if (isMockApi || !API_BASE) {
    await delay(null, 600);
    if (mockState.passkeys.length === 0) throw new Error("No passkey registered on this device (demo).");
    return { ...mockState.user };
  }

  const options = await authFetch<WireRequestOptions>("/auth/passkeys/authenticate/options", {
    method: "POST",
    body: JSON.stringify({}),
  });
  const publicKey: PublicKeyCredentialRequestOptions = {
    ...(options as unknown as PublicKeyCredentialRequestOptions),
    challenge: base64urlToBuffer(options.challenge),
    allowCredentials: (options.allowCredentials ?? []).map((c) => ({
      type: "public-key" as const,
      id: base64urlToBuffer(c.id),
      transports: c.transports as AuthenticatorTransport[] | undefined,
    })),
  };

  const asserted = (await navigator.credentials.get({ publicKey })) as PublicKeyCredential | null;
  if (!asserted) throw new Error("Passkey sign-in was cancelled.");
  const response = asserted.response as AuthenticatorAssertionResponse;
  const credential = {
    id: asserted.id,
    rawId: bufferToBase64url(asserted.rawId),
    type: asserted.type,
    authenticatorAttachment: asserted.authenticatorAttachment ?? undefined,
    clientExtensionResults: asserted.getClientExtensionResults(),
    response: {
      authenticatorData: bufferToBase64url(response.authenticatorData),
      clientDataJSON: bufferToBase64url(response.clientDataJSON),
      signature: bufferToBase64url(response.signature),
      userHandle: response.userHandle ? bufferToBase64url(response.userHandle) : undefined,
    },
  };

  const res = await authFetch<{ user?: AuthUser }>("/auth/passkeys/authenticate/verify", {
    method: "POST",
    body: JSON.stringify({ credential, rememberMe }),
  });
  if (!res.user) throw new Error("Passkey sign-in failed.");
  return res.user;
}
