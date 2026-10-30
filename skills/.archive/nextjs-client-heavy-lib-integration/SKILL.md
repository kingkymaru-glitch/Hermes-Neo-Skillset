---
name: nextjs-client-heavy-lib-integration
description: Fix Cesium-in-Next.js octal SyntaxError via CDN load.
---

# Next.js + client-heavy library integration

## When to use
- Integrating Cesium / Three.js / any large client-only or wasm-embedding library
  into a Next.js app (App Router, deployed on Vercel).
- Symptom: `next build` SUCCEEDS, but the browser throws
  `SyntaxError: The only valid numeric escape in strict mode is '\0'`
  or `Octal escape sequences are not allowed in template strings` — and the
  page renders blank / "click does nothing".
- The console error points at a minified chunk (e.g. `06cei0ac5z5uk.js:877`),
  not your source.

## Root cause
The library (Cesium especially) ships ESM whose source embeds its wasm as a
base64 string containing `\0` (NUL) bytes. Inside a **template literal**, `\0`
and octal escapes are ILLEGAL in strict-mode ES modules. Next's production
minifier preserves those escapes in the output chunk. Node parses the *source*
fine (so `next build` passes), but the *minified chunk* fails to parse in the
browser → the whole route chunk dies → blank page.

Decisive proof (do NOT trust just the build): after `next build`, run
`node --check` on every output chunk. The offending chunk reports the
octal/template SyntaxError. See `references/verify-chunks.md`.

## Fix (Cesium worked example — generalizes)
DO NOT statically import the library into the Next bundle:
```ts
import { Viewer } from "cesium";                 // ❌ ends up minified with \0
import "cesium/Build/Cesium/Widgets/widgets.css"; // ❌
```
Instead load it from CDN at runtime inside the component, then use the global.
Full snippet in `references/cesium-cdn-load.md`. Summary:
1. In `useEffect`, inject `<script src="https://cdn.jsdelivr.net/npm/cesium@<ver>/Build/Cesium/Cesium.js">`
   and `<link rel="stylesheet" href=".../Widgets/widgets.css">`, await `window.Cesium`.
2. Use `const C = window.Cesium; new C.Viewer(container, {...})`.
This removes the library from the Next bundle entirely → no octal error.

### `transpilePackages: ['cesium']` does NOT fix it
Verified: after adding it, the same chunk still failed `node --check`. The
wasm-as-base64 string is emitted regardless. Only removing it from the bundle
(CDN load) works.

### `next/dynamic { ssr:false }` does NOT fix it — and is unnecessary
Common advice (incl. from well-meaning plans) says "wrap the Cesium component in
`next/dynamic(..., { ssr:false })`" to stop it server-executing. Two things:
1. It does NOT defeat the octal trap — the static `import ... from "cesium"`
   still lands in the bundle and still ships the `\0` escapes. Verify with the
   same `node --check` canary.
2. It is REDUNDANT: a plain `"use client"` component is already not
   server-rendered for its effects/WebGL — you do not need dynamic import at
   all. Mount the client component directly; SSR only pre-renders its markup
   shell, and Cesium init lives in `useEffect` which never runs on the server.
   Deviate from a prompt that mandates `next/dynamic` and explain why.

### `window.Cesium` is untyped — expect an ESLint `no-explicit-any` build gate
Because the CDN global is deliberately untyped (you skip `@types/cesium`), every
`any` in the component trips `@typescript-eslint/no-explicit-any`, which `next
build` treats as a HARD failure (lint runs during build). `tsc --noEmit` passes
but the build dies. Fix: a file-top
`/* eslint-disable @typescript-eslint/no-explicit-any */` WITH a comment stating
WHY (the global is inherently untyped by design). Do not sprinkle per-line
disables. Note `npx tsc --noEmit` is NOT a sufficient pre-build gate here — run
`npm run build` to catch the lint stage.

## Post-build verification (structural, no browser needed)
After `next build`, prove the CDN approach actually shipped (a static import or
a tree-shake can silently drop/keep the wrong path):
- `node --check` every `.next/static/chunks/*.js` → no octal/template error
  (the canary that the blank-globe crash is impossible).
- `grep -l 'cesium' .next/static/chunks/*.js` → EMPTY means the npm pkg is not
  bundled.
- `grep -rl 'cdn.jsdelivr.net/npm/cesium' .next/` → confirms the runtime CDN
  load string survived into a served chunk (the `{ver}` in the URL is NOT
  enough — grep the literal in build output, since a build error/removed import
  leaves it only in `.next/cache/webpack/*.pack`, not a real chunk).
- `curl -I` the CDN `Cesium.js` + `Widgets/widgets.css` → 200, so the browser
  can reach it.

