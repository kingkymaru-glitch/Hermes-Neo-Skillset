---
name: cdm-spatial-platform
description: Work on the CDM/OSHCIM Spatial Intelligence app.
category: software-development
---

# CDM Spatial Intelligence Platform

MARU's construction CDM/OSHCIM risk platform — the venture with the enterprise
partner (CDM/OSHCIM Spatial Intelligence). Repo `kingkymaru-glitch/CDM`, local
`~/CDM`, live on Vercel. Vault note: `Projects/CDM/CDM.md`.

**Trigger on:** "CDM", "CDM Spatial", "OSHCIM", "CDM1/CDM2/CDM3/CDM4",
"Principal Designer", "DRM register", "site_risks", "risk matrix", "siting",
or any milestone prompt forwarded from MARU's enterprise partner.

Positioned as a **Spatial Intelligence & Value Protection Platform**, not a
compliance tick-box tool — the UX bar is "billion-ringgit": dark, 3D, legible.

**Backend identity:** its own Supabase project `ennvfuaimplxkzfdxfqd`. Do NOT
confuse with LunaV (`okzmblyboudjffaifixa`) or ARRAS (`lxmmxpxjercmhmiuqeqq`) —
grep `~/CDM/.env.local` when in doubt. Apps may share *code*, never data.

## Domain rule that governs every feature: human-in-the-loop

This is compliance software. **The AI never owns a risk; the Principal Designer
does.** Every risk is a row in `risk_nodes`; only `status='OPEN'` AND
`accepted_by` set is reportable. MARU's requirement is explicit — the blame must
not fall on the model.

```
YOLO detect   -> source=AI_DETECTED, status=DETECTED, ai_confidence
Human detects -> source=MANUAL,      status=OPEN,     accepted_by
Review        -> Accept  => status=OPEN, source=HUMAN_ADJUSTED, accepted_by, reviewed_at
              -> Adjust  => edit geometry/class then Accept (HUMAN_ADJUSTED)
              -> Dismiss => status=REJECTED (never reportable)
Report        -> only status=OPEN AND accepted_by IS NOT NULL
```

Keep `source`/`status`/`accepted_by`/`reviewed_at`/`ai_confidence` on the row.
Legal copy stays generic, advisory-only, never overclaiming (no advertised RBAC
or encryption the code lacks). Details: `references/risk-node-data-model.md`.

## Two-channel risk encoding (do not conflate)

| Property | Channel |
|---|---|
| risk **category** (what kind) | **node colour** — water→blue, geo→brown, congestion→pink, fire→red, structural→purple, traffic→yellow, utilities→grey, env→green, other→cyan (user-pickable) |
| risk **criticality** (how bad) | **ring colour** — OSHCIM RAG from `levelForScore(L×S)`; always drawn, 10 m min radius |

An earlier design put criticality in the node colour; that forces a choice between
"what is it" and "how dangerous is it" and was replaced. Do not regress it.

**The L×S editor is a clickable 5×5 HSE grid, never a slider pair.** Rows =
Likelihood 5 Frequent → 1 Improbable, columns = Severity 1 Marginal → 5
Catastrophic, each cell RAG-coloured with level + score, current cell highlighted.
HSE stakeholders are the audience — match the standard matrix visual language.
OSHCIM is 5×5 (both axes 1–5) even where HSE wall-charts are 5×4.

## Milestone protocol

An external enterprise partner writes long, heavily-constrained "anti-drift"
prompts as if addressing an agent directly. MARU forwards them verbatim.

- **One milestone per version.** Ship it, bump the stamp, commit, push.
- Follow the partner's named stack + file paths literally — that is what keeps
  the partner's mental model in sync with the repo.
- Where a partner instruction is technically wrong (e.g. mandating
  `next/dynamic { ssr:false }` for Cesium, or a library that breaks the Next SSR
  bundle), implement the correct approach and say plainly why you deviated.
  Never implement a known-broken instruction to appear compliant.
- "Discuss first, no code" is a HARD gate for this founder.

## Repo map

