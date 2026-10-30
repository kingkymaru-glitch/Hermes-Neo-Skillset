---
name: vanilla-fe-debug
description: >
  Debug non-functional interactive elements in vanilla HTML/CSS/JS apps served locally or statically.
  Covers the common failure modes where buttons, tabs, and forms render but do nothing,
  especially after initial scaffold or module-loading changes.
  Trigger on: "dead button", "buttons don't work", "click does nothing",
  "tabs not switching", "nothing happens when I click", "interactive elements dead",
  "page is static", "JS not running", or any "it looks right but nothing responds" report.
---

# Vanilla FE Debug — Dead Interactive Elements

## Trigger
- Interactive controls render visually but produce no response.
- Tabs, forms, uploads, mappings, or footer actions are inert after load.
- Local dev server returns 200 HTML/JS, but runtime does not bind events.

## Core Approach
Treat it as a JS runtime load failure first, not a CSS or HTML markup issue.
Rendered buttons with no handlers will look fine and click with no effect.

## Step 1 — Verify Script Delivery
- Fetch the JS bundle URL(s) directly from the browser or via `curl -I`:
  - `curl -I http://localhost:<port>/<script-path>`
- Expect `200 OK` and a non-zero `Content-Length`.
- If `404` / cross-origin block / empty body, the script never arrives.

## Step 2 — Verify JS Execution Path
- Open DevTools Console:
  - Check for `SyntaxError`, `ReferenceError`, `TypeError`.
- If the page uses `<script type="module">` and the browser/serve combo rejects it:
  - The script is fetched but not executed; controls stay inert.
  - Indication: dynamic `import('./main.js')` or module imports throw synchronously.
- If imports from `./src/...` fail because paths are wrong for the served root:
  - Repo layout does not match what the page requests; modules never resolve.

## Step 3 — Fix Module-Load Failures
Two safe resets:
- Preferred: bundle into a single non-module script and load with `<script src="assets/app.bundle.js"></script>`.
- Alternative: keep modules, but use a real build server with correct root mapping (Vite/Parcel) and verify `import` paths exactly match served paths.

Bundling notes:
- Remove all `import ... from ...` lines.
- Remove all `export ...` keywords from lib files before concatenation.
- Keep entry-point code as-is after its dependency code.

## Step 4 — Rebind Events After DOM Changes
If panels/sections are replaced with `outerHTML = ...`:
- Event listeners attached to replaced nodes are lost.
- Reattach handlers from surviving parents, or attach to document-root selectors,
  or bind via event delegation on a stable ancestor.

## Step 5 — Re-check After Fix
- `curl` the script path again; expect 200 + valid JS.
- Re-test interactivity in the browser.
- If still inert, read the first console error and continue from there.

## Pitfalls
1. `node --check` passing is not evidence the browser executed the script.
   It proves syntax is valid in Node, not that the browser load path succeeded.
2. `<script type="module">` is not always transparent on naive static serves.
   Prefer non-module bundles for simple localhost demos.
3. `DOMContentLoaded` handlers never fire if the script is never executed.
4. Paths like `./utils/helpers.js` assume root mapping; mismatched roots silently break module resolution.
5. Replacing DOM nodes (`outerHTML = ...`) destroys inline listeners; use delegation or re-bind.

## Pitfall — single transitive-import 404 aborts the WHOLE ES module graph
The #1 cause of "page renders, button does nothing, no error overlay, `node --check` passes"
on a `<script type="module">` app is a **missing transitive dependency**. If any vendored
import in the graph 404s (e.g. `three-addons/utils/BufferGeometryUtils.js` for three r160
when only `three.module.js` + `OrbitControls`/`GLTFLoader` were vendored), the browser
**fails the entire module** — the entry script's fetched 200 but its body never runs, so no
handlers bind. Symptom signature:
  - `curl` of the entry `.js` returns 200; `node --check` passes; page HTML looks complete.
  - In the browser: `el.onclick` is `null` (typeof `"object"`), a `window.__bootRan` flag set
    at the top of the binding IIFE stays `undef`, and `#p-log`/console may show nothing or a
    generic "Error creating WebGL context" if a top-level renderer ctor also throws.
This is invisible to `curl`/`node --check` — you must execute the page in a real browser.

