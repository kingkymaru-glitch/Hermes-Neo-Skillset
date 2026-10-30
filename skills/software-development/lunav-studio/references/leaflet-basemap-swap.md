# Leaflet basemap swap — replace tile layer only, keep all overlays

Pattern used on the LunaV **Project Homepage** (`/project/[id]/home`) Leaflet 2D map
to add a Map (OSM) / Satellite (Esri) toggle WITHOUT disturbing polygons, node pins,
annotations, draw boxes, or handles.

## Why this matters
Re-creating the Leaflet map (`L.map(...)`) to change the basemap would wipe every
overlay and re-trigger the load/center logic. MARU's requirement was explicit:
"when selected the OSM map only it change while maintaining all other nodes, box,
comment intact." The fix is to swap ONLY the tile layer, not the map.

## Mechanism
- Keep a `tileRef` (useRef) pointing at the currently-added `L.tileLayer`.
- On basemap change, `map.removeLayer(tileRef.current)` then `L.tileLayer(newUrl).addTo(map)`.
- The map instance, its panes, and all overlay layers (polygons, markers, DOM boxes)
  are untouched → they persist across the swap.

## Reference implementation (ProjectHomepage.tsx)
```js
const OSM_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const OSM_ATTR = "© OpenStreetMap contributors";
const BASEMAPS = {
  satellite: { url: ESRI_SATELLITE, attr: ESRI_ATTR, maxZoom: 19 }, // Esri World_Imagery
  map:       { url: OSM_URL,         attr: OSM_ATTR,   maxZoom: 19 },
};

const [baseMap, setBaseMap] = useState("satellite"); // fronting default
const tileRef = useRef(null);

// init: add the default tile, store ref
const tile = L.tileLayer(BASEMAPS[baseMap].url, { maxZoom, attribution }).addTo(map);
tileRef.current = tile;

// swap effect — runs on baseMap change; preserves all overlays
useEffect(() => {
  const map = mapRef.current;
  if (!map || !mapReady) return;
  let cancelled = false;
  (async () => {
    const L = await loadLeaflet();           // cached after first load
    if (cancelled || !mapRef.current) return;
    const cfg = BASEMAPS[baseMap];
    if (tileRef.current) map.removeLayer(tileRef.current);
    const t = L.tileLayer(cfg.url, { maxZoom: cfg.maxZoom, attribution: cfg.attr }).addTo(map);
    tileRef.current = t;
  })();
  return () => { cancelled = true; };
}, [baseMap, mapReady]);
```

## UI toggle (top-left, glass segmented control)
```jsx
<div className="ph-basemap-toggle" role="group">
  <button className={baseMap === "map" ? "is-active" : ""} onClick={() => setBaseMap("map")}>Map</button>
  <button className={baseMap === "satellite" ? "is-active" : ""} onClick={() => setBaseMap("satellite")}>Satellite</button>
</div>
```
CSS: `position:absolute; top:12px; left:12px; z-index:8` glass pill; `.is-active` uses
`var(--mb-turquoise)` bg. Keep it top-LEFT so it doesn't collide with the top-right
draw-tools FAB.

## Gotchas
- `L` inside the swap effect must be (re)loaded via `loadLeaflet()` — the module-level
  `L` from the init effect is out of scope there. Awaiting it is fine (cached, instant).
- Default MUST be `satellite` (Esri) — MARU rejected the flat OSM default; satellite is
  the fronting/first-load layer.
- Don't use `map.setView` or re-add overlays in the swap effect — that defeats the point.
- This is the Leaflet analog of R-Tessera's raster swap in `ViewerBridge` (Cesium imagery
  layer removal + re-add). Same principle: mutate the basemap layer, not the scene.
