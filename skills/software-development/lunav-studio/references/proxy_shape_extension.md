# Adding a new Proxy shape (Spatial Proxy Toolbox)

Pattern for extending LunaV Studio's Spatial Proxy Toolbox with a new `shape`.
Worked example:
- the AutoCAD-style `dimension` measure line (Path A label-only line + `feat/dimension-drag`
  draggable endpoints); BOTH shipped to `main` and are live on the Vercel URL.
  NOTE: an `annotation` arrow+text-box callout was prototyped in a prior session but was
  REVERSED by the founder — annotation was fully removed (schema CHECK, types.ts union,
  Viewer3D render branch, ProjectWorkspace button/handlers/modal all reverted). Do NOT
  reintroduce `shape:'annotation'` / `annotation_text` unless asked. The dimension tool now
  lives in its OWN "Dimension Tool" group BELOW the Spatial Proxy Toolbox (see relocation
  note below), and its Record tab is value-only (no unit selector).
Vercel builds `main` only — merging a feature branch to `main` IS the deploy trigger.

## When to use
Founder wants a new clickable thing in the 3D twin that is NOT a defect marker —
e.g. a measurement line, leader/callout, section cut. These belong in the
`proxies` table (intentionally NOT counted in severity analytics), not markers.

## The 4 touch-points (all required)
1. **schema.sql** — extend the `proxies` table:
   ```sql
   alter table public.proxies add column if not exists point_a jsonb;
   alter table public.proxies add column if not exists point_b jsonb;
   alter table public.proxies add column if not exists dimension_value text;
   ```
   Also widen the `shape` check: `check (shape in ('box','plane','dimension'))`.
2. **types.ts `ProxyShape`** — widen union + add fields:
   ```ts
   shape: "box" | "plane" | "dimension";
   point_a: { x: number; y: number; z: number } | null;
   point_b: { x: number; y: number; z: number } | null;
   dimension_value: string | null;
   ```
   Keep position_*/scale_* as-is; for a line proxy they're unused (position can
   hold the midpoint if convenient).
3. **Viewer3D.tsx** — in the `proxies.forEach((p) => { ... })` effect, add an
   early `if (p.shape === "dimension") { ...; return; }` branch BEFORE the
   box/plane mesh logic so it never falls through. Render recipe:
   - main `THREE.Line` between `point_a` / `point_b`
   - perpendicular tick `LineSegments` at each end (cross the line dir:
     `perp = new Vector3(-dir.y, dir.x, 0).normalize().multiplyScalar(1.2)`;
     watch the zero-length case → fall back to `(0,0,1.2)`)
   - two `ConeGeometry` arrowheads oriented with
     `quaternion.setFromUnitVectors(new Vector3(0,1,0), dir)` and negated dir
   - a `CSS2DObject` at the midpoint holding a `<div>` (label) or `<input>`
     (when actively edited)
   Add props `dimension_input?: string | null` and
   `onDimensionChange?: (id: string, value: string) => void` so the parent
   drives the editable center value; thread them through the destructure.
