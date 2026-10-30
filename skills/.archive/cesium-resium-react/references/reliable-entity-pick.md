# Reliable Entity Pick (re-click-safe) — Cesium / Resium

## The trap
Resium's `<Viewer onSelectedEntityChange={fn}>` maps Cesium's
`selectedEntityChanged`. That event fires **only when the selected entity
changes**. So this sequence silently breaks:

1. Click S22 dot → `selectedEntityChanged` fires → drawer opens.
2. User dismisses the drawer (e.g. back/collapse button). The selection is
   STILL `s22-ultra` (nothing cleared it).
3. Click S22 dot again → Cesium sees the selection is unchanged → event does
   NOT fire → drawer stays shut.

Symptom the user reports: "clicking the green dot sometimes fails to open the
tab." It's intermittent because it only fails on the *second* click of an
already-selected entity.

## The fix
Attach a `ScreenSpaceEventHandler` `LEFT_CLICK` to the canvas and resolve the
entity yourself on EVERY click via `scene.pick()`. This decouples "what was
clicked" from Cesium's selection state, so re-clicks always register.

### Where to put it
Inside the `useCesium()` child bridge (the same component that already holds the
live `viewer` — see skill G6/G13). Do NOT put it in a bare `useEffect([])` on
`App`; you won't have the engine yet.

### Handler
```jsx
import { ScreenSpaceEventHandler, ScreenSpaceEventType } from 'cesium'

// In the child bridge component:
const cesiumContext = useCesium()
const viewer = cesiumContext?.viewer
useEffect(() => {
  if (!viewer || typeof viewer.isDestroyed !== 'function' || viewer.isDestroyed()) return

  const handler = new ScreenSpaceEventHandler(viewer.scene.canvas)
  handler.setInputAction((click) => {
    const obj = viewer.scene.pick(click.position)
    // obj.id is the Cesium Entity when a primitive/entity was hit; undefined
    // when empty space (or a non-entity primitive) was clicked.
    const entity =
      obj && obj.id && typeof obj.id.id === 'string'
        ? { id: obj.id.id, name: obj.id.name }
        : null
    if (onPickRef && onPickRef.current) onPickRef.current(entity)
  }, ScreenSpaceEventType.LEFT_CLICK)

  return () => {
    if (handler && !handler.isDestroyed()) handler.destroy()
  }
}, [viewer, onPickRef])
```

### Route the pick — by ENTITY ID, to a SIDE (not just "open")
Once you have `picked.id`, branch on *which* entity it is and which **side** of
the screen its panel lives on. This session's settled layout:

- S22 node (`id === 's22-ultra'`) → MAIN command drawer slides in from the **LEFT**.
- An individual sensor (`demo-1/2/3`) → its tab slides in from the **RIGHT**
  (`SensorsPanel` scoped to that sensor via a `selected` prop).
- Empty space (`!picked`) → dismiss every flyout.

```jsx
const S22_ID = 's22-ultra'

const handleMapPick = (picked) => {
  if (!picked) {                       // empty canvas click → close all
    closeAllFlyouts()
    setSelectedAsset(null)
    return
  }
  if (selectedAsset?.id === picked.id) {
    // Same dot re-clicked → toggle the side it drives (THE real fix for the
    // "sometimes won't open" bug — onSelectedEntityChange would no-op here).
    if (picked.id === S22_ID) setDrawerOpen((o) => !o)
    else setSensorsOpen((o) => !o)
    return
  }
  setSelectedAsset({ id: picked.id, name: picked.name })
  if (picked.id === S22_ID) openMain()        // left
  else openRight('sensors')                    // right, scoped to this sensor
}
// Keep the one-time listener pointed at the latest closure:
const handleMapPickRef = useRef(handleMapPick)
handleMapPickRef.current = handleMapPick
```
Pass `handleMapPickRef` into the bridge as a prop so the effect's `onPickRef`
always calls the current `handleMapPick`.

### Single-active side manager (no left/right collision)
If a LEFT panel (main drawer) and a RIGHT panel (sensor/chat/settings) can both
exist, opening one must force-close the other, or they overlap the map. Encode it
as a strict ONE-SIDE model with a single `flyoutSide` state:

```jsx
const [flyoutSide, setFlyoutSide] = useState(null) // 'left' | 'right' | null

function openMain() {                 // LEFT
  setDrawerOpen(true)
  setChatOpen(false); setSensorsOpen(false); setSettingsOpen(false)
  setFlyoutSide('left')
}
function openRight(which) {           // RIGHT
  setDrawerOpen(false)                // ← force-closes LEFT
  setChatOpen(which === 'chat')
  setSensorsOpen(which === 'sensors')
  setSettingsOpen(which === 'settings')
  setFlyoutSide('right')
}
function closeRight(which) {
  if (which === 'chat') setChatOpen(false)
  if (which === 'sensors') setSensorsOpen(false)
  if (which === 'settings') setSettingsOpen(false)
  setFlyoutSide(null)
}
function closeAllFlyouts() {
  setDrawerOpen(false); setChatOpen(false); setSensorsOpen(false); setSettingsOpen(false)
  setFlyoutSide(null)
}
```
Because `openMain()` and `openRight()` are the *only* entry points that set
`drawerOpen`/`sensorsOpen`/etc., and each clears the opposite side, at most one
side is ever visible. Wire every opener/close button through these four functions
(don't call raw `setX(true)` from JSX) so the invariant holds. This also makes
the per-entity routing above safe: an S22 pick (left) and a sensor pick (right)
can never be open together.

### Scoping a panel to the picked sensor
`SensorsPanel` reads the live SHM stream; give it a `selected` prop (the matched
asset object or `null`). When `selected`, filter rows to that sensor's channels,
swap the header title to the sensor name, and show a small "focused sensor" banner;
fall back to a "No live channels for this node." empty state when the stream has
no matching channel. Compute `selectedSensor` in the parent:
```jsx
const selectedSensor = selectedAsset?.id && selectedAsset.id !== S22_ID
  ? assets.find((a) => a.id === selectedAsset.id)
  : null
```
Clicking empty space (`!picked` → `closeAllFlyouts` + `setSelectedAsset(null)`)
exits the focused view.

## Verification
- `npm run lint` (oxlint) — add `onPickRef` to the effect deps or it warns on
  a missing dependency.
- `npm run build` — confirms `ScreenSpaceEventHandler` / `ScreenSpaceEventType`
  imports resolve.
- In-browser: click S22 → opens. Dismiss. Click S22 again → MUST reopen (this
  is the regression the `onSelectedEntityChange` version failed).
