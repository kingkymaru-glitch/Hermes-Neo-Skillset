# New map node: prefill from current viewport center

When the user creates a map node, seed Lat/Lon with the coordinate they are
currently looking at (the viewport center), but keep the fields editable so
they can nudge them. Verified working in `NodeEditorModal` + the New Node button.

## Why center, not camera position
`viewer.camera.position` is the camera's arbitrary point in space — with tilt it
is NOT the point under the crosshair. `pickEllipsoid` at the canvas center gives
the actual geo point the user is focused on. This is what "where I'm looking"
means to a human.

## The helper (lives in DashboardInner, alongside `screenToLonLat`)

```js
// Reverse-geocode a canvas screen position into lon/lat via the live camera.
function screenToLonLat(screenPos) {
  const viewer = viewerRef.current
  if (!viewer || !screenPos) return null
  const cartesian = viewer.camera.pickEllipsoid(
    screenPos,
    viewer.scene.globe.ellipsoid,
  )
  if (!cartesian) return null
  const carto = Cartographic.fromCartesian(cartesian)
  return {
    lon: +CesiumMath.toDegrees(carto.longitude).toFixed(5),
    lat: +CesiumMath.toDegrees(carto.latitude).toFixed(5),
  }
}

// Lon/lat at the CENTER of the viewport (what the user is looking at).
// null if engine not ready or the center ray misses the globe (looking at space).
function cameraFocusLonLat() {
  const viewer = viewerRef.current
  if (!viewer || !viewer.scene || !viewer.scene.canvas) return null
  const canvas = viewer.scene.canvas
  const center = new Cartesian2(
    Math.floor(canvas.clientWidth / 2),
    Math.floor(canvas.clientHeight / 2),
  )
  return screenToLonLat(center)
}
```

Note `Cartesian2` must be imported from `resium`/Cesium (already in MARU's import
list). `clientWidth/clientHeight` (CSS pixels) are correct here — `pickEllipsoid`
expects pixel coords relative to the canvas.

## Wire the New Node button

```jsx
onClick={() => {
  const focus = cameraFocusLonLat()
  setNodeEditor({
    draft: true,
    lat: focus ? focus.lat : '',
    lon: focus ? focus.lon : '',
    _focusedAt: focus ? Date.now() : 0,
  })
}}
```

Pass the helper into the modal so it can re-grab later:

```jsx
<NodeEditorModal
  node={nodeEditor}
  ...
  getFocusCoord={cameraFocusLonLat}
/>
```

## Modal side

```jsx
function NodeEditorModal({ node, ..., getFocusCoord }) {
  const isNew = !node || node.draft || !node.id
  const [form, setForm] = useState(() => ({
    id: node?.id || '', name: node?.name || '', type: node?.type || 'structural',
    lat: node?.lat ?? '', lon: node?.lon ?? '', height: node?.height ?? '',
    model: node?.model || '', status: node?.status || 'draft',
    marks: firstSection(node?.body, 'Inspection Marks'),
    findings: firstSection(node?.body, 'Findings'),
    report: firstSection(node?.body, 'Reports'),
  }))
  function grabFocus() {
    const f = getFocusCoord && getFocusCoord()
    if (!f) return
    setForm((fm) => ({ ...fm, lat: f.lat, lon: f.lon }))
  }
  // ...
}
```

Render the re-grab control ONLY for new nodes, right after the Longitude field:

```jsx
{isNew && (
  <div className="node-field node-field-wide node-focus-row">
    <button type="button" className="node-focus-btn" onClick={grabFocus}>
      ◎ Use map center
    </button>
    <span className="node-focus-hint">
      Coordinates prefilled from where you're looking — edit freely, or re-grab the current focus.
    </span>
  </div>
)}
```

CSS: `.node-focus-row` (flex, gap, wrap), `.node-focus-btn` (cyan pill),
`.node-focus-hint` (dim, flex:1). Match the existing `.node-hint` styling family.

## Verification
1. `npm run lint` → 0 errors (watch for a `no-unused-vars` warning on any helper
   you added but didn't wire, e.g. a renamed `refreshFocusCoord` you abandoned —
   delete dead helpers, they add noise).
2. `npm run build` → passes.
3. Browser: pan to a spot → New Node → Lat/Lon match the map center → edit them
   → Save. Then test "◎ Use map center" after panning with the modal open.

## Alternative (not used)
A click-to-place pin (grab the exact mouse click via the existing
`onPickRef`/LEFT_CLICK handler's `click.position` → `screenToLonLat`) is also
possible if the user prefers clicking the precise spot over using the viewport
center. Center is usually what "where I'm focusing" means; offer click-placement
if they ask.
