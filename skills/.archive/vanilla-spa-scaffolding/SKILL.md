---
name: vanilla-spa-scaffolding
description: Assemble multiple HTML prototypes or form modules into a single working vanilla JS single-page application (SPA) with ES modules, tab navigation, local-first state, optional backend API, and Node-based verification tests. Use when the user provides several standalone HTML pages and asks to consolidate into one cohesive browser app without React/Vue/Angular.
version: "0.2"
---

# Vanilla SPA Scaffolding

## Trigger
- User supplies multiple HTML modules (forms, parsers, mappers, dashboards, upload pages, settings, help) and asks to merge them into one working site.
- Requirements explicitly say vanilla JS/HTML/CSS; no React/Vue/Angular/frameworks.
- App should run by opening `index.html` or `npx serve .` with no build step.

## Approach
1. Create source tree under the project root:
   - `/src/api/{client.js}` — fetch wrapper plus optional backend helpers
   - `/src/styles/main.css` — CSS variables, responsive flex/grid layout
   - `/src/utils/{helpers.js,validation.js,storage.js,parser.js,mapper.js}` — cross-cutting helpers
   - `/tests/test.js` — Node-based verification
   - `/templates/` or `/assets/` as needed
2. Write `index.html` as a single app shell with:
   - `<nav class="tabs" aria-label="Sections">` containing tab buttons
   - `<main id="mainContent">` containing `<section class="panel">` placeholders for each tab
   - `<footer>` with summary/badges and action buttons
3. Write `main.js` as an ES module (import maps or direct imports) that:
   - renders panels into the shell
   - wires tab switching and panels
   - syncs global project metadata into all form sections
   - saves/restores draft via localStorage
   - handles file input changes
   - calls API helpers if backend is wired
4. Write `package.json` with:
   - `"type": "module"` so ESM imports in `/src` and `/tests` work
   - `scripts.start` and `scripts.test`
5. Add a Node `tests/test.js` that asserts:
   - shell elements exist (`index.html` has `<main>`, `<nav>`, `<footer>`)
   - `main.js` exports functions and bootstrap calls
   - CSS has variables and responsive media queries
   - API client exposes helpers
   - utils folders export helpers
   - no React/Vue/Angular imports in source

## Verification Gate
Always verify before claiming completion:
```bash
node --check main.js
npm test
```
If Node warns about missing `"type": "module"`, patch `package.json` before delivery.

## Pitfalls
- Structural tests are not syntax coverage. `npm test` can pass while `main.js` contains a dangling `;` or unmatched braces that never execute in the tested paths. Always run `node --check` on every JS file first; it catches parse errors before any runtime test does.
- Avoid oversized whole-file patches from truncated reads. When `read_file` returns truncated output, use a small unique anchor for `patch` instead; otherwise you can reintroduce syntax errors, malformed strings, or remove needed closing delimiters.
- Local-first draft restore must be additive, not overwriting. Only restore draft values into existing form controls; do not synthesize new fields from the draft.
- When dynamically generating panels/sections, ensure callers like `countFields()` and form collection iterate over both statically present and dynamically inserted panels.
- Accessibility: add `aria-label`, `role`, and `tabindex` where listboxes/panels are dynamic; keep contrast via CSS variables.
- Draft restore: do not overwrite user input with empty draft values; only set values from draft when they exist.

## References
- `references/verification-scripts.md` — Node test patterns
- `references/session-notes.md` — CDM 2024 consolidation example