## Live Cesium recolor / entity injection from React state
When UI state must repaint a Cesium entity live (risk-matrix recolor, scan-injection) do NOT call `dataSources.add` again — reloading the DataSource flickers and loses styling. Pattern that works:
- Keep `viewer`, the loaded `window.Cesium` (`C`), and the entity list in refs (`viewerRef`/`cesiumRef`/`entitiesRef.current`), set ONCE right after `await viewer.dataSources.add(dataSource)`.
- Run a separate `useEffect` keyed on the state change (`[selectedRisk]` etc.) that finds the target entity and mutates `entity.polygon.material`, `.outlineColor`, `.outlineWidth` DIRECTLY. No reload.
- Guard duplicate side-effects (injecting the same entity twice across re-renders) with a last-handled-id ref (`handledXRef.current === id ? return : (handledXRef.current = id)`).

## Matching a UI selection to a Cesium entity across DIFFERENT tables
When the interactive list/chat/lookup and the drawn GeoJSON come from separate tables that describe the same hazard with different words (register "Overhead Electric Power Lines" vs polygon "132kV line within crane slew arc"; a school hazard can share ZERO tokens with its polygon), text-overlap matching silently misses. Match on a stable shared key (e.g. `risk_category`/`category`) FIRST, hazard-token overlap second — and align that key across both tables at seed time, not at render time.

## Loading a GLB model into Cesium (CDN global) — use an Entity `model`, not `Model.fromGltf`
Placing/loading a .glb onto the globe: `C.Model.fromGltf({...})` + `viewer.scene.primitives.add(...)`
frequently throws `TypeError: C.Model.fromGltf is not a function` from the CDN-loaded `window.Cesium`
global (the primitive Model API is not reliably present/usable on the CDN build). The robust path is a
Cesium **Entity with a `model` graphics** — Cesium wires the GLB internally and the model rides the
entity's `position`, so moving the entity moves the building:
```ts
viewer.entities.add({ id, position: C.Cartesian3.fromDegrees(lon, lat, h),
  point: {...}, label: {...},
  model: { uri: "/models/building.glb", scale, heightReference: C.HeightReference.CLAMP_TO_GROUND } });
```
- **Do NOT probe dimensions with `C.Model.fromGltf`.** The probe calls the SAME primitive API that is
  missing on the CDN build, so it throws too — and a `try/catch` "fallback scale" then silently becomes
  the only path, landing every model at an arbitrary size that reads to the user as a units bug. Keep
  `model.scale` a USER-controlled value instead: `1` means "the GLB's own units", so a model authored in
  metres lands at true size and one scale slider is the single knob the user reasons about. (Anchoring to
  the ellipsoid makes on-screen size grow/shrink with zoom automatically; never fake this with a
  screen-fixed overlay.)
- Set `minimumPixelSize` (~6) on the model graphics so the building stays visible when zoomed far out
  instead of shrinking to nothing.
- Because the model is part of the entity, delete = `viewer.entities.remove(entity)` and move = set
  `entity.position` — no separate primitive bookkeeping.
- **Attach / swap / detach a model on a LIVE entity without recreating it:** keep the uploaded models in
  React state and run a `useEffect` keyed on that list. Per node, set
  `ent.model = buildModelGraphics(C, model, worldPos)` to attach or update, and `ent.model = undefined` to
  detach. No remove/re-add, so the pin, its colour and its selection state survive the swap — assigning or
  re-orienting a model in a separate editor updates the globe immediately.
- **Rotation:** map stored Euler degrees through `C.HeadingPitchRoll` and set
  `orientation: C.Transforms.headingPitchRollQuaternion(worldPos, hpr)` on the model graphics; do not try to
  rotate a model via `entity.orientation`, which is for the entity frame, not the model's own axis.
- **Keep a preview-stage offset separate from the map position.** An offset dialled in while framing the
  model in a standalone preview (orbit) stage is a framing aid, not a georeference — apply only rotation +
  scale on the globe so the node's lon/lat stays the single source of position truth.
- **Entity click picking:** `viewer.scene.pick(pos)?.id?.id` gives the entity id (e.g. `pin-1`); resolve it
  defensively (`picked?.id?.id ?? picked?.id ?? null`) and match by prefix. If the user says "I click the
  node and nothing opens", prefer a SINGLE-click open over `LEFT_DOUBLE_CLICK` — double-click on a small
  entity is unreliable in Cesium's input pipeline.

