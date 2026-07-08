import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import { ThemeProvider } from "@/theme/ThemeProvider";
import { startIconAutoRefresh } from "@/ds/icons";
import App from "./App";
import "@/styles/index.css";

// Keep Lucide's `<i data-lucide="...">` markers rendered as real SVGs across
// the whole app (see src/ds/icons.ts) — most design-system components rely
// on the caller to do this rather than calling window.lucide.createIcons()
// themselves.
startIconAutoRefresh();

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <BrowserRouter>
      <ThemeProvider>
        <App />
      </ThemeProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
