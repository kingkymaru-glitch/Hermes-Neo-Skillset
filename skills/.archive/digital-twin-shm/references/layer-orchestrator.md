# Layer Orchestrator Pattern — geospatial overlays (MaRU / my-digital-twin)

Canonical location: `src/layers/`. Introduced 2026-07-18 to satisfy a user brief
for an OpenWeather map layer with a **scalable, config-driven** architecture (add
future layers = config change, not a map-component rewrite).

## Why this structure
The Cesium `<Viewer>` must NEVER learn about individual layers. It only owns the
live viewer ref. All layer *behaviour* lives in `LayerManager.js`; all layer
*declarations* live in `layerRegistry.js`. The React hook is glue only. This is
the "Layer Orchestrator" pattern the user specified.

## File triad

### 1) `layerRegistry.js` — DECLARATIVE CONFIG (the only file you edit to add a layer)
```js
export const LAYER_REGISTRY = [
  { id:'osm', group:'base', label:'Streets (OSM)',
    type:'url-template', url:'https://tile.openstreetmap.org/{z}/{x}/{y}.png', default:true },
  { id:'owm-clouds', group:'overlay', label:'Weather · Clouds',
    type:'url-template', requiresKey:'openweather',
    url:'https://tile.openweathermap.org/map/clouds_new/{z}/{x}/{y}.png?appid={key}',
    alpha:0.7, cache:{ttlMin:30}, lazy:true },
  { id:'ships', group:'overlay', label:'Ships (AIS)', enabled:false, badge:'soon' },
]
export const API_KEYS = { openweather: import.meta.env.VITE_OPENWEATHER_API_KEY || '' }
```
Field reference: `id` unique key; `group:'base'` ⇒ mutually-exclusive radio-select,
`group:'overlay'` ⇒ independent additive toggle; `requiresKey` ⇒ layer ships INERT
(disabled in UI, never activated) when the key is missing; `alpha` ⇒ overlay opacity;
`cache:{ttlMin}` ⇒ metadata localStorage TTL; `lazy:true` ⇒ provider built only on
activate; `enabled:false` + `badge` ⇒ visible-but-disabled future placeholder.
Helpers exported: `baseLayers()`, `overlayLayers()`, `getLayer(id)`, `isLayerAvailable(layer)`.

### 2) `LayerManager.js` — framework-agnostic CORE (plain class, no React/Cesium-UI)
Responsibilities + Cesium specifics:
- **State**: `Map<id, { layer: ImageryLayer, provider }>` + `activeBaseId`.
- **Inject (activate)**: lazily `new UrlTemplateImageryProvider({ url })` (key
  substituted into `{key}`), wrap in `new ImageryLayer(provider, { alpha, show:true })`,
  then `viewer.imageryLayers.add(imagery, index)` where `index = 0` for base (bottom
  of stack) and `viewer.imageryLayers.length` for overlays (near top).
- **Base exclusivity**: `setBaseExclusive(id)` removes any other `group:'base'` layer
  on activate — radio behaviour.
- **Deactivate**: `viewer.imageryLayers.remove(handle.layer)` + delete from map.
- **Cache**: `localStorage['maru.layer.<id>'] = { ts, ok }`, 30-min TTL checked on
  activate. We cache the *probe result*, NOT tiles — the browser + Cesium HTTP-cache
  the tile bytes. `readCache`/`writeCache` are try/catch-guarded (private mode safe).
- **Graceful degradation**: missing key or failed provider ⇒ `console.warn` + return
  `false`; the base map is NEVER affected (no throw into the viewer).
- `toggle(id)` flips; `destroy()` tears every layer down (call from the hook cleanup).

### 3) `useLayerManager.js` — React BRIDGE (glue only, no behaviour)
```js
const cesiumContext = useCesium()
const viewer = cesiumContext?.viewer
useEffect(() => {
  if (!viewer) return
  managerRef.current = new LayerManager(viewer)
  // NOTE: do NOT call activate(DEFAULT_BASE_ID) here. The <Viewer baseLayer> prop
  // already paints the default base on first paint (it's load-bearing — without it
  // the dummy-Ion-token globe flashes a black void). The LayerManager constructor
  // CAPTURES that prop handle as the default base, so re-activating it would stack
  // a DUPLICATE layer and desync base-exclusivity. (See G18 in the cesium skill.)
  return () => managerRef.current?.destroy()
}, [viewer])
```
Exposes `{ ready, layers, baseLayers, overlayLayers, activeIds, activeBaseId,
isActive, isAvailable, toggle }`. A `forceRender` counter re-renders consumers when
active-state mutates. Mount this hook INSIDE the `<Viewer>` tree (the only place
`useCesium()` holds the real engine) — never in `App`'s body (it's outside the engine).

### Constructor capture (the G18 fix — DO NOT skip)
`LayerManager` MUST register the `<Viewer baseLayer>` prop's handle in its
constructor, otherwise a later `activate(default)` would stack a duplicate layer
and base-exclusivity would desync (UI says Satellite, globe still shows OSM):
```js
constructor(viewer) {
  this.viewer = viewer
  this.active = new Map()
  this.activeBaseId = DEFAULT_BASE_ID || null
  const first = viewer.imageryLayers.get(0)   // the <Viewer baseLayer> prop's layer
  if (DEFAULT_BASE_ID && first) this.active.set(DEFAULT_BASE_ID, { layer: first, provider: null })
}
```

## OpenWeather wiring
- Tile endpoint is standard XYZ: `https://tile.openweathermap.org/map/<layer>_new/{z}/{x}/{y}.png?appid={key}`.
  Layers used: `clouds_new`, `precipitation_new`, `temp_new`. `temp_new` lighter alpha (0.6).
- Key via `VITE_OPENWEATHER_API_KEY` (env, git-ignored). Absent ⇒ rows render disabled
  with tooltip; manager degrades gracefully. Do NOT hardcode or crash on missing key.
- Drop the key into `.env` (copy from `.env.example`) to activate weather rows live.

## Sharp catches (this session)
- **Cesium substitutes tile coords from LITERAL template tokens.** `UrlTemplateImageryProvider`
  fills `{z}/{x}/{y}` AND Esri's `{z}/{y}/{x}` straight from the URL string — NO axis-order
  branching / `scheme:'zyx'` flag needed. An earlier `scheme` field was dead config; removed.
  Don't re-add per-provider axis logic.
- **Lazy = constructed only inside `activate()`.** Nothing loads at boot; the registry is
  inert data until a user flips a toggle. This is the "lazy loading" mandate.
- **Base vs overlay index matters.** Base at index 0, overlays appended — otherwise an
  overlay can land UNDER the base and be invisible.
- **Match existing import style**: `ImageryLayer`, `UrlTemplateImageryProvider` from `'cesium'`;
  `useCesium` from `'resium'`. Same as the rest of `App.jsx`.

## Scalability proof
Adding Ships / Flight paths later = append a registry object (or, if a novel provider
type appears, one `type` branch in `LayerManager.buildProvider`). The `<Viewer>`, the
hook, and all UI stay untouched. The `enabled:false` + `badge:'soon'` rows already
demonstrate this visually.

## Verification
`npm run lint` (oxlint 0/0) + `npm run build` green, `rm -rf dist`. The service layer
is wiring-complete but inert until the Control Panel UI mounts the hook (next step).
