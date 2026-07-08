// The vendored bundle is plain JS with no type declarations of its own (see
// _ds_bundle.js — a side-effect-only script, no import/export statements).
// This ambient declaration lets TS resolve the side-effect import in index.ts
// without requiring `allowJs` project-wide.
declare module "./_ds_bundle.js";
