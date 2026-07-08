/**
 * The vendored design-system bundle (`_ds_bundle.js`) is authored as a plain
 * <script> — every component reads the bare global identifiers `React` /
 * `window.lucide`, it does not `import` them. This module's only job is to
 * make those globals exist *before* the bundle evaluates.
 *
 * Import ordering is what makes this safe: ES modules evaluate static
 * imports depth-first, in the order they're written, and a module fully
 * finishes evaluating before the next sibling import starts (as long as
 * there's no cycle and nothing here is async — both true here). So as long
 * as `./reactGlobal` is imported *before* `./_ds_bundle.js` in index.ts, this
 * file's top-level assignments are guaranteed to run first — no top-level
 * await, no dynamic import() race required.
 */
import React from "react";
import ReactDOM from "react-dom";
import * as ReactDOMClient from "react-dom/client";
import { icons, createElement, type IconNode } from "lucide";

declare global {
  interface Window {
    React: typeof React;
    ReactDOM: typeof ReactDOM & typeof ReactDOMClient;
    lucide: { createIcons: (options?: unknown) => void };
    DeciduousDesignSystem_6c95c0: Record<string, unknown>;
  }
}

window.React = React;
window.ReactDOM = { ...ReactDOM, ...ReactDOMClient };

function toPascalCase(name: string): string {
  return name.replace(/(\w)(\w*)(_|-|\s*)/g, (_m, g1: string, g2: string) => g1.toUpperCase() + g2.toLowerCase());
}

const iconMap = icons as unknown as Record<string, IconNode>;

/**
 * Renders every `<... data-lucide="name">` marker's icon as a *child* of the
 * marker, rather than replacing the marker element itself (which is what the
 * `lucide` npm package's own `createIcons()` does —
 * `element.parentNode.replaceChild(svgElement, element)`, see
 * node_modules/lucide/dist/esm/replaceElement.js).
 *
 * That matters because the markers are React-managed elements: once lucide's
 * own version swaps a marker for a freshly-created `<svg>`, React still
 * holds a reference to the original (now detached) element and keeps
 * writing prop updates to it — e.g. `data-lucide="sun"` after
 * `data-lucide="moon"` on a theme toggle. Those updates land on a node no
 * longer in the document, so the visible icon freezes on whatever it first
 * rendered. Rendering into the marker as a child instead keeps the marker
 * itself alive in the tree, so later attribute changes stay observable (see
 * `./icons.ts`'s MutationObserver) and keep re-rendering correctly.
 */
export function renderLucideMarkers(root: ParentNode = document): void {
  const markers = root.querySelectorAll<HTMLElement>("[data-lucide]");
  markers.forEach((el) => {
    const name = el.getAttribute("data-lucide");
    if (!name) return;
    if (el.dataset.lucideRendered === name) return; // already correct, skip the DOM churn

    const iconNode = iconMap[toPascalCase(name)];
    if (!iconNode) {
      if (import.meta.env.DEV) {
        // eslint-disable-next-line no-console
        console.warn(`[icons] "${name}" was not found in lucide's icon set.`);
      }
      return;
    }

    const svg = createElement(iconNode);
    svg.setAttribute("class", `lucide lucide-${name}`);
    // Carry over sizing the marker itself was given — design-system
    // components pass `style={{ width, height }}` on the `<i data-lucide>`
    // marker, matching how lucide's own createIcons() merges the marker's
    // attributes onto the resulting <svg> (see replaceElement.js).
    const style = el.getAttribute("style");
    if (style) svg.setAttribute("style", style);

    el.replaceChildren(svg);
    el.dataset.lucideRendered = name;
  });
}

// A few bundle components (AppShell, ScenarioTabs, Combobox) call
// `window.lucide.createIcons()` themselves after their own renders, with or
// without lucide's own `{ nameAttr, attrs, icons }` options shape. None of
// them override `nameAttr` away from `"data-lucide"` (renderLucideMarkers'
// only fixed assumption), so routing all of them through the same
// non-destructive renderer keeps every icon in the app on one safe path.
window.lucide = {
  createIcons: () => renderLucideMarkers(document),
};
