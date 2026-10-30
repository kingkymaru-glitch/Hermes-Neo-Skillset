---
name: client-side-supabase
description: >-
  Replace legacy REST routes with Supabase-backed React context helpers, implement
  deep-linking / camera fly-to from URL params, and wire Supabase persistence
  into Vite/React apps that use Cesium or other 3D viewers. Trigger on: "replace
  fetch with Supabase", "entity CRUD context", "Supabase persistence hooks",
  "load from cloud", "save to cloud", "URL deep-linking", "?model_id=",
  "fly camera to id", "Context API + Supabase", "remove /api/* route", or any
  R-Tessera-style live/deploy fix where client code should read directly from
  Supabase instead of an intermediate backend.
category: database
---

# Client-side Supabase wiring for Vite/React + 3D viewers

Covers the repeatable pattern for moving entity/asset CRUD out of a legacy
backend API and into a React context backed by Supabase, plus URL-driven
camera-fly deep-links on top of Cesium-style viewers.

## When to use
- You have `fetch('/api/...')` in a React/Vite app and want to eliminate it.
- You need browser-refresh persistence for placed entities/assets.
- You want `?id=` or `?model_id=` deep-links to fly the 3D camera to the
  matching row.

## Workflow: replace a legacy fetch with a context helper

1. Define the entity table shape in SQL, create + push the migration, and
   lock in the column/field names. Prefer snake_case DB names
   (`model_url`, `latitude`, `longitude`) and map them explicitly in
   the JS layer.

2. Incrementally move logic into context:
   - load helpers: `supabase.from(...).select(...)` at mount
   - add/update/delete helpers: write immediately, then reload/merge
   - optimistic local updates are fine; reconcile by reload from cloud
     after writes.

3. Avoid aliasing collisions in the destructuring boundary. If the context
   exports both reactive state and a same-named cloud helper, alias at the
   import site, e.g. `addNode: addNodeFromCloud`. Then call only the
   cloud helper from one-off user-event handlers.

4. In components that read entity state, guard undefined before render:
   - destructure with fallbacks, e.g. `const { status } = entity || {}`
   - render stable strings so React doesn't crash on `undefined`

## Deep-linking pattern

- Read `URLSearchParams` with `new URLSearchParams(window.location.search)`.
- Fetch the matching row from Supabase.
- Wait one animation frame for the 3D engine to mount, then call
  `viewer.camera.flyTo({ destination, orientation, duration })`.

## Node List item click → camera fly-to

Reuse the existing `viewer.camera.flyTo(...)` already wired in `App.jsx`
(the `?model_id=` deep-link / "Locate Me" path) — do NOT create a second
Cesium viewer or separate camera controller. There is exactly ONE `viewerRef`
in the tree; route every fly-to through it.

1. The Node List flyout renders node-group rows from `useEdgeData()` node state.
2. Each row's `onClick` reads the node's `lat`/`lon` (and optional `height`),
   guards undefined, then:
   ```jsx
   const viewer = viewerRef.current
   if (!viewer) return
   viewer.camera.flyTo({
     destination: Cartesian3.fromDegrees(Number(lon), Number(lat), (Number(height) || 0) + 80),
     orientation: { heading: 0, pitch: CesiumMath.toRadians(-25), roll: 0 },
     duration: 2,
   })
   ```
3. If `viewerRef.current` is null (Viewer not yet mounted), open the node
   editor first so the Viewer mounts, then fly.

## Workflow: add an optional column / field end-to-end

Use this when the user wants a new optional attribute on an existing entity
(e.g. "add an external URL to node groups"). Touch every layer so the value
survives creation, reload, and render:

1. **Migration** — add the column (snake_case) with `IF NOT EXISTS` so re-runs
   are idempotent:
   ```sql
   ALTER TABLE public.nodes ADD COLUMN IF NOT EXISTS portal_url text;
   ```
   Commit the file under `supabase/migrations/`. This does NOT apply to the
   live DB automatically (see Pitfalls — Vercel never runs migrations).

