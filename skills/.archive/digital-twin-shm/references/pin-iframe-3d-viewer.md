# Pin + iframe 3D viewer (PREFERRED structural-model pattern)

## Why
Rendering a heavy GLB *inside* Cesium destabilizes the camera frustum culler and
crashes the whole viewer:
`RangeError: Failed to set the 'length' property on 'Array': Invalid array length`
at `View.js updateFrustums` → `Scene.js executeCommandsInViewport`. Observed in
this repo when the "Structural Models" layer was toggled ON with a GLB added via
`viewer.entities.add({ model })`. The user explicitly redirected away from this:
"rather than burdening MARU, place a node that opens a flyout" — i.e. keep heavy
WebGL out of the globe.

## The fix (verified in-session)
A lightweight clickable pin opens the standalone 3D viewer in a sandboxed iframe
modal. The heavy WebGL lives in the iframe, decoupled from Cesium.

### 1. Asset placement
- Copy the standalone HTML viewer (e.g. a Three.js `3d-platform-rev*.html`) into
  `public/models/`.
- Copy any sibling assets it references (images like `logo.png`, local scripts)
  into the SAME `public/models/` folder so relative `src`/`href` resolve.
- Strip spaces from filenames (Cesium/URL gotcha).

### 2. The pin (inside `<Viewer>`, resium `Entity`)
```jsx
function DamGatePin({ onOpen }) {
  const { showStructural } = useEdgeData()
  if (!showStructural) return null
  return (
    <Entity
      id={DAM_GATE_PIN.id}
      position={Cartesian3.fromDegrees(DAM_GATE_PIN.longitude, DAM_GATE_PIN.latitude, DAM_GATE_PIN.height)}
      onClick={onOpen}
      name={DAM_GATE_PIN.name}
    >
      <PointGraphics pixelSize={13} color={Color.fromCssColorString('#22e07a')}
        outlineColor={Color.WHITE} outlineWidth={2}
        scaleByDistance={new NearFarScalar(1.0e3, 1.6, 2.0e7, 0.5)} />
      <LabelGraphics text={DAM_GATE_PIN.name} showBackground
        backgroundColor={Color.fromCssColorString('rgba(11,18,32,0.72)')}
        backgroundPadding={new Cartesian2(8, 5)}
        verticalOrigin={VerticalOrigin.BOTTOM} pixelOffset={new Cartesian2(0, -16)}
        scaleByDistance={new NearFarScalar(1.0e3, 1.2, 2.0e7, 0.6)} />
    </Entity>
  )
}
```
Gate the pin on the existing `showStructural` context flag (toggled from
`MapControlPanel` "Structural Models" row). `onClick={onOpen}` opens the modal.

### 3. The flyout modal (renders OUTSIDE `<Viewer>`)
```jsx
function DamGateViewerModal({ pin, onClose }) {
  if (!pin) return null
  return (
    <div className="modal-scrim" onMouseDown={onClose} role="presentation">
      <div className="modal-card dam-gate-modal" role="dialog" aria-modal="true"
        onMouseDown={(e) => e.stopPropagation()}>
        <header className="modal-head">
          <span className="modal-kicker">STRUCTURAL MODEL · 3D VIEWER</span>
          <h2 className="modal-title">{pin.name}</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">×</button>
        </header>
        <div className="modal-body dam-gate-modal-body">
          <div className="dam-gate-frame-wrap">
            <iframe className="dam-gate-frame" src={pin.html} title={pin.name}
              loading="lazy" allow="fullscreen"
              sandbox="allow-scripts allow-same-origin allow-pointer-lock" />
            <div className="dam-gate-loading">Loading 3D model…</div>
          </div>
        </div>
      </div>
    </div>
  )
}
```
Reuses MARU's existing `.modal-scrim`/`.modal-card`/`.modal-head` classes; add a
`.dam-gate-modal` wide variant (~`min(1080px,94vw)` and a `60vh` iframe) in
`App.css`. The `sandbox` attr keeps the heavy WebGL isolated so it can never
crash the globe.

### 4. Wiring in `DashboardInner`
- `const [damGateOpen, setDamGateOpen] = useState(false)`
- `<DamGatePin onOpen={() => setDamGateOpen(true)} />` inside `<Viewer>`.
- `{damGateOpen && <DamGateViewerModal pin={DAM_GATE_PIN} onClose={() => setDamGateOpen(false)} />}`
  anywhere in the return (outside `<Viewer>` is fine).
- A module-level `DAM_GATE_PIN` constant holds `{ id, name, longitude, latitude,
  height, html: '/models/dam-gate-3d.html', blurb, coords }`.

### 5. Verify (don't claim done without these)
- `npm run lint` (0 errors) + `npm run build` (passes).
- Dev server: `curl -s -o /dev/null -w "%{http_code} %{size_download}" http://localhost:5174/models/<file>.html`
  → `200` with full byte size (a transient `702` is a curl race; re-fetch).
- Toggle the layer ON → pin appears → click → flyout opens, viewer renders,
  globe stays alive.

## When NOT to use this
Only render a GLB *in-globe* (the render-loop-safe `viewer.entities.add` recipe)
if it is lightweight AND the user explicitly insists it live on the globe — and
accept the frustum-crash risk documented above.
