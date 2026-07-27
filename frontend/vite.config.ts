import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

/**
 * Refuse to bake the offline demo adapter into a deployable bundle.
 *
 * `VITE_API_BASE=mock` (src/api/client.ts `isMockApi`) is a *local* convenience
 * for working on screens with no backend running. Vite inlines env vars at
 * build time, so a stray `frontend/.env` left over from that workflow silently
 * ships a `dist/` that renders seeded sample transcripts/GPA to real users —
 * exactly the kind of defect that survives a "looks fine locally" check,
 * because locally it *is* what you asked for. Fail the build loudly instead.
 *
 * Escape hatch for publishing an intentional demo build: ALLOW_MOCK_BUILD=1.
 */
function assertNotMockBuild(mode: string): void {
  const env = loadEnv(mode, process.cwd(), "");
  if (env.VITE_API_BASE !== "mock") return;
  if (process.env.ALLOW_MOCK_BUILD === "1") {
    console.warn("\n[deciduous] ALLOW_MOCK_BUILD=1 — building a DEMO bundle (mock API, sample data).\n");
    return;
  }
  throw new Error(
    [
      "",
      "Refusing to build: VITE_API_BASE=mock would ship the offline demo adapter.",
      "",
      "The resulting dist/ serves seeded sample data (transcript, programs, GPA)",
      "instead of the real API, for every visitor.",
      "",
      "Fix: remove `VITE_API_BASE=mock` from frontend/.env (or delete the file) and rebuild.",
      "Intentional demo build? Re-run with ALLOW_MOCK_BUILD=1.",
      "",
    ].join("\n"),
  );
}

// https://vite.dev/config/
export default defineConfig(({ command, mode }) => {
  if (command === "build") assertNotMockBuild(mode);

  return {
    plugins: [react()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "src"),
      },
    },
    server: {
      // Dev-only same-origin bridge to the Flask backend. Set `VITE_API_BASE=/api`
      // in `frontend/.env` and requests go browser -> Vite (this origin) -> Flask,
      // instead of a direct cross-origin fetch to `http://localhost:5000`.
      //
      // This matters specifically in GitHub Codespaces (and any HTTPS-forwarded
      // dev tunnel): the browser only ever sees the forwarded HTTPS
      // `*.app.github.dev` origin Vite is served on. A direct fetch from that
      // HTTPS page to `http://localhost:5000` would either be blocked as mixed
      // content or -- worse -- silently resolve `localhost` to the *browser's
      // own machine* rather than the Codespace container, so it would never
      // reach the backend at all. Proxying here keeps every `/api/*` call
      // same-origin from the browser's point of view, which also means the
      // `csrf_token` / session cookies the backend sets (see
      // `backend/api/auth.py`) land as first-party cookies on that same origin
      // -- no dropped `Set-Cookie`, no empty `X-CSRF-Token` from
      // `ensureCsrfToken()` (`src/api/client.ts`). Without this proxy, the CSRF
      // fetch never lands on Flask, the cookie is never set, and every
      // subsequent guarded POST (signup/signin included) 403s with an empty
      // double-submit header.
      proxy: {
        "/api": {
          target: "http://localhost:5000",
          changeOrigin: true,
          // The backend never sets an explicit cookie `Domain` (no
          // SESSION_COOKIE_DOMAIN in backend/config_app.py), so this is a no-op
          // today -- kept as a safety net so a future Domain-scoped cookie still
          // rewrites to "host-only" and attaches to whatever origin Vite is
          // actually served on (e.g. the Codespaces forwarded host) rather than
          // being silently dropped for not matching "localhost".
          cookieDomainRewrite: "",
        },
      },
    },
    build: {
      // The vendored design-system bundle (design/claude-design-output/_ds_bundle.js,
      // copied into src/ds/) is plain modern JS (arrow fns, optional chaining, etc.)
      // authored for evergreen browsers — esnext avoids unnecessary down-leveling.
      target: "esnext",
    },
  };
});
