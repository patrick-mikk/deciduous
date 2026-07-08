import { renderLucideMarkers } from "./reactGlobal"; // also ensures window.lucide exists first

/**
 * Design-system components render icons as `<i data-lucide="name">` and rely
 * on the *caller* to swap those into real SVGs (a handful of components —
 * AppShell, ScenarioTabs, Combobox — already call `window.lucide.createIcons()`
 * themselves after their own renders; most don't). Rather than special-case
 * every component, we run a single throttled MutationObserver at the app root
 * (see App.tsx) that re-scans the DOM for un-rendered `[data-lucide]` markers
 * whenever the tree changes and swaps them in — using the same non-destructive
 * renderer `window.lucide.createIcons()` was wired to in `./reactGlobal.ts`
 * (see the comment there for why it must be non-destructive in a React tree).
 */
export const refreshIcons = renderLucideMarkers;

let scheduled = false;
function scheduleRefresh() {
  if (scheduled) return;
  scheduled = true;
  requestAnimationFrame(() => {
    scheduled = false;
    refreshIcons();
  });
}

/**
 * Starts observing `root` for DOM mutations and keeps lucide icons rendered.
 * Returns a cleanup function. Call once near the app root (see App.tsx).
 */
export function startIconAutoRefresh(root: Node = document.body): () => void {
  refreshIcons();
  const observer = new MutationObserver(scheduleRefresh);
  observer.observe(root, { childList: true, subtree: true, attributes: true, attributeFilter: ["data-lucide"] });
  return () => observer.disconnect();
}