2. **Context: map-in on load** — in the `loadNodesFromCloud` row→object map,
   add `portal_url: r.portal_url || null`.

3. **Context: map-out on save** — in `saveNodeToCloud`, add
   `portal_url: node.portal_url || null` to the upsert payload.

4. **Every modal surface that creates/edits the entity.** In R-Tessera this is
   TWO separate components and both must get the field or it silently drops:
   - `NewNodeGroupModal` (center modal, group-only) — add a `portalUrl` field
     to `useState`, a labeled `<input>` with the default as both initial value
     and `placeholder`, and `portal_url` in the `onCreate` payload.
   - `NodeEditorModal` (per-node inspection drawer) — same `portalUrl` field in
     its own `useState`/`buildPayload`, seeded from `node.portal_url`.
   Normalize on submit: `const v = (form.portalUrl || '').trim() || DEFAULT`.

5. **External launch action** — in the drawer footer, a button that opens the
   link with a fallback default:
   ```jsx
   <button onClick={() => window.open(node?.portal_url || 'https://lunavsolution.vercel.app', '_blank')}>
     Launch Twin Portal ↗
   </button>
   ```
   Add a `.modal-foot-btn.portal` style (cyan gradient) to mirror existing
   `.primary`/`.danger` foot buttons.

6. **Verify** — `npm run build` (exit 0), then commit + push main.

## Build + deploy guard

- Run `npm run build` after each logical chunk.
- Commit + push to main; Vercel auto-builds and promotes.
- Do not rely on `vercel deploy/alias` for primary deploys.

## Pitfalls

- Supabase does not run migrations during Vercel builds. Use `supabase db push`
  against the live project and verify with a live `supabase db query --usurp`
  proxy or dashboard SQL proof. See `references/vercel-migrations-not-applied.md`
  for the live-fix pattern.
- The dashboard shows the **Publishable key** (`sb_publishable_...`), not
  "anon". Long keys must be stored/read in full; partial keys cause 401s.
- If an env-backed client throws at module-load (`supabaseUrl is required`),
  make it resilient so the page shows "Backend not configured" instead of
  crashing blank, and set the env var in Vercel and redeploy.
- Aliased destructuring is easy to get wrong. After patching, grep the file
  for bare `await addNode(payload)` / `await updateNode(id, payload)` /
  `await removeNode(id)` to catch calls that still hit the reactive updater
  instead of the cloud helper.
- Adding an optional field: the SAME field often lives in more than one modal
  (R-Tessera has both `NewNodeGroupModal` and `NodeEditorModal`). Update every
  surface plus the context map-in/map-out, or the value is created-but-never
  shown or saved-but-never-loaded.
- A user report of "broken links" / "dead buttons" may reference UI that does
  NOT exist in the current build. Before patching, run `npm run dev` (usually
  :5174), open the relevant flyout, and snapshot the DOM + console. In one
  R-Tessera session the user reported "several broken sensor links" but the
  only `<a>` links present were working recon cards (USGS/Windy/NASA) and the
  GLB Studio LuNav CTA — sensor rows are drill-down `<button>`s, not anchors.
  Verify first, then report findings and ask for the exact link text / a
  screenshot rather than guessing. (See `references/rtessera-ui-surface-inventory.md`.)

## Reference

See `references/entity-crud-context-pattern.md` for the R-Tessera example
surface: `EdgeDataContext`, `App.jsx`, and a `?model_id=` flyto effect, and
`references/vercel-migrations-not-applied.md` for application/verification.
See `references/add-optional-field-recipe.md` for the end-to-end "add an
optional column/field" walkthrough (migration → context → both modals → launch).
See `references/rtessera-ui-surface-inventory.md` for the current flyout/link
inventory (what each panel contains, which links exist and resolve, and the
known `public.assets` missing-table console error) plus the camera fly-to note.
