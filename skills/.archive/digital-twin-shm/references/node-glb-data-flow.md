# Node ↔ GLB model data flow (full architecture trace)

This is the end-to-end path of how a user-created map node relates to a 3D model
in M.A.R.U. It documents the separation of concerns: nodes are geospatial bookmarks
(points on the globe), and GLB models are viewed in isolated iframes — never loaded
into Cesium's scene graph.

## 1. Node records: the `model` and `portal_url` fields

Every node (persisted via `src/nodesService.js` → Supabase `nodes` table +
localStorage mirror) carries two URL fields:

| Field       | Purpose                                              | Example                          |
|------------ |----------------------------------------------------- |----------------------------------|
| `model`     | Standalone 3D viewer page (HTML) or raw GLB path     | `/models/dam-gate-3d.html`       |
| `portal_url`| External digital twin dashboard URL                  | `https://external-twin.com`      |

Both are **metadata only** — no Cesium entity reads `node.model` to load geometry
at render time. The `model` field is editable in the NodeEditorModal (line 1861
of `App.jsx`) and written into the node's Obsidian-style markdown `body` for
sync, but it never drives a `ModelGraphics` or `Cesium3DTileset`.

## 2. Node rendering on the globe: MapNodePins (line 1679–1724)

User-created nodes (from `useEdgeData().nodes`) are rendered as lightweight
Cesium entities — a colored dot + text label ONLY:

```
<Entity position={Cartesian3.fromDegrees(lon, lat, height)}>
  <PointGraphics pixelSize={11} color='#5ad1ff' />   ← cyan dot
  <LabelGraphics text={nodeName} />                    ← name label
</Entity>
```

Gated by `showNodes` from EdgeDataContext. Toggled from MapControlPanel.
Clicking a node opens the NodeEditorModal (`onOpen(n)`), where the `model` field
is displayed as editable text.

## 3. Hardcoded infrastructure: DamGatePin (line 1637–1672)

The Temenggor Dam Gate is a special case — it has its own dedicated component
with a standalone 3D viewer. The pin is a `DAM_GATE_PIN` module-level constant
with hardcoded lat/lon/height and an `html` field pointing to
`/models/dam-gate-3d.html`.

Rendered identically to a MapNodePin (dot + label), but:
- Gated by `showStructural` (NOT `showNodes`)
- Color is `#22e07a` (green) vs `#5ad1ff` (cyan) for user nodes
- Clicking opens `DamGateViewerModal` (not NodeEditorModal)

The modal (`DamGateViewerModal`, line 1929–1967) loads the standalone viewer in a
sandboxed iframe:

```html
<iframe src={pin.html}
  sandbox="allow-scripts allow-same-origin allow-pointer-lock" />
```

This is the **only GLB rendering path in the current codebase** — the model lives
in its own isolated WebGL context, completely decoupled from Cesium's renderer.

## 4. Structural Models layer toggle mechanism

In `layerRegistry.js` (line 131–141), `structural_models` is declared as:

```js
{ id: 'structural_models', group: 'overlay', kind: 'entity', provider: 'structural' }
```

Because `kind: 'entity'`, the `LayerManager` (line 101: `if (layer.kind === 'entity') return false`)
**skips it entirely** — no imagery provider or tile provider is built. Instead,
the `showStructural` flag from `EdgeDataContext` directly gates the `DamGatePin`
component:

```jsx
// DamGatePin (line 1639)
if (!showStructural) return null
```

MapControlPanel wires the toggle (line 59):
```jsx
if (l.id === 'structural_models') return showStructural
```

The `structural` provider in `governanceRegistry.js` (line 104–114) sets a
budget cap (200 daily / 60 session) but currently only governs entity count —
no API calls are involved since GLB models are served as static files from
`public/models/`.

## 5. Why GLBs are never loaded in-globe

Documented at line 48–53 of `App.jsx`:

> "Instead of loading a heavy GLB *inside* Cesium (which can crash the renderer —
> tracked in updateFrustums, see RangeError reports), we place a lightweight
> clickable marker. Clicking it opens the standalone interactive 3D model viewer
> in an isolated modal — the heavy WebGL lives in that iframe, so MARU's globe
> never has to render it."

The crash signature: `RangeError: Failed to set the 'length' property on 'Array':
Invalid array length` in Cesium's `View.js updateFrustums` → `Scene.js
executeCommandsInViewport`. Heavy GLB geometry destabilizes the camera frustum
culler.

## 6. AssetEntities (line 1975–2053) — separate from nodes

`AssetEntities` renders a different data source: the seeded/managed asset list
(`assets` array) + mock sensors + live S22 GPS. These are ALL rendered as
`PointGraphics` dots — no model loading. Rendered inside `<Viewer>` after
`<MapNodePins>` and `<DamGatePin>`.

## 7. Quick reference: which entity renders what

| Component          | Data source          | Gate flag         | Renders model? |
|--------------------|----------------------|--------------------|----------------|
| `MapNodePins`      | `useEdgeData().nodes`| `showNodes`        | No (opens editor) |
| `DamGatePin`       | `DAM_GATE_PIN` const | `showStructural`   | No (opens iframe modal) |
| `AssetEntities`    | `assets` array       | always             | No (dots only) |
| S22 Ultra entity   | `useEdgeData().geo`  | `mode === 'android'`| No (green dot) |
| Mock sensors       | `mockSensors` array  | always             | No (colored dots) |

## 8. What would change for true in-globe GLB

If a lightweight GLB MUST live on the globe (user insists, model is small):
- Use the render-loop-safe imperative pattern in the main SKILL.md ("In-globe GLB recipe")
- Use `viewer.entities.add({ model: { uri, scale, minimumPixelSize, ... } })` after viewer confirmed
- Key the effect ONLY on `[viewer, showStructural]` — never track loaded IDs in state
- Accept the frustum-crash risk documented above
