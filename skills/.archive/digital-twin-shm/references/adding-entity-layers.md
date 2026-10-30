# Adding free/keyless ENTITY layers to MARU (Cesium digital twin)

MARU = Vite + React + Cesium/resium SPA (field-engineer SHM). Layers are either
`url-template` (imagery tiles) or `kind:'entity'` (Cesium entities via a React
component + a context flag). This note covers the **entity** kind, used for
ambient data overlays (weather, air quality, marine waves, OSM POI).

## The 7 touchpoints (mirror `src/components/SituationalEntities.jsx`)
Add all of these for every new overlay:

1. **egressDrivers.js** — `export async function fetchXxx(gov)`:
   - `const v = gov?.ask?.(PROVIDER)`; if `!v?.allow` return `{…, error:null}` early.
   - fetch through the Vite proxy path (never the raw upstream from the browser).
   - map to plain entity objects; `gov?.record?.(PROVIDER)` on success.
   - on failure return `{…, error:{code,message}}` — **NEVER fabricate data**.
2. **governanceRegistry.js** — add provider `{ id, label, desc, dailyLimit, sessionLimit, warnAt, enabled:true }` (no key needed for keyless).
3. **layerRegistry.js** — entity row `{ id, group:'overlay', kind:'entity', label, category:'DATA OVERLAY', provider, requiresKey:null }`.
4. **EdgeDataContext.jsx** — `const [showX,setShowX]=useState(false)` + `const [xCount,setXCount]=useState(0)` near the other overlay flags; export both in the context-value object.
5. **components/XxxLayer.jsx** — new file: `useCesium()` (viewer), `useEdgeData()` (flag + `setXCount`), `if (!showX) return null` self-gate, poll egress on interval, render `Entity` pins, render a click-to-open glass HUD (`.xxx-hud` / `.xxx-hud-error`). Copy `SituationalEntities.jsx` as the scaffold.
6. **MapControlPanel.jsx** — add `showX` to the `useEdgeData()` destructure + to `ENTITY_META` (count + noun fn); handle in `isLayerOn` and in the `if (isEntityLayer(l))` toggle block.
7. **App.jsx** — `import XxxLayer from './components/XxxLayer'`; mount `<XxxLayer />` inside the Viewer tree (after `<SituationalEntities />`).

Plus:
- **vite.config.js** — add a `/api-xxx` proxy (`target` = upstream host, `rewrite` strips the prefix). This is the CORS dodge — route browser fetches through the same-origin dev server so no preflight hits the client.
- **App.css** — add `.xxx-hud` + `.xxx-hud-error` styles (mirror `.meteo-hud`).

## Verification gate (web == Xcode Cmd+B)
`npm run lint` (0 errors) + `npm run build` (modules transform, no errors).
Cannot open a browser from here — user does the visual review; assistant must NOT commit.

## Pitfalls
- **HONOR EXCLUSIONS.** The user explicitly cancelled the e-Solat Prayer layer
  ("i dont think e solat should be on MARU") across two sessions. Do NOT
  build/keep it even as part of a "each free API" batch. When the user excludes
  a feature, drop it from the plan and never re-add it in a later turn.
- Overpass (OSM) can 406 / rate-limit from some networks — always proxy it and
  degrade gracefully (show nothing + red OFFLINE banner); never simulate POIs.
- Open-Meteo is CORS-clean but still route via proxy to match the pattern and
  skip preflight entirely.
- Before relying on a shared helper (e.g. `toNum` in egressDrivers), grep it
  exists — a missing ReferenceError won't fail the build, only runtime.
- Prefer `patch()` over sed/raw edits for source; keep changes scoped per file.

## GLB / static-model entity rows — extra pitfalls (from Dam Gate work)
When the new entity layer is a static GLB model (not a polled data feed), the
generic 7-touchpoint recipe above needs these adjustments:

- **Do NOT give the row a live-count badge.** The generic `MapControlPanel`
  entity-row code originally rendered a "vessels" count badge for ANY entity
  row that was ON — copy-pasted from the maritime row. For a GLB row there is
  no count, and referencing an undefined `vesselCount`/`setVesselProvider`
  (from a different branch) will throw. Fix: show the live-count badge ONLY
  for `l.id === 'situational_ctx'`; every other entity row (incl. GLB) renders
  the stock `<span className="mcp-switch">` switch. Guard the badge ternary so
  it can never fall through to a non-existent count variable.
- **Wiring for a GLB toggle** (instead of `components/XxxLayer.jsx` polling):
  - `EdgeDataContext.jsx`: `const [showStructural, setShowStructural] = useState(false)` + export both in the context value.
  - `layerRegistry.js`: entity row `{ id:'structural_models', group:'overlay', kind:'entity', label:'Structural Models', category:'STRUCTURAL', provider:'structural', requiresKey:null }`.
  - `governanceRegistry.js`: provider `{ id:'structural', label, desc, dailyLimit:200, sessionLimit:60, warnAt:0.8, enabled:true }`.
  - `MapControlPanel.jsx`: destructure `showStructural, setShowStructural`; add to `isLayerOn` (`if (l.id==='structural_models') return showStructural`); in the toggle, `else if (l.id==='structural_models') setShowStructural(on=>!on)`.
  - `App.jsx`: a `StructuralModels()` component using `useCesium()` + `useEdgeData()`, with the add/remove-only effect from the SKILL.md "GLB loading discipline" (NO loaded/failed-ID state — that causes the render-loop bug).
- **Verify the asset serves** (filename-space gotcha): see SKILL.md Desktop
  assets rule. A `Dam Gate.glb` (space) silently fails; rename to `dam-gate.glb`.