```
app/page.tsx                  -> renders <AppShell/> only
components/AppShell.tsx       -> all providers + header + studio overlay (the real shell)
components/WorkspaceGrid.tsx  -> 3-panel grid; columns react to panel collapse
components/SpatialCanvas.tsx  -> Cesium panel chrome (HUD chips, basemap/terrain, legend)
components/CesiumViewer.tsx   -> the globe: risks, overlay feeds, plots, buildings, risk nodes
components/MapToolbox.tsx     -> left-edge vertical flyout tab strip (Node/Surroundings/Building/Plot/Risk)
components/NodePanel.tsx      -> tab 1: place + review risk nodes
components/SurroundingsPanel.tsx -> tab 2: OSM context import + alignment controls
components/LoadBuildingPanel.tsx -> tab 3: model dropdown + place building + move/rotate/scale
components/PlotControls.tsx   -> tab 4: to-scale footprint (W×D m + heading)
components/RiskZonePanel.tsx  -> tab 5: draw Red/Amber/Green areas by hand
components/RiskMatrixGrid.tsx -> the clickable 5×5 OSHCIM HSE matrix
components/NodeEditor.tsx     -> floating draggable node editor (Details | L×S tabs)
components/ModelStudio.tsx    -> 3D Model full-screen upload/orient/scale page
components/ModelStudioViewer.tsx -> standalone Three.js orbit stage
components/AiModelManager.tsx -> Settings > AI Detection > YOLO > Custom model
contexts/{Risk,Layers,PanelLayout,Models,Plot,Buildings,RiskZones,RiskNodes,Surroundings}Context.tsx
app/api/{risks,models,scan,search,plots,buildings,risk-zones,risk-nodes,surroundings,ai-models}/route.ts
scripts/{build_surroundings.py,surroundings_worker.mjs} -> headless Blender context import + worker
lib/{app-version,risk,model-upload,supabase}.ts
```

**Provider nesting matters.** `AppShell` holds them; the three-panel grid sits
INSIDE `RiskProvider > LayersProvider > PlotProvider > BuildingsProvider >
RiskZonesProvider > RiskNodesProvider > PanelLayoutProvider`, with
`ModelsProvider > ModelPlacementProvider` wrapping the whole shell (studio and
globe both read the model catalogue). Moving a provider across the wrong boundary
silently breaks the globe or a studio overlay.

**Nothing is session-only.** All layers persist in Supabase: `risk_nodes`,
`site_buildings`, `site_plots`, `site_risk_zones`, `models`, `context_imports`
(imported surroundings + their alignment offsets), `ai_models` (YOLO registry).
Only `site_risks`
uses PostGIS — newer tables use `numeric` lon/lat + `jsonb`, which is what keeps a
future local-Postgres migration simple. Don't add PostGIS to new tables.

`ModelPlacementContext` now only carries `placeMode`/`spec`/queued pin actions;
**risk nodes moved to `RiskNodesContext`**, and the old `assigned_pin_id` model→node
assignment was REMOVED (buildings are placed independently of nodes).

## Cesium

Cesium is loaded from the CDN at runtime as `window.Cesium` — never statically
imported (that is what breaks the Next bundle). For the entity/viewer trap list —
viewer-init `deps: []` + ref-bag, the clamp-to-ground outline crash, the ignored
`ellipse.outlineWidth`, the NaN guard, the model-orientation trap, and the
snake_case-vs-camelCase NaN trap — load **`cesium-resium-rendering`** before
touching `CesiumViewer`. Also `nextjs-client-heavy-lib-integration` for the
Next-specific CDN load.

App-specific: thick radius rings are sampled **polylines** (~96–128 segments),
never `ellipse.outlineWidth`. Give each visual concern its OWN entity keyed by the
parent id (`rnode-<id>`, `plot-<id>`, `zone-<id>`, `bldg-<id>`) so one bad row
can't abort the render loop. Node interaction: **single-click opens the editor** —
double-click on a small Cesium entity is unreliable.

**Georeferenced glTF imports (Blender/OSM context) have an axis trap.** blosm exports
+X=east / +Z=south, but Cesium's `getAxisCorrectionMatrix(Y-up, Z-forward)` maps
**glTF +Z→East, +X→North**, so an OSM import lands rotated ~90° about its origin —
default `heading_deg = 90` for OSM. And Overpass returns WHOLE ways crossing the
bbox, so stray geometry inflates the bounding sphere (a 1 km import measured
36 km × 19 km) and Cesium then sizes/frames the model wrongly: **clip every mesh to
the bbox before export**. A single uploaded building rotated about its own centre
looks fine, so this only ever shows up on a cityscape. Details + the marker-cube
proof technique in `references/desktop-and-context-pipeline.md`.

## 3D Model studio (upload → control → place)

Ported from the LunaV/ARRAS 3D Digital Twin page (`lunav-studio`). A model is
uploaded, oriented and scaled in a standalone stage BEFORE it is placed — never
uploaded straight onto the map.

**Storage: Supabase Storage by default, R2 is a one-file swap.** Do NOT assume the
LunaV/ARRAS R2 presign path is available — it needs deployed Edge Functions plus
five R2 secrets a fresh app does not have. Use a public Supabase Storage bucket
(`models`) with `storage.objects` policies so uploads work today, and keep EVERY
call site behind `lib/model-upload.ts` so moving to R2 is one file.

