# GLB Model Import & Spatial Transform Studio

Pattern for importing `.glb` 3D models into a Cesium/Resium viewer with a
spatial-transform UI, click interaction, and a solution portal drawer.

## Resium `<Model>` component

Confirmed: resium exports `<Model>` (line 50 of `resium/dist/index.d.ts`).
Accepts `url` (path to `.glb`) and `modelMatrix` (Cesium.Matrix4).

```jsx
import { Model } from 'resium'  // NOT from 'cesium'

<Model
  ref={modelRef}
  url={model.url}              // local blob URL or HTTP .glb
  modelMatrix={modelMatrix}
  minimumPixelSize={64}
  show
/>
```

## Computing modelMatrix from spatial params

The canonical Cesium approach for placing a model at lat/lon with
heading/pitch/roll and uniform scale:

```js
import { Cartesian3, HeadingPitchRoll, Matrix4, Transforms } from 'cesium'

const center = Cartesian3.fromDegrees(lon, lat, height)
const hpr = HeadingPitchRoll.fromDegrees(heading, pitch, roll)
const modelMatrix = Transforms.headingPitchRollToFixedFrame(center, hpr)
const scaled = Matrix4.multiplyByUniformScale(modelMatrix, scale, new Matrix4())
```

Key: use `Transforms.headingPitchRollToFixedFrame()` — it combines the ENU
frame at position with the orientation in one call. Then apply scale via
`Matrix4.multiplyByUniformScale()`.

## Click detection on the model

Cesium's `ScreenSpaceEventHandler` picks primitives by pixel position:

```jsx
useEffect(() => {
  if (!viewer) return
  const handler = new ScreenSpaceEventHandler(viewer.scene.canvas)
  handler.setInputAction((movement) => {
    const picked = viewer.scene.pick(movement.position)
    if (picked?.primitive === modelRef.current?.cesiumElement) {
      onClick?.(model)  // fires only when THIS model is clicked
    }
  }, ScreenSpaceEventType.LEFT_CLICK)
  return () => handler.destroy()
}, [viewer, model.id, onClick])
```

The `cesiumElement` ref from resium's `<Model>` is the primitive that
`scene.pick()` returns — compare it to disambiguate from other scene objects.

## State shape

```js
{
  id: 'glb-<timestamp>-<random>',
  name: 'Human-readable label',
  url: 'https://...' | 'blob:...',
  longitude, latitude, height,  // degrees, degrees, meters
  heading, pitch, roll,         // degrees (0–360)
  scale,                        // uniform (default 1.0)
}
```

## Render all models in Viewer tree

Must be inside `<Viewer>` so `useCesium()` resolves:

```jsx
function GlbModelLayer() {
  const { glbModels } = useEdgeData()
  if (!glbModels?.length) return null
  return glbModels.map(m =>
    <DynamicGlbModel key={m.id} model={m} onClick={onModelClick} />
  )
}
```

Render `<GlbModelLayer />` inside the `<Viewer>` JSX tree (not as a child of
`<Viewer>` in the DOM — it relies on the Resium/Cesium context).

## Portal drawer pattern

When a model is clicked, lift the selected model state to the parent
(`App.jsx`) and pass it as `portalModel`/`setPortalModel` to both the studio
panel and the model layer. This lets click-from-map and click-from-list both
open the same drawer, even when the studio flyout is closed.

## Pitfall: `HeadingPitchRoll.fromDegrees` exists

Confirmed in `@cesium/engine/Source/Core/HeadingPitchRoll.js` line 77.
`Transforms.headingPitchRollQuaternion` is also available but
`headingPitchRollToFixedFrame` is simpler — it does position + orientation
in one call.
