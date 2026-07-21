import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

// https://vite.dev/config/
export default defineConfig({
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
});
