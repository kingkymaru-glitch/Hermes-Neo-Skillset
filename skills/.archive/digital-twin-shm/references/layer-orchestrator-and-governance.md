# Layer Orchestrator, Governance Registry & Secret Handling (MARU / my-digital-twin)

How to add a new geospatial data layer or governed API provider WITHOUT rewriting
the map component. The repo is deliberately declarative — you edit registries, not
the `<Viewer>`. Follow the real file shapes below; specs from the user are often
written against an idealized structure and must be adapted (the "sharp catch").

## The declarative registries (edit these, never the Viewer)

- `src/layers/layerRegistry.js` — flat `LAYER_REGISTRY` array + selectors
  `baseLayers()` / `overlayLayers()` / `getLayer(id)` / `isLayerAvailable(layer)`.
  API keys resolved lazily: `export const API_KEYS = { openweather: import.meta.env.VITE_..._API_KEY || '' }`.
  Row fields: `id, group('base'|'overlay'), label, type('url-template'), url,
  requiresKey, alpha, cache{ttlMin}, lazy, default, badge, enabled`.
  A missing `requiresKey` key ⇒ layer ships INERT (visible but disabled), never crashes.
- `src/governance/governanceRegistry.js` — `GOVERNANCE_POLICY.providers[]`, each
  `{ id, label, desc, dailyLimit, sessionLimit, warnAt, enabled }`. Modes OFF/NORMAL/OPEN.
  Adding a provider auto-surfaces a Budget Pill in Settings → System Governance.
- `src/MapControlPanel.jsx` (NOTE: at `src/`, NOT `src/components/`) — the
  glassmorphic Layer Orchestrator UI; toggle rows live here, mounted in the Viewer tree.
- There is NO `src/services/` by default — create it if a spec calls for an egress driver.
- `vite.config.js` `server.proxy` — the 8th, keyless-only touchpoint. For APIs
  without a CORS header (e-Solat, OSM Overpass) the browser MUST fetch the
  proxied same-origin path (`/api-xxx`), never the raw `https://`. Open-Meteo is
  CORS-clean but proxy anyway to match the `/api-vessel` pattern. Full recipe +
  verified free-API bank: **`references/free-keyless-ambient-overlay.md`**.

## CRITICAL: tile-layers vs entity-layers (don't shoehorn)

`LayerManager.js` builds **imagery tile providers** (`UrlTemplateImageryProvider`) only.
Anything that is a **moving Cesium entity** (live vessels, aircraft, tracked assets —
points/vectors with position/heading) is a DIFFERENT render path and must NOT be
registered as a tile overlay. Pattern for entity layers:
- Mark the registry row `kind: 'entity'` so `LayerManager` skips it.
- Drive visibility with a React context flag (e.g. `showMaritimeLayer`) toggled from
  MapControlPanel.
- Render via a dedicated component (e.g. `<MaritimeEntities>`) placed in the Viewer
  tree next to `<AssetEntities>` (App.jsx, inside `<Viewer>`), so `useCesium()` resolves.

## Governance gate API (real two-call pattern)

Call sites use `useGovernance()`. It is NOT a single throttling `gov.ask()` — it's:
```js
const verdict = gov.ask('provider_id')   // { allow, reason, remaining, state }
if (verdict.allow) { const data = await fetch(...); gov.record('provider_id') }
else { return [] }  // rejected/throttled → return SAFE EMPTY payload, never throw
```
The gate FAILS-OPEN if the policy/counter layer is broken (see governanceService.js).
Wrap every outbound API call in this hook. Return empty array on reject to keep the
canvas stable.

## Secret handling (VITE_ env keys)

- `.env` is git-ignored (verify: `git check-ignore .env` must echo `.env`).
- Client-read keys MUST be prefixed `VITE_` (e.g. `VITE_VESSEL_API_KEY`) — Vite only
  exposes `VITE_*` to `import.meta.env`.
- Write the real key to `.env`; add a `your_..._here` placeholder + comment to
  `.env.example` so the layer degrades gracefully (toggle disabled) when unset.
- NEVER echo the raw key back into chat or commit it. Confirm safety with
  `git check-ignore` rather than claiming it.

## Click-to-HUD on entities

Reuse the existing always-on pick handler in `TelemetryTracker` (App.jsx ~L924):
`ScreenSpaceEventHandler` + `viewer.scene.pick(click.position)` forwards
`(entity, screenPos)` through `onPickRef`. For a per-entity micro HUD pill, branch in
`handleMapPick` on the picked entity id (same pattern as `s22-ultra` / sensor dots).

## Verified worked example — Live Maritime Fleet (entity layer)

This session shipped a live vessel layer end-to-end. The FULL, copy-with-
modifications implementation — egress driver, Cesium entity component + COG
heading vector + click HUD, App.jsx mount, and `.vessel-hud` CSS — lives in
**`references/maritime-fleet-implementation.md`**. Read that file for the
concrete code. The registry/context/toggle CONTRACT (shape-independent half):

1. `layerRegistry.js` — row (note `kind:'entity'` so LayerManager skips it, and
   `provider` names the governance id DISTINCT from the key id):
   ```js
   {
     id: 'maritime_live',
     group: 'overlay',
     kind: 'entity',
     label: 'Live Maritime Fleet',
     category: 'DATA OVERLAY',
     provider: 'vesselapi_maritime',   // governance id, not the key id
     requiresKey: 'vesselapi',
   }
   ```
   Add `vesselapi: import.meta.env.VITE_VESSEL_API_KEY || ''` to `API_KEYS`.

