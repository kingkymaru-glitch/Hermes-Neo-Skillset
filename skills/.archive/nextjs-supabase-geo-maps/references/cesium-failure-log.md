# Cesium CDN failures in Next.js (production build)

## Symptom
Production build passes (`next build EXIT=0`) but the browser throws:
```
SyntaxError: The only valid numeric escape in strict mode is '\0'
```
at a minified chunk (e.g. `06cei0ac5z5uk.js:877`).

## Root cause
Cesium's npm package embeds its wasm runtime as a base64 string in `Build/Cesium/Cesium.js`. The base64 string contains literal `\0` bytes inside template literals. Next.js's production minifier (Terser) preserves these escapes, and the browser rejects them because `\0` inside a template literal is illegal in strict-mode ES modules.

`transpilePackages: ['cesium']` in next.config does NOT fix this — the problem is the wasm embedding, not JS transpilation.

## CDN loading also fails
Loading Cesium from `https://cdn.jsdelivr.net/npm/cesium@<version>/Build/Cesium/Cesium.js` via dynamic `<script>` injection works in theory, but:

- The Cesium.js file is ~4 MB (wasm embedded) — slow to load
- The Viewer requires WebGL context, which may not be available
- Race condition: the `new Viewer(container)` call fires before the CSS (`widgets.css`) loads, and the React useEffect that sets up the viewer races with the load promise
- The camera `flyTo` runs before the viewer is ready (fixed with `cesiumReady` state, but still fragile)

## Solution: Leaflet
Replace Cesium entirely with Leaflet (unpkg CDN, ~40 KB). Free ESRI World Imagery satellite tiles provide the same visual without WebGL or wasm.

## ESRI World Imagery tile URL
```
https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}
```
Free, no API key, maxZoom 19. Attribution: "Esri, Maxar, Earthstar Geographics".