Split `.gltf`: it references an external `.bin` (+ textures). Pack them into one
`.glb` client-side before upload, and include `.bin` in the file input's `accept`
or the user cannot select the companion file.

## Conventions

- **Version stamp:** every build bumps `lib/app-version.ts` (`V0.xx`, never
  reused) and it shows in the header. Never ship under an old stamp.
- **MARU pastes SQL himself.** Write ONE clean, idempotent, COMMENT-FREE `.sql` to
  `~/Desktop/apply_cdm_*.sql` and hand him the path. Select-all → paste → Run must
  work with zero editing. Keep the repo copy in `supabase/migrations/`; the
  Desktop copy is the one-shot apply. No `-- ===` banners, no labels.
- **Build gate:** run BOTH `npx tsc --noEmit` and `npx next build` (lint runs
  during `next build`, so tsc alone is not sufficient).
- **Never run `next build` while `npm run dev` is live on the same `.next`** — the
  production build clobbers dev chunks and the globe goes blank with 404s. Kill
  dev, `rm -rf .next`, build, then restart dev.
- Commits must be authored `kingkymaru@gmail.com` or the Vercel auto-deploy webhook
  is gated and the site serves stale code.

## Pitfalls

- **Deno Edge Functions inside a Next TS repo break the pre-build gate.** Any
  `supabase/functions/*/index.ts` (Deno: `Deno.env`, `https://` imports,
  `DOMParser`) fails the root `npx tsc --noEmit` with `Cannot find name 'Deno'`
  and unresolvable https-module errors — looks like app breakage but is just Deno
  files in a Node tsconfig. Exclude that folder or delete stubs you are not
  deploying. Do not let Deno files into the gate.
- **A flyout panel containing a dropdown must NOT sit inside `overflow-y-auto`.**
  The popover is clipped by the scroll container and the list renders invisible —
  the user clicks and sees nothing. Put the scroll on inner lists only.
- **Normalise snake_case columns → camelCase wire shape at exactly ONE boundary**
  (a `normalizeX(row)` helper in the API route). A component reading snake_case
  off a camelCase object computes `Number(undefined)` = NaN vertices, which freezes
  the entire Cesium render ("my node disappeared" = everything died).
- **Never let the hardcoded demo model creep back in.** The original node code
  hardcoded `/models/building.glb` plus a `C.Model.fromGltf` size probe — that is
  what produced "Model.fromGltf is not a function". Nodes carry no model; buildings
  are placed separately.
- **Model size on the globe = the placed building's scale × the GLB's native
  units.** If a model lands the wrong size, fix the scale, not a per-node special case.
- **Deleting a model must detach it from the globe.** Match buildings to models by
  `model_id` and drop the entity when the model row is gone, or a phantom building
  lingers. (Do NOT match node→model by an unpersisted hint field — that bug wiped
  every model off the map when one unrelated model was deleted.)
- **Purging a real-client example from seeded/placeholder data is a three-layer sweep.**
  Examples live in at least three places — `DetailsScreen.tsx` field placeholders,
  `scripts/seed.ts` (project name, client name, risk set, coordinates), and
  `scripts/purge_demo_data.mjs` comments — and leaving any one of them means a client
  name still surfaces in the UI or the DB. When a real client name is used in demos
  (TNB, DBKL, a named developer), grep the ENTIRE codebase for every occurrence before
  declaring it clean; `search_files` with the client's distinctive terms across all
  file types is the reliable check, not a manual scan of the files you remember
  editing.
- **Plot/zone rectangles must be built from centre + W/D + heading, never four
  clicked corners.** Metres→degrees via `mPerLat = 111320`,
  `mPerLon = 111320 * cos(lat)`; that is what makes a 56×67 m plot exactly 56×67 m
  on the ground at any latitude.

## Desktop direction (decided: Option A)

Desktop installer (Tauri/Electron) + cloud DB — heavy work (Blender geometry
import, YOLO inference) belongs on the machine, not serverless. Layer-by-layer
effort table, the B/C alternatives, and the embedded 3D **context pipeline**
(headless Blender + blosm pulls real surrounding OSM geometry as a fifth 'Context'
layer) are in `references/desktop-and-context-pipeline.md`.

## Related skills

`cesium-resium-rendering` + `nextjs-client-heavy-lib-integration` (the globe),
`supabase-backend` (schema/RLS/Storage), `lunav-studio` / `arras-white-label`
(source of the model-studio flow), `founder-workflow` (terse execution style),
`vault-memory-sync`.

## References
- `references/risk-node-data-model.md` — `risk_nodes` schema, review state machine,
  RAG thresholds, category palette, liability/reporting rule.
- `references/desktop-and-context-pipeline.md` — Option A conversion layer-by-layer,
  plus the Blender/blosm context-import shape and its georeferencing gotcha.
