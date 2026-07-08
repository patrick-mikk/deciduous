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
  build: {
    // The vendored design-system bundle (design/claude-design-output/_ds_bundle.js,
    // copied into src/ds/) is plain modern JS (arrow fns, optional chaining, etc.)
    // authored for evergreen browsers — esnext avoids unnecessary down-leveling.
    target: "esnext",
  },
});
