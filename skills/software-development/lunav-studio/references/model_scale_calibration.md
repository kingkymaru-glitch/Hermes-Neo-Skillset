# Model true-size scale calibration (LunaV Studio viewer)

How to let the user set a model's real-world size in the 3D twin WITHOUT
breaking marker placement. Established 2026-08-18 (branch `feat/model-scale`).

## The core invariant (do NOT violate)
Markers in LunaV Studio are **world-space siblings** — at click time they are
placed at the model's *rendered surface point* and stored as absolute
`position_x/y/z`, then added straight to `scene` in `Viewer3D.tsx`
(`markers.forEach(...)` / point+along+box sync). They are NOT children of the
model group. Therefore:

- Scaling the **model root** after markers exist moves the surface but leaves
  marker coords fixed → markers float off the surface (DRIFT).
- Scaling the model root **before** any marker exists → everything placed
  afterwards is consistent → ZERO drift.

So calibration must be a *gate at upload/early-load time*, not an afterthought
slider applied to an already-annotated model.

## How the viewer currently fits models (Viewer3D.tsx `place()`)
Every .glb is hard-normalized to a 25-unit footprint:
```ts
const scale = 25 / Math.max(size.x, size.y, size.z);
obj.scale.setScalar(scale);   // BEFORE markers sync
```
This means today "true scale" is ALWAYS wrong (a 2m and a 2mm asset both render
at 25 units). The calibration feature *fixes* a real existing limitation — it
does not pile onto a correct system.

## Working pattern (what shipped on feat/model-scale)
1. Add columns to `models` (schema.sql + TS `Model3D`):
   ```sql
   scale_set boolean not null default false,
   scale_x  double precision not null default 1,
   scale_y  double precision not null default 1,
   scale_z  double precision not null default 1,
   ```
2. `Viewer3D` gets new props `modelScale?: {x,y,z}|null` and `showReference?: boolean`.
   In `place()`, apply calibration ON TOP of the auto-fit, to the root only,
   before markers sync:
   ```ts
   const scale = 25 / Math.max(size.x, size.y, size.z);
   const sx = (modelScale?.x ?? 1) * scale;
   const sy = (modelScale?.y ?? 1) * scale;
   const sz = (modelScale?.z ?? 1) * scale;
   obj.scale.set(sx, sy, sz);
   autoFitRef.current = scale;   // remember pure auto-fit for live re-apply
   ```
3. Live re-apply without reload — memoize `autoFitRef` at load so a slider
   drag can recompute `obj.scale = autoFit * newFactor` in a `useEffect([modelScale])`.
   (Do NOT try to back-derive the fit from `obj.scale` at apply time — fragile.)
4. Reference layer (toggle via `showReference`): a `THREE.Group` built once with
   a 1-unit `GridHelper` (the 1m scale) + a 1.7m human silhouette
   (Capsule + Sphere, world-axis aligned, feet at grid level). Visibility
   toggled live via `referenceGroupRef.visible = showReference`.
5. UI: calibration sliders live in the existing model transform drawer
   (double-click model → drawer). Persist through the existing generic
   `saveModelTransform(patch)` — it already does `.update(patch)` + state merge,
   so scale fields flow through with no new DB function. Add a "Reset to
   auto 25u fit" button that writes `scale_set:false, scale_x/y/z:1`.

## Pitfalls (the ones that bit)
- **Don't auto-reproject markers on re-scale.** v1 deliberately does NOT
  reproject existing marker world-coords after a scale change. Rationale:
  keeps the marker-sync code untouched and avoids a class of drift bugs.
  Recommended UX: calibrate BEFORE annotating; if re-scale-after-annotate is
  needed later, reproject each marker by the scale delta (future work).
- **Same-batch patch ordering.** When you add a `useRef` and reference it in
  another edit in the same batch, the LSP will report "Cannot find name 'X'"
  transiently. It resolves once both writes land — do not "fix" it by removing
  the ref. Confirm with a real `npm run build` at the end.
- **Schema claim drift.** Memory/notes may say `scale_x/y/z` already exist on
  `models` — verify against `supabase/schema.sql` before writing code that
  assumes them. In this session they did NOT exist; they were added.
- **Anchor reference to model base, not world origin.** A follow-up change
  anchored the silhouette + 1m grid to the model's world bounding-box
  base-center via an `anchorReference()` call in the load + transform + scale
  effects. Keep the reference GROUP in world space (so the human stays a true
  1.7 units and never inherits the model's scale) and position it each frame
  at the model's base. Don't parent it to the model (it would scale with it).

## Verification (no deploy, safe rollback)
- Branch isolation: `git checkout -b feat/<name>` keeps `main`/prod untouched.
  Rollback = `git checkout main && git branch -D feat/<name>`.
- Build gate: `npm run build` (Next.js + Turbopack) → must show
  "Compiled successfully" + TypeScript pass + all routes generated.
- **Local green ≠ Vercel green.** In this session `npm run build` passed
  locally but the Vercel deploy failed with `npm run build exited with 1`.
  A local pass does NOT prove the deploy will pass (Node version / env vars /
  Vercel build env can differ). After pushing, confirm on the Vercel dashboard
  (Deployments tab) — don't trust the local build as proof of ship.
- **Vercel webhook needs author `kingkymaru@gmail.com`.** Auto-deploy only
  fires if the pushed commit's author is `kingkymaru@gmail.com`. Commit with
  `git -c user.name=maru -c user.email=kingkymaru@gmail.com` before push, or the
  branch push won't trigger a build. (Applies to ALL LunaV Studio Vercel
  pushes, not just scale.)
- Runtime smoke: boot `npm run dev` (background), `curl -s -o /dev/null -w "%{http_code}"`
  `http://localhost:3000/` → 200. Do NOT spawn headless Chrome (MARU's machine
  rule — orphaned procs block his real Chrome). Verify via curl/log, not a browser.
- Kill dev server before committing (`process action=kill`).
