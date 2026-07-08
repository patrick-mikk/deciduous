/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL of the Flask API, e.g. "https://planner.mikkelsen.ca/api". Unset in dev → mock adapter. */
  readonly VITE_API_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