4. **ProjectWorkspace.tsx** — toolbox button (next to Cube/Plane under
   "Spatial Proxy Toolbox"); an `addDimension()` that inserts a `proxies` row
   with `shape:'dimension'` + a default `point_a/point_b` (e.g. an 8-unit segment
   along X at origin so it's visible immediately); a `dimension_input` state;
   an `onDimensionChange` handler calling `saveProxy({ dimension_value })`; and
   pass `dimension_input` / `onDimensionChange` to `<Viewer3D>`.

## Pitfalls (the ones that bit)
- **`isCSS2DObject` does NOT exist** on `CSS2DObject`. When tearing down a group
  that may contain a CSS2D label, guard with
  `if ((c as unknown as { element?: HTMLElement }).element) { ...element.remove(); }`
  — never `c.isCSS2DObject`.
- **Same-batch patch ordering** — adding a `useRef` and using it in another edit
  in the same batch triggers a transient "Cannot find name" LSP error that
  clears once both writes land. Confirm with a real `npm run build` at the end;
  don't "fix" by deleting the ref.
- **Type union must be widened in BOTH places** — `schema.sql` check AND
  `types.ts` union. Forgetting the TS union yields
  "comparison ... has no overlap" on `p.shape === "dimension"`.
- **LIVE DB CHECK CONSTRAINT is the #1 cause of a 400 on new shapes — adding
  columns is NOT enough.** Supabase derives the insert payload from `shape`
  FIRST; if `proxies.shape` CHECK only permits `'box','plane'`, inserting
  `shape:'dimension'` returns HTTP 400 *before* any column check.
  The `schema.sql` in the repo is the SOURCE OF TRUTH but is NOT auto-applied to
  the live DB — a code-only deploy that adds a new shape will 400 until the
  constraint is widened live. Always deliver a migration SQL the founder runs in
  Supabase SQL Editor. Idempotent pattern (safe to re-run):
  ```sql
  alter table public.proxies drop constraint if exists proxies_shape_check;
  alter table public.proxies
    add constraint proxies_shape_check
    check (shape in ('box','plane','dimension'));
  alter table public.proxies add column if not exists point_a jsonb;
  alter table public.proxies add column if not exists point_b jsonb;
  alter table public.proxies add column if not exists dimension_value text;
  alter table public.proxies add column if not exists dimension_unit text;
  alter table public.proxies add column if not exists dimension_note text;
  alter table public.proxies alter column dimension_value drop not null;
  ```
  (Annotation shape was removed — do NOT include `'annotation'` in the CHECK
  or an `annotation_text` column unless the founder reverses that decision.)
  Symptom signature: two identical `[Failed to load resource: 400 (proxies)]`
  errors on the click that creates the proxy. Fix = run the migration, NOT a
  code change (the code was already correct). Save the .sql to `~/Desktop/` and
  tell the founder to paste it into Supabase → SQL → New query → Run.
- **Don't guard the CHECK widening on constraint NAME.** A wrapper like
  `if not exists (select 1 from pg_constraint where conname='proxies_shape_check'
  and pg_get_constraintdef(oid) like '%dimension%') then ... end if;` is fragile:
  if the live constraint has an autogenerated/different name, the guard never
  matches and the migration silently does nothing while the founder still sees
  400s. Prefer unconditional `drop constraint if exists` + re-`add` (idempotent),
  OR after applying, verify with
  `select conname, pg_get_constraintdef(oid) from pg_constraint where
  conname='proxies_shape_check'` and check the definition actually lists
  `'dimension'`. Founder reporting \"applied with success\" is NOT proof — give
  them that SELECT when a 400 persists.
- **No Supabase CLI link in this env** — you cannot `supabase db push` yourself.
  Generate the migration as a re-runnable SQL file for the founder to apply
  manually. Never embed DB credentials/secrets in code or the migration.
- **Path A (label-only) when founder says "simpler".** For the Dimension tool
  the founder explicitly wanted simple: the center number is a free-text label
  the user types, NOT physically linked to the line length or to true-scale
  meters. Don't pull the scale-calibration feature into a "simpler" ask unless
  they ask for real-unit accuracy.

## Build / verify gate (mandatory before claiming done)
- `npm run build` (Next.js + Turbopack) → "Compiled successfully" + TS pass.
  A green local build is NOT proof a Vercel deploy will pass — see
  `references/model_scale_calibration.md` Verification pitfalls.
- Runtime smoke: `npm run dev` (background) + `curl localhost:3000` → 200.
  Do NOT spawn headless Chrome on MARU's machine. Kill dev before commit.
- Branch isolation: `git checkout -b feat/<name>`. Rollback:
  `git checkout main && git branch -D feat/<name>`.

## Extending the Dimension tool — draggable endpoints (`feat/dimension-drag`)
What "users convenience in mind" required beyond the static line:
- **On-model placement.** A new dimension's default endpoints were hardcoded at
  origin (`-4..+4` on X). Fix: when `point_a/point_b` equal that sentinel,
  override them to sit on the model bounding box (center + ~40% span along X
  `scene.getObjectByName('modelGroup')` → `.geometry.boundingBox` after
  `computeBoundingBox()`). This makes every new measure line land ON the geometry.
- **Draggable endpoint handles — AutoCAD-style, NOT bulky nodes.** Add two
  thin grip meshes per dimension. Founder explicitly rejected "bulky node end"
  handles: use `new THREE.OctahedronGeometry(0.35, 0)` (a small diamond pick)
  in the line color, NOT `SphereGeometry(0.7)` blobs. Register them in a handle
  map so the pointer loop can pick them.
  - **GOTCHA — shared handle map across effects.** The proxy-sync effect rebuilds
    the whole group every sync (disposes children), so it must populate a
    **top-level `useRef`** (`endpointHandlesRef`, declared next to `raycasterRef`),
    NOT a local `const endpointHandles` inside the scene-bootstrap `useEffect`. A
    local one is out of scope for the sync-effect and the pointer handlers. Use
    `endpointHandlesRef.current.set(p.id, { a: hA, b: hB })`.
  - **Pick function** `pickEndpoint(e)`: `raycaster.setFromCamera(ndc, camera);
    intersectObjects([...Object.values(endpointHandlesRef.current).flatMap(h =>
    [h.a,h.b)], false)` → returns `{ id, end }` or null.
  - **Drag loop** (attach to `renderer.domElement`): on pointerdown, if
    `pickEndpoint` hits, set `dragState={id,end}`, `controls.enabled=false`,
    `renderer.domElement.setPointerCapture(e.pointerId)`. On pointermove, raycast
    the **model mesh**; if hit, snap endpoint to the surface hit; else fall back
    to a depth plane at the endpoint's current distance from camera. On
    pointerup, `onDimensionDrag(id, end, worldPos)` → parent persists `point_a` /
    `point_b`, then `controls.enabled=true`, release capture.
  - **Discoverability**: idle pointermove sets cursor `'grab'` when over a handle
    (respect `addMarkerMode` so it doesn't clobber the marker crosshair),
    `'default'` otherwise.
- **Prop wiring**: add `onDimensionDrag?: (id, end:'a'|'b', pos:{x,y,z}) => void`
  to `Viewer3DProps`; thread it through the component destructure AND
  `liveRef.current` (the event handlers close over `liveRef`, not the prop, so
  without this the handler is always undefined). Parent `onDimensionDrag` does
  `supabase.from('proxies').update({ point_a | point_b })`.

## Dimension Tool — founder-driven UX corrections (this session)
Two corrections the founder made after the first build; bake these into the
pattern so they aren't re-litigated:
- **Relocation out of the Spatial Proxy Toolbox.** The Dimension button was moved
  OUT of the "Spatial Proxy Toolbox" group (which holds Cube/Plane) into its OWN
  "Dimension Tool" group rendered BELOW it in `ProjectWorkspace.tsx`. Reason:
  the toolbox group implies the same primitive-spawn behaviour; dimension is a
  distinct inspect-and-record flow. When adding similar inspect tools later,
  prefer a dedicated group rather than cramming into the primitive toolbox.
- **Value-only Record tab (no unit selector).** The founder removed the unit
  selector (m/cm/ft/in + custom) from the Record Dimension modal. The "Measured
  value" field became a free-text **"Value"** input (type=text) where the user
  types number + unit together (e.g. "12.4 m overall width"). `dimension_unit`
  is still written by the save path but always as `""` — do NOT re-add a unit
  selector unless asked. Rationale: the model is a representation, not
  survey-accurate, so forcing a unit taxonomy adds friction with no accuracy gain.

## NEXT.JS PITFALL — static prerender crashes on Supabase client (FIRST-CLASS)
Symptom: `next build` fails at "Generating static pages" with
`@supabase/ssr: Your project's URL and API key are required to create a Supabase
client!` for a page like `/update-password`. Cause: that page called
`createClient()` (from `@/lib/supabase/client`, a **browser** client) at the top
of the component body, so Next's static prerender pass executed it with no env
loaded. The OTHER pages avoided this by lazy-initing the client inside an effect
or handler.
- **Fix**: replace the top-level `const supabase = createClient()` with a lazy
  accessor:
  ```ts
  const supabaseRef = useRef<ReturnType<typeof createClient> | null>(null);
  function getSupabase() { if (!supabaseRef.current) supabaseRef.current = createClient(); return supabaseRef.current; }
  ```
  Then call `getSupabase()` inside the `useEffect` / submit handler only. Prerender
  never constructs the client, so no env needed at build time. (Remember to add
  `useRef` to the React import if missing, and replace every `supabase.` call site
  with `getSupabase().`.)
- This is the recurring pattern for ANY pinned page that touches Supabase at
  module/render top level — audit before a build if a new route fails prerender.