### Decisive diagnostic: drive local Chrome via DevTools CDP
`browser_exec` is BLOCKED from localhost/private addresses, so it cannot reach the local
server. Instead launch a local headless Chrome (it IS allowed — it's a local process, not the
browser tool) and probe over the Chrome DevTools Protocol. A ready harness is in
`scripts/cdp_localhost_probe.mjs`:
  - `curl`/`node --check` only prove the ENTRY script loaded — NOT module-graph resolution.
  - The probe reports: each `.js`/`.css` HTTP status (non-200 = the break), `onclick` type
    (`object`=null/unbound vs `function`=bound), a `window.<BOOT>` flag (set to `true` as the
    first line of the binding IIFE to confirm it ran), and console/exceptions.
  - Add `window.__bootRan = true;` as the FIRST line inside the binding IIFE and
    `document.getElementById('p-log').textContent = '[boot] entered\n';` so the probe can
    distinguish "module never ran" from "ran but threw later".
  Run:
    node scripts/cdp_localhost_probe.mjs http://localhost:8753/web/index.html p-run __bootRan
  Read output in this order: (1) any non-200 `.js`/`.css` → that's the missing import;
  (2) `onclickType` `object`(unbound) vs `function`(bound); (3) `bootRan` `undef` = IIFE never
  ran; (4) console/exception block for the actual import error.

### Fix
Fetch the missing vendored file at the EXACT version the rest of the vendor tree uses
(`curl -fsSL https://unpkg.com/three@<REV>/examples/jsm/<path> -o <vendor>/<path>`), then
re-run the probe until every `.js` is 200 and `onclickType` is `function`. Do NOT assume
`node_modules` presence — vendored trees drift from their package versions.

## Pitfall — top-level renderer ctor kills the whole script
If a `<script type="module">` constructs `new THREE.WebGLRenderer(...)` (or any GPU/3D context)
at TOP LEVEL, before the binding IIFE, a context-creation failure (headless, disabled GPU,
old hardware) throws at module-eval time and the binding IIFE never runs — same "dead button"
symptom, different root. Keep viewer/scene init INSIDE a try/catch and bind the functional
panels (upload/pipeline/forms) independently so a render failure can't take down the controls.

## Pitfall — popup-blocker: `window.open` after `await` silently does nothing
A button that fetches a token/URL via `await` and THEN calls `window.open(url, "_blank")`
looks like it "did nothing / opened no tab" — the browser blocks the post-await popup
because it wasn't initiated by the user gesture in the same tick. **Fix:** open the window
SYNCHRONOUSLY inside the click handler first, then set its location after the await:
```js
const popup = window.open("", "_blank");
const { data } = await fetchToken();
(popup ? (popup.location.href = url) : window.open(url, "_blank"));
```
This also applies to SPAs (Next/React) — see `ss-rover-cloud-dev` for the exact
Supabase-rpc + `popup.location.href` pattern that fixed a "Link to external site" button.
Always re-test the actual click; a green build will NOT catch a blocked popup.

## Pitfall — React modal "stuck at top": `position:fixed` inside a transformed ancestor
A modal rendered with `position: fixed` (or any viewport-relative centering) that lives
INSIDE a parent with `transform`, `filter`, `perspective`, or `will-change` is positioned
relative to THAT ancestor, NOT the viewport. If the ancestor is an animated/scrollable
container (e.g. a `fade-up` card using `transform: translateY()`), the modal won't center
and can appear pinned at the top, clipped, or non-scrollable. Symptom: "modal opened but
stuck at the top / won't scroll / not centered", while the build passes and the DOM node
exists. This is common in Next.js dashboards where panels use entrance transforms.

Fix: render the modal through a React portal to `<body>` so it escapes the transformed
subtree, and make it scrollable with a sticky action bar:
```jsx
import { createPortal } from 'react-dom';
// mounted = typeof document !== 'undefined' guard for SSR/Next
{mounted && draft && createPortal(
  <CameraEditor onCancel={...} onSave={...} />,
  document.body
)}
```
For tall content give the overlay `position: fixed; inset: 0; overflow: auto` and the
dialog a max-height with its own scroll + sticky footer buttons. Distinct from the
popup-blocker pitfall above — both can co-occur (a "View on X" button that also opens a
modal). The portal fix is invisible to `tsc`/`next build`; only a real browser click proves it.

## Verification Evidence
Always report after a fix:
- The failing delivery mode or console error.
- The concrete change made.
- Browser confirmation that previously inert controls now respond.

When the server is localhost and `browser_exec` is blocked, use the bundled CDP probe
(`scripts/cdp_localhost_probe.mjs`) to get real browser execution evidence instead of guessing
from `curl`/`node --check`. See the "transitive-import 404" pitfall above for its usage.
