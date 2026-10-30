# The Wall — build recipe + resium/Cesium pitfalls

Condensed from the 2026-07-19 build of MARU "the Wall" (digital-twin receiving end).
Companion to the SKILL.md "The Wall" section.

## Why glTF/GLB (not SketchUp .skp)
- Cesium (`resium <Model>`) loads .glb / .gltf natively. `.skp` is NOT a web/runtime format.
- Pipeline: SketchUp → Export → .glb (or .gltf+binary). Draco-compress for the wire.
- Lidar: Cesium 3D Tiles (`<Cesium3DTileset>`, `url` to `tileset.json`), NOT a raw point cloud.
- Durable rule: MARU stores model URL + format; it does NOT convert. Client exports once.

## Resium component facts (verified against resium@1.24 types in node_modules)
- `<Model>` cesiumProps INCLUDE: `url`, `modelMatrix`, `scale`, `show`, `minimumPixelRatio`,
  `id`. (NOT `baseResolution`, `incrementallyLoadTextures` — those are not resium props;
  drop them or you get runtime warnings.)
- `<Cesium3DTileset>` cesiumProps INCLUDE `url`, `show`.
- Both render INSIDE `<Viewer>` (Cesium's React root). A component using `useCesium()`
  MUST be a descendant of `<Viewer>` or the hook returns undefined.

## ESM import pitfall (the one that bites)
- `require('cesium')` does NOT work in MARU's ESM (Vite) build. DO NOT use it.
- Import named Cesium classes directly from the `cesium` package:
  `import { Cartesian3, Color, Transforms, HeadingPitchRoll, Math as CesiumMath,
  VerticalOrigin, LabelStyle, Cartesian2, NearFarScalar, ScreenSpaceEventHandler,
  ScreenSpaceEventType, HeightReference } from 'cesium'`

## Upright placement (east-north-up transform)
```js
import { Cartesian3, Transforms, HeadingPitchRoll, Math as CesiumMath } from 'cesium'
function modelMatrix(origin, headingDeg = 0) {
  const pos = Cartesian3.fromDegrees(origin.lon, origin.lat, origin.alt ?? 0)
  const hpr = new HeadingPitchRoll(CesiumMath.toRadians(headingDeg), 0, 0)
  return Transforms.headingPitchRollToFixedFrame(pos, hpr)
}
// <Model url={url} scale={s} modelMatrix={modelMatrix(origin, heading)} ... />
```
- glTF is +Y up; Cesium orients it correctly once position is set. You only need pos + heading.
- `modelMatrix` overrides `position`/`orientation`/lat-lon — pick ONE approach (modelMatrix wins).

## Click handling on slot pins
- Use `useCesium()` → `viewer.screenSpaceEventHandler` (set in `onReady`/`useEffect`,
  guarded by `if (!viewer) return`).
- `ScreenSpaceEventHandler` + `ScreenSpaceEventType.LEFT_CLICK`; test `picked.id?.id`
  against your slot id. Remove handler on unmount (`handler.destroy()`).
- Alternative (simpler): `onClick` prop on `<Entity>` — resium forwards the picked entity.

## State placement (the MARU-specific gotcha)
- The twin registry (walls[]) must live in `EdgeDataContext` (NOT a Cesium-aware file),
  because BOTH the map component (`<DigitalTwinWall>`, inside `<Viewer>`) and the
  Studio panel (`<TwinWallStudio>`, a flyout) read/write it. Put registry + `showTwinWall`
  flag there. Keep `twinRegistry.js` free of any `cesium` import.
- `initTwinState()` returns the `{twinWalls, upsertTwinWall, removeTwinWall, validateWall,
  resolveTwinSlot, twinWallCount}` blob to spread into the context's `useState` bundle.

## Wiring a new MARU layer (the 7-touch template, confirmed green)
1. Define state + flag in `EdgeDataContext` (e.g. `showTwinWall`, `twinWalls`) + spread
   `initTwinState()` into the provider value.
2. `MapControlPanel.jsx`: destructure the flag/count from `useEdgeData()`; add a row to
   `ENTITY_META` (`twin_wall: {count, noun}`); add `l.id === 'twin_wall' → showTwinWall`
   in `isLayerOn`; add the toggle branch in the `onToggle` chain; render a group + action button.
3. `App.jsx`: import the component; add `const [XxxOpen, setXxxOpen] = useState(false)`;
   thread `XxxOpen` through `openRight`/`openSecondary`/`closeRight`/`closeAllFlyouts`;
   mount the 3D component inside `<Viewer>` (self-gating on `showX`); mount the Studio
   flyout as a sibling of the other right flyouts; pass `onOpenStudio` to `MapControlPanel`.
4. `App.css`: mirror `settings-drawer` / `.mcp-row*` classes for the flyout + inputs.
5. Verify: `npm run lint` (0 errors) + `npm run build` (green). Do NOT commit — user
   reviews in Xcode + Cmd+B, then commits.

## Honest gap (next chunk)
Live client socket data is NOT yet rendered onto slot pins. `resolveAnchor` accepts
`wallResolver` (card `{building, slot}` → slot marker position) but `ClientLayerRenderer`
does not yet consume twin anchors for display. The "wow" = a front-door reading ON the
front-door pin — wire that next.
