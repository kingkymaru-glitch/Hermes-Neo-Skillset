# Scroll-Driven Globe Stage — STEADY (no flicker, no blink)

Canonical LUNAV Labs pattern. A fixed Cesium `<Viewer>` behind a scrolling
foreground doc, camera eased (dolly-out) by scroll progress AND spinning on its
axis continuously — with NO flicker during scroll and NO blink on section change.

## Two bugs this fixes (and their root causes)
- **Flicker (per-frame judder):** naive version ran its own `requestAnimationFrame`
  loop calling `camera.setView` every frame, which collided with Cesium's internal
  render loop (also touches the camera each frame). Two writers, out of sync.
- **Blink on section change:** `<GlobeStage progress={progress}/>` was NOT memoized;
  every scroll `setProgress` re-rendered the parent → re-rendered GlobeStage →
  resium tore down + rebuilt the WebGL `<Viewer>` → canvas flashed at each section.

## The fix (3 parts)
1. **Drive the camera from Cesium's clock, not a custom RAF.**
   `viewer.clock.onTick.addEventListener(cb)` + `viewer.clock.shouldAnimate = true`.
   The clock is GPU-synced, so the single `setView` per tick lands with the draw.
2. **Do BOTH dolly-out + spin inside the one tick** — no `flyTo` (it animates and
   fights the per-tick setView).
3. **Decouple the globe from React re-renders:** `memo(GlobeStage)` + pass scroll
   progress via a `ref` (not a prop), throttled scroll handler.

## Canonical GlobeStage.jsx (steady)

```jsx
import { memo, useEffect, useRef } from 'react'
import { Viewer, Entity } from 'resium'
import { Ion, ImageryLayer, UrlTemplateImageryProvider, Cartesian3, Color,
  Math as CesiumMath, VerticalOrigin, Cartesian2, NearFarScalar } from 'cesium'

Ion.defaultAccessToken = import.meta.env.VITE_CESIUM_ION_TOKEN || 'local-dev-no-ion'

function approach(cur, target, k = 0.05) { return cur + (target - cur) * k }

function GlobeStage({ progressRef }) {
  const viewerRef = useRef(null)
  const camRef = useRef({ lat: 8, height: 600000, heading: 0, pitch: -55 })

  const baseLayer = (() => {
    try {
      return new ImageryLayer(new UrlTemplateImageryProvider({
        url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        credit: 'Esri', maximumLevel: 19,
      }))
    } catch { return undefined }
  })()

  // load cables/quakes/pins once (independent of progressRef)
  useEffect(() => {
    const viewer = viewerRef.current?.cesiumElement
    if (!viewer || viewer.isDestroyed?.()) return
    viewer.clock.shouldAnimate = true   // keep the spin tick firing
    // fetch('/submarine-cables.json') + USGS quakes + local pins (see G30/G45)
  }, [])

  // ONE steady clock tick: lerp dolly-out toward scroll target + constant spin.
  useEffect(() => {
    const viewer = viewerRef.current?.cesiumElement
    if (!viewer || viewer.isDestroyed?.()) return
    const SPIN = 0.025 // deg/tick — slow axial rotation (~1 rev / 25s)
    const remove = viewer.clock.onTick.addEventListener(() => {
      const c = camRef.current
      const prog = progressRef.current || 0
      const p = prog * prog * (3 - 2 * prog)         // smoothstep
      const tHeight = 600000 * Math.pow(2.4e6 / 600000, p) // 600k → 2.4M
      const tPitch = -55 + p * 50                     // top crop → whole globe
      const tLat = 8 - p * 6
      c.height = approach(c.height, tHeight)
      c.pitch = approach(c.pitch, tPitch)
      c.lat = approach(c.lat, tLat)
      c.heading = (c.heading + SPIN) % 360
      viewer.camera.setView({
        destination: Cartesian3.fromDegrees(0, c.lat, c.height),
        orientation: { heading: CesiumMath.toRadians(c.heading),
          pitch: CesiumMath.toRadians(c.pitch), roll: 0 },
      })
    })
    return () => remove()
  }, [progressRef])

  return <Viewer ref={viewerRef} baseLayer={baseLayer} className="globe-canvas"
    animation={false} timeline={false} baseLayerPicker={false} geocoder={false}
    homeButton={false} sceneModePicker={false} navigationHelpButton={false}
    fullscreenButton={false} infoBox={false} selectionIndicator={false} scene3DOnly />
}

export default memo(GlobeStage)
```

## App.jsx wiring (throttled ref, not re-render)
```jsx
const progressRef = useRef(0)
useEffect(() => {
  let ticking = false
  const onScroll = () => {
    if (ticking) return
    ticking = true
    requestAnimationFrame(() => {
      const max = document.documentElement.scrollHeight - window.innerHeight
      const p = max > 0 ? Math.min(1, Math.max(0, window.scrollY / max)) : 0
      progressRef.current = p          // NO setState for the globe
      ticking = false
    })
  }
  window.addEventListener('scroll', onScroll, { passive: true })
  return () => window.removeEventListener('scroll', onScroll)
}, [])
// <GlobeStage progressRef={progressRef} />
```

## Verify the blink fix (in-browser)
Scroll from section 1 to the last; confirm the Cesium canvas is the SAME node:
```js
const a = document.querySelector('.cesium-widget canvas')
// scroll to last section
const b = document.querySelector('.cesium-widget canvas')
console.log(a === b) // must be true
```
`sameCanvasNode: true` proves the Viewer is not re-mounting.

## Navigator dead-button trap (separate, easy to miss)
If the page has a floating up/down navigator that calls `el.scrollIntoView()` per
section index, every section MUST register its ref — including the LAST one.
Forgetting `ref={(el)=>(sectionsRef.current[N]=el)}` on the final section (e.g. the
CTA footer) makes `sectionsRef.current[N]` undefined → the last down-click is a
silent no-op. Symptom: "last arrow from page 6→7 does nothing." Fix: add the ref
to the final section.
