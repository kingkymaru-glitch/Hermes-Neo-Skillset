# Static GLB Structural Models

Prefer a minimal static render path unless the user explicitly wants a layer toggle or live authoring flow.

## intake recipe
- copy `*.glb` into `public/assets/`
- import `ModelGraphics` from `cesium` in `src/App.jsx`
- memoize `Cartesian3` scale/`NearFarScalar` outside the render body
- render one map-ready `<Entity><ModelGraphics/></Entity>` block inside `<Viewer>`

## placement defaults
lat/lon defaults for Malaysia placeholders:
- Temenggor Dam/Gerik/Perak: `latitude: 5.420, longitude: 101.050, height: 60`
- Bangi demo array: `latitude: 2.9227, longitude: 101.768, height: 0`

## scaling guardrails
- `minimumPixelSize` stops the model vanishing at distance
- `maximumScale` keeps it from covering the whole globe when zoomed out
- prefer separate `scaleByDistance` rather than raw scalar scale only

## validation preflight (developer-debug read from console)
Before treating a viewer crash as a regression, differentiate:
- Missing table / API env error (`Could not find the table 'public.assets'...`); usually shows AFTER Viewer starts.
- Direct Cesium-Resium bridge throw `TypeError: Cannot set properties of undefined (setting '_definitionChanged')` from `resium/src/ModelGraphics/*` or `ModelGraphics.js`; this is a startup-path crash.

## fail-safe pattern
If offline mode is enabled or no model URI is present, return `null` from the structural-models component so `ModelGraphics` never mounts. If there is a model URI but the current viewer-device context does not guarantee the Cesium-Resium bridge, degrade to a placeholder entity-producing primitive first and only re-enable `ModelGraphics` once visibility is proven.

## governance-first principle
do not extend `layerRegistry`/`MapControlPanel` until:
- at least one model is confirmed visible, or
- the user requests multi-model visibility/toggling