2. `governanceRegistry.js` — provider with budget caps (tune to the provider's
   real quota; these protect a tight dev allowance):
   ```js
   { id: 'vesselapi_maritime', label: 'VesselAPI Maritime', desc: 'Live vessel positions & course',
     dailyLimit: 100, sessionLimit: 5, warnAt: 0.8, enabled: true }
   ```

3. `EdgeDataContext.jsx` — the entity on/off flag lives in shared context (NOT
   the LayerManager, which is tile-only):
   ```js
   const [showMaritimeLayer, setShowMaritimeLayer] = useState(false)
   // ...expose both in the context value
   ```

4. `MapControlPanel.jsx` — branch the row so entity layers flip the context flag
   while tile layers still call `toggle(id)`:
   ```js
   const { showMaritimeLayer, setShowMaritimeLayer } = useEdgeData()
   const isEntityLayer = (l) => l.kind === 'entity'
   const isLayerOn = (l) => (isEntityLayer(l) ? showMaritimeLayer : isActive(l.id))
   // in the row render: const active = isLayerOn(l)
   // in onToggle: if (isEntityLayer(l)) setShowMaritimeLayer((on) => !on); else toggle(l.id)
   ```
   And map `requiresKey==='vesselapi'` → governance id `'vesselapi_maritime'` in
   `governanceIdForLayer`, plus a `disabledReason` of
   `'Add VITE_VESSEL_API_KEY to enable'`. The toggle STILL runs `gov.ask(govId)`
   / `gov.record(govId)` + the circuit-breaker check first.

5. `.env` / `.env.example` — store the real key in `.env` (git-ignored); add a
   `VITE_VESSEL_API_KEY=your_vessel_api_key_here` placeholder + comment.

The row renders with the existing `mcp-row` / `mcp-switch` glassmorphic switch —
no new CSS needed. When the key is absent the row is disabled-with-tooltip (same
pattern as the weather rows). Verified green (oxlint 0/0, vite build OK).

## Premise check — "the payload above" may never have arrived

When the user says "use the endpoint/JSON I pasted above" but NO such paste
exists in the transcript (clarify only captured intent, not content), do NOT
fabricate a fetch adapter or guess field names (lat vs latitude, cog vs heading,
sog vs speed). Build the shape-independent stages first (registry rows,
governance provider, context flag, glassmorphic toggle — all of which work
without the endpoint), then STOP at the fetch/entity-render stage and ask the
user to paste the exact endpoint URL + sample JSON. This is the maritime-layer
split the user approved: Stages 1-2 (registries + toggle) commit-ready without
the API contract; Stages 3-4 (egress driver + Cesium entities/HUD) wait for the
real schema. Flag the missing payload explicitly ("sharp catch: the bbox/JSON
block didn't actually arrive") rather than silently guessing.

### Resolution — a config SPEC (not a JSON sample) can still unblock you
This session the user later PASTED a VesselAPI *config spec* (endpoint + Bearer
auth + field mapping) — it was a spec, not a literal sample JSON row. The fix is
a TOLERANT mapper (`normalizeVessel` reads canonical names AND alternatives:
`latitude`/`lat`, `cog`/`course`/`heading`, `sog`/`speed`). That satisfies the
premise-check's real intent (don't hardcode a guessed single field name) without
a literal JSON sample. If the real edition uses a quirky spelling, add ONE line to
the `??` chain — no other change needed. Lesson: you do NOT need a sample JSON row
to build safely; a tolerant mapper + exposed `??` chain is sufficient.

## Workflow reminders

- Build ONE stage per turn; hold all edits for a single atomic commit at the end
  (user commits after visual review + green Cmd+B / `npm run build`).
- Run `npm run lint` (oxlint, 0/0) after each chunk; `npm run build` + `rm -rf dist`
  before the final commit. No dist artifacts in the tree.
- When the external API endpoint/response shape is unknown, do the shape-independent
  stages first (registries, toggle) and ASK for the endpoint URL + sample JSON before
  writing the fetch adapter — don't guess field names (lat/lon/cog/sog/name/dest).

## Shifu bridge specific pitfalls
- The S22 Ultra publisher is NOT in this workspace; bridge work in `my-digital-twin`
  assumes the `/state` JSON tick already arrives via DeviceShifu HTTP.
- MARU never consumes MQTT/ROS directly — only the uniform HTTP instruction shape
  should be referenced from frontend code or docs.
- Derived anchor values: if you recalculate `AK`, also update any GNSS fallback paths
  that still use the literal S22 anchor.
- Wait for the debounced data toggle before claiming the HUD/telemetry readout is
  - Wait for the debounced data toggle before claiming the HUD/telemetry readout is wrong; same `showShifuLayer` gate drives both the entity render and the preview.
  - Verify with `npm run lint` and `npm run build`; hold purely visual changes until the debounced layer/HUD behavior is shown.

  ## MARU edit-surface discipline

  Vault/project notes often still carry TODO markers while the repo already contains committed bridge code. Before adding more parts: read the existing workspace tree, then let `npm run lint` + `npm run build` verify whether the planned pieces are actually wired. Treat Android-app gaps as out-of-scope for this repo unless the user explicitly redirects there.

  ## HUD / sidebar interaction anti-patterns
  - Observe existing sibling panels when authoring a new one; align placement, padding, and close affordance BEFORE claiming done.
  - Don't add entity-pick semantics to a preview panel that only renders text.
  - Don't assume the first successful edit is a working user flow; map through viewport and close behavior too.
  debounced layer/HUD behavior is shown.