## Co-occurring React/Next client pitfalls (same component work)
- **A previously-working globe/page renders BLANK after you ran `npm run build`
  against a dev server that is still running on the same `.next`.** Both modes
  share `.next/`; the production build clobbers it, so the running dev server
  keeps serving HTML whose chunk/CSS filenames no longer exist → the browser
  logs 404s for `/_next/static/css/...css` and `/_next/static/chunks/*.js`
  (and "failed to load a stylesheet"), nothing hydrates, and the client-heavy
  component (Cesium globe) never mounts. Symptom = app shell renders but the
  globe/interactive part is gone, with NO JS source error. Fix: kill the dev
  process, `rm -rf .next`, restart `npm run dev`, hard-refresh. Rule: NEVER run
  `npm run build` while `npm run dev` is live on the same repo — stop dev (or
  build in a separate clone) first. Verify a live dev server with `curl -s -o
  /dev/null -w "%{http_code}" http://localhost:3000/_next/static/css/app/layout.css`
  → 200, not 404, before telling the user to look.
- **Popup blocker on `window.open` after `await`**: browsers block popups not
  opened in the same tick as the user gesture. Open synchronously FIRST, then
  navigate after the await:
  ```ts
  const popup = window.open("", "_blank");
  const { data } = await supabase.rpc("mint_handoff_token", {...});
  if (popup) popup.location.href = url; else window.open(url, "_blank");
  ```
- **Controlled input + async save jumps cursor to front**: keep a LOCAL
  `useState` form as the input's source of truth; debounce the persist (~600ms).
  Never write the server response back into the input-bound state.
- **Next.js middleware public routes**: any route absent from the `isPublic`
  matcher gets 307-redirected to `/login` for unauthenticated requests — even
  anon-readable pages. Add every publicly-reachable route (e.g.
  `/project/[id]/home`) to the matcher, or viewers see "nothing happens".
- **Runtime-only crashes build/lint miss** (full detail + diagnostic order in
  `references/runtime-crash-pitfalls.md`):
  - Hardcoded "Supabase not configured" sentinel: caused by the anon env vars
    being ABSENT in the *deployed* build (Vite inlines `import.meta.env` at
    build -> `undefined` in prod -> client factory returns null). Fix = set the
    Vercel Env Vars; lint/build stay green so this is browser-only.
  - Deleted `useRef`/`useState` during a refactor -> `ReferenceError: Can't find
    variable` on the user's click (a closure still references the name). Search
    the whole file for the identifier before committing.
- **Flex-collapse after adding a nav wrapper** (Cesium container goes 0px):
  The outer `<div>` uses `min-h-screen flex flex-col` (nav + globe shell). The
  shell has `height: 100%` which resolves to 0 inside a flex parent whose height
  is only `min-height` (not definite). Fix: change outer to `height: 100dvh`
  (or `h-screen`) so flex has a definite height to distribute, and add
  `style={{ flex: 1 }}` on the shell div so it fills the remaining space after
  the nav. Symptom: "no globe to begin with" despite no JS error, or Cesium
  initializes in a zero-height container -> invisible. Show a loading overlay
  (`!cesiumReady && !error` → "🌐 Loading globe…") so the user sees progress.
- **Cesium flyTo fires before CDN-loaded Cesium is ready**:
  The load effect seeds `site.center_lon/lat` from the DB, and a separate
  effect calls `viewer.camera.flyTo(...)`. But Cesium loads asynchronously from
  CDN — when the flyTo fires, `viewerRef.current` is null → skipped. After
  Cesium loads, center hasn't changed → flyTo never fires again → camera stays
  at (0, 20, 18M km). Fix: add a `cesiumReady` state, set after
  `new C.Viewer(...)`, include it in the flyTo effect's deps so it re-fires
  when the viewer becomes available.
- **Editor vs Viewer CSS inheritance gap** (e.g. remarks card):
  `.ph-remarks-view .ph-remarks-row` has `font-size: 0.76rem`, but
  `.ph-remarks-edit .ph-remarks-row` has NO font-size rule. When adding
  read-only fields (name, coordinate) inside the EDITOR (not the viewer), they
  inherit whatever size → mismatch. Always add a mirror rule for the edit
  context when adding display-only rows inside an edit container.
- **`@react-pdf/renderer` (and other Node-API PDF/browser-lib packages) break
  Next SSR via a static import**: statically importing the lib into any
  client-component module graph makes the page prerender throw "Element type is
  invalid ... but got: undefined" → route 500 (dev) / prerender error (build).
  Fix: `import()` BOTH the lib entry and the document component at RUNTIME
  inside the click handler (`const [{ pdf }, { default: Doc }] = await
  Promise.all([import('@react-pdf/renderer'), import('./CDMReport')])`), then
  build the element with `createElement(Doc, { ...props })` and cast `pdf`
  narrow (its TS signature only accepts `DocumentProps`). This code-splits the
  lib out of the SSR bundle. `tsc --noEmit` passes while `next build` still
  dies, so gate on the build. (Same root class as the Cesium octal trap: the
  lib must never be in the server-bundled chunk graph.)
