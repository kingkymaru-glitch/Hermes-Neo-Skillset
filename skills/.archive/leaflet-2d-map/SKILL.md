---
name: leaflet-2d-map
description: Use when Cesium fails — Leaflet 2D satellite map fallback.
category: frontend
---

# Leaflet 2D Satellite Map (Cesium Fallback)

When a Cesium 3D globe won't load (CDN drama, WebGL issues, Next.js bundle conflicts), drop it for Leaflet. Lighter, faster, and always works. Used in LunaV Project Homepage as the primary map after Cesium repeatedly failed.

## When to use

- Cesium won't load after multiple attempts (CDN, WebGL, bundler issues).
- User explicitly wants a 2D satellite map ("no need the globe").
- The project homepage only needs: satellite base + center marker + optional polygon draw.
- You need a map that loads in ~200ms with zero configuration.

## Core pattern

### 1. CDN loader

Load Leaflet CSS + JS from unpkg at runtime (avoids Next.js bundler entirely):

```ts
function loadLeaflet(): Promise<any> {
  return new Promise((resolve, reject) => {
    const w = window as any;
    if (w.L) return resolve(w.L);
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
    document.head.appendChild(link);
    const script = document.createElement("script");
    script.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
    script.onload = () => {
      if ((window as any).L) resolve((window as any).L);
      else reject(new Error("Leaflet loaded but L not found"));
    };
    script.onerror = () => reject(new Error("Failed to load Leaflet from CDN"));
    document.body.appendChild(script);
  });
}
```

### 2. ESRI World Imagery (free, keyless satellite)

```ts
const ESRI_SATELLITE = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";
const ESRI_ATTR = "Esri, Maxar, Earthstar Geographics";

// Inside bootstrap useEffect:
const map = L.map(container, {
  attributionControl: false,
  zoomControl: true,
}).setView([20, 0], 4);
L.tileLayer(ESRI_SATELLITE, { maxZoom: 19, attribution: ESRI_ATTR }).addTo(map);
```

### 3. Full-viewport layout (Next.js client component)

The map container needs a definite parent height. Use `100dvh` on the outer wrapper and `flex: 1` on the map shell:

```tsx
<div className="dash-bg flex flex-col" style={{ height: "100dvh" }}>
  <nav>...</nav>
  <div className="ph-shell" style={{ flex: 1 }}>
    <div ref={containerRef} className="ph-globe" />
  </div>
</div>
```

The CSS:
```css
.ph-shell { position: relative; height: 100%; width: 100%; }
.ph-globe { position: absolute; inset: 0; height: 100%; width: 100%; }
```

### 4. Draw area — DO NOT use Leaflet draggable paths. Use a custom DOM overlay box.

Leaflet's `L.rectangle(..., { draggable: true })` and `map.on("click")` polygon drawing **do not work** in practice when the map is inside a React component loaded via CDN. Leaflet's map-level gesture handler intercepts `pointerdown` BEFORE the Path layer or click handler sees it, so:
- `draggable: true` rectangles can't be grabbed (every drag just pans the map).
- `map.on("click")` draw handlers never fire because the click is consumed as a map drag/pan.

**The working pattern: a plain HTML `<div>` box overlay driven by React pointer events.** The box is NOT a Leaflet object — it floats over the map at a computed pixel rect. Leaflet's gesture system can't touch it.

State + refs:
```ts
const [box, setBox] = useState<{ s: number; w: number; n: number; e: number } | null>(null);
const dragRef = useRef<{ mode: "move" | "se" | "nw" | null; startX: number; startY: number; startBox: any } | null>(null);
```

When draw mode turns on, seed the box at the map center (or pin):
```ts
useEffect(() => {
  const map = mapRef.current;
  if (!map || !mapReady) return;
  if (drawMode) {
    const c = site?.center_lat != null
      ? { lat: site.center_lat, lng: site.center_lon as number }
      : map.getCenter();
    const span = 0.004; // ~400m box
    setBox({ s: c.lat - span, w: c.lng - span, n: c.lat + span, e: c.lng + span });
    map.dragging.disable(); map.boxZoom.disable();
    map.scrollWheelZoom.disable(); map.doubleClickZoom.disable();
  } else {
    setBox(null);
    map.dragging.enable(); map.boxZoom.enable();
    map.scrollWheelZoom.enable(); map.doubleClickZoom.enable();
  }
}, [drawMode, mapReady, site?.center_lon, site?.center_lat]);
```

Mirror the box to a non-interactive Leaflet rectangle for visual parity (optional):
```ts
useEffect(() => {
  const map = mapRef.current; const L = (window as any).L;
  if (!map || !L) return;
  if (rectRef.current) { map.removeLayer(rectRef.current); rectRef.current = null; }
  if (box) {
    rectRef.current = L.rectangle([[box.s, box.w], [box.n, box.e]],
      { color: "#00e5c3", weight: 3, fillOpacity: 0.15, interactive: false, pane: "overlayPane" }).addTo(map);
  }
}, [box]);
```

Convert lat/lng box → pixel rect for the overlay:
```ts
const boxToPixels = () => {
  const map = mapRef.current; if (!map || !box) return null;
  const nw = map.latLngToContainerPoint([box.n, box.w]);
  const se = map.latLngToContainerPoint([box.s, box.e]);
  return { left: nw.x, top: nw.y, width: se.x - nw.x, height: se.y - nw.y };
};
```

Pointer handlers (pixel delta → lat/lng delta at current zoom):
```ts
const onBoxPointerDown = (e: React.PointerEvent) => {
  if (!box) return;
  e.stopPropagation();
  (e.target as HTMLElement).setPointerCapture(e.pointerId);
  dragRef.current = { mode: "move", startX: e.clientX, startY: e.clientY, startBox: box };
};
const onHandlePointerDown = (corner: "se" | "nw") => (e: React.PointerEvent) => {
  if (!box) return;
  e.stopPropagation();
  (e.target as HTMLElement).setPointerCapture(e.pointerId);
  dragRef.current = { mode: corner, startX: e.clientX, startY: e.clientY, startBox: box };
};
const onPointerMove = (e: React.PointerEvent) => {
  const d = dragRef.current; const map = mapRef.current;
  if (!d || !map || !d.startBox) return;
  const dxPx = e.clientX - d.startX, dyPx = e.clientY - d.startY;
  const size = map.getSize();
  const b = d.startBox;
  const dLng = (dxPx / size.x) * (map.getBounds().getEast() - map.getBounds().getWest());
  const dLat = -(dyPx / size.y) * (map.getBounds().getNorth() - map.getBounds().getSouth()); // y inverted
  if (d.mode === "move") setBox({ s: b.s+dLat, w: b.w+dLng, n: b.n+dLat, e: b.e+dLng });
  else if (d.mode === "se") setBox({ ...b, s: b.s+dLat, e: b.e+dLng });
  else if (d.mode === "nw") setBox({ ...b, n: b.n+dLat, w: b.w+dLng });
};
const onPointerUp = (e: React.PointerEvent) => {
  if (dragRef.current) { try { (e.target as HTMLElement).releasePointerCapture(e.pointerId); } catch {} }
  dragRef.current = null;
};
```

Render the overlay (inside `.ph-shell`, which carries `onPointerMove`/`onPointerUp`):
```tsx
{drawMode && box && (() => {
  const px = boxToPixels(); if (!px) return null;
  return (
    <div style={{ position:"absolute", left:px.left, top:px.top, width:px.width, height:px.height,
        border:"3px solid #00e5c3", background:"rgba(0,229,195,0.12)", zIndex:6, cursor:"move", touchAction:"none" }}
        onPointerDown={onBoxPointerDown}>
      <div style={{ position:"absolute", right:-8, bottom:-8, width:16, height:16, background:"#00e5c3",
          border:"2px solid #04110e", borderRadius:4, cursor:"nwse-resize", touchAction:"none" }}
          onPointerDown={onHandlePointerDown("se")} />
      <div style={{ position:"absolute", left:-8, top:-8, width:16, height:16, background:"#00e5c3",
          border:"2px solid #04110e", borderRadius:4, cursor:"nwse-resize", touchAction:"none" }}
          onPointerDown={onHandlePointerDown("nw")} />
    </div>
  );
})()}
```
On Confirm, convert `box` → GeoJSON ring (note the `[lng, lat]` order for GeoJSON):

```ts
const ring = [[box.w, box.s], [box.e, box.s], [box.e, box.n], [box.w, box.n], [box.w, box.s]];
const polygon = { type: "Polygon" as const, coordinates: [ring] };
const lon = (box.w + box.e) / 2, lat = (box.s + box.n) / 2;
```

### 4b. Polygon trace mode (freeform area — preferred by founder over fixed box)

Offer BOTH: a **Box area** button (`drawShape="box"`) and a **Trace polygon** button (`drawShape="polygon"`). For polygon trace, click points directly on the map (NOT Leaflet draggable, NOT `map.on("click")` — same gesture-swallow problem). Capture clicks via the container's React `onClick` + `containerPointToLatLng`:

State: `const [polyPts, setPolyPts] = useState<[number, number][]>([]); // [lat,lng]`

```ts
const onMapClick = (e: React.MouseEvent) => {
  if (!(drawMode && drawShape === "polygon")) return;
  const map = mapRef.current; if (!map) return;
  const rect = (containerRef.current as HTMLElement).getBoundingClientRect();
  const pt = map.containerPointToLatLng([e.clientX - rect.left, e.clientY - rect.top]);
  setPolyPts((prev) => [...prev, [pt.lat, pt.lng]]);
};
// wire: <div ref={containerRef} className="ph-globe" onClick={onMapClick} />
```

Live preview while tracing (non-interactive Leaflet polygon, mirrored like the box):
```ts
useEffect(() => {
  const map = mapRef.current; const L = (window as any).L;
  if (!map || !L) return;
  if (polyRef.current) { map.removeLayer(polyRef.current); polyRef.current = null; }
  if (drawMode && drawShape === "polygon" && polyPts.length > 0) {
    polyRef.current = L.polygon(polyPts.map(([lat,lng]) => [lat,lng]),
      { color:"#00e5c3", weight:3, fillOpacity:0.15, interactive:false, pane:"overlayPane" }).addTo(map);
  }
}, [polyPts, drawMode, drawShape]);
```

Confirm (>=3 pts), GeoJSON ring `[lng,lat]`:
```ts
const ring = [...polyPts.map(([lat,lng]) => [lng,lat] as [number,number]), [polyPts[0][1], polyPts[0][0]]];
const polygon = { type:"Polygon" as const, coordinates:[ring] };
const lat = polyPts.reduce((a,p)=>a+p[0],0)/polyPts.length;
const lng = polyPts.reduce((a,p)=>a+p[1],0)/polyPts.length;
persist({ area_polygon: polygon, center_lon: lng, center_lat: lat });
```

Toolbar for polygon mode: show `Click N points`, **Finish (N)**, **Undo point** (`setPolyPts(p=>p.slice(0,-1))`), **Cancel**.

### 4c. Multiple areas (array) + per-area delete

Store areas as an ARRAY `site.area_polygons: Polygon[]` (NOT a single `area_polygon`). Confirm APPENDS to the array; never overwrites. Each saved area gets its own **✕** delete button (anchored at the polygon's bounding-box top-left in container pixels) that removes that one index.

```ts
// Confirm (box or polygon trace) — APPEND, don't overwrite:
const ring = [...]; // GeoJSON [lng,lat] ring
const polygon = { type: "Polygon" as const, coordinates: [ring] };
const lon = (box.w + box.e) / 2, lat = (box.s + box.n) / 2;
persist({ area_polygons: [...(site?.area_polygons ?? []), polygon],
          center_lon: site.center_lon ?? lon, center_lat: site.center_lat ?? lat });
// only set center on the FIRST area (?? ) so the view isn't reset on every add.

const deleteAreaAtIndex = (i: number) => {
  const list = (site?.area_polygons ?? []).filter((_, idx) => idx !== i);
  persist({ area_polygons: list });
};
```

Render EVERY polygon in the array (loop), not just one:
```ts
useEffect(() => {
  const map = mapRef.current; const L = (window as any).L;
  if (!map || !L) return;
  // keep a ref array so each layer is removed before re-adding
  if (polyRefs.current) polyRefs.current.forEach(r => map.removeLayer(r));
  polyRefs.current = [];
  for (const poly of site?.area_polygons ?? []) {
    const coords = poly.coordinates[0].map((p: number[]) => [p[1], p[0]]); // swap lng/lat
    polyRefs.current.push(L.polygon(coords, { color:"#00e5c3", fillColor:"#00e5c3", fillOpacity:0.15, weight:3 }).addTo(map));
  }
}, [site?.area_polygons, mapReady]);
```
Also offer a bulk **🗑 Delete all areas (n)** button (owner only) that `persist({ area_polygons: [] })`. The per-area ✕ and the bulk button are the key requirements when the user wants "multiple work areas." Keep `previewRef` for the live trace preview (§4b) and `polyRefs` for the saved array — SEPARATE refs (see Pitfalls).

Key insight: `setPointerCapture` keeps the drag tracking even if the cursor leaves the element. `touchAction: "none"` stops mobile scroll-steal. Disable map dragging while drawing so the box math stays 1:1 with pixels. For polygon trace, the same gesture-swallow rule applies — use the container `onClick`+`containerPointToLatLng`, never Leaflet's click handler.

### 5. Render existing polygons (array — coordinate swap)

Leaflet expects `[lat, lng]` — swap from GeoJSON's `[lng, lat]`. When `area_polygons` is an array, loop and keep a ref array so each layer is removed before re-adding on change:

```ts
const polyRefs = useRef<any[]>([]);
useEffect(() => {
  const map = mapRef.current; const L = (window as any).L;
  if (!map || !L) return;
  polyRefs.current.forEach(r => map.removeLayer(r)); polyRefs.current = [];
  for (const poly of site?.area_polygons ?? []) {
    const coords = (poly.coordinates[0] as number[][]).map((p) => [p[1], p[0]]); // swap lng/lat
    polyRefs.current.push(
      L.polygon(coords, { color:"#00e5c3", fillColor:"#00e5c3", fillOpacity:0.15, weight:3 }).addTo(map)
    );
  }
}, [site?.area_polygons, mapReady]);
```

### 6. Center on loaded coordinate

```ts
useEffect(() => {
  const map = mapRef.current;
  const L = (window as any).L;
  if (!map || !mapReady || center_lon == null) return;
  map.setView([center_lat, center_lon], 16);
}, [center_lon, center_lat, mapReady]);
```
Do NOT drop a marker here at the area centroid — the polygon/box IS the centroid's visual. A centroid marker is what created the phantom "2nd node" confusion (§6b).

### 6b. ALWAYS show the source pin as a persistent marker (geo-linked apps)

When the map is geo-linked to an external pinpoint (e.g. an R-Tessera node stored in a shared `project_nodes` table, distinct from any area polygon the user draws on the homepage), the source pin MUST always render as its own marker — independent of the area shape.

**Pitfall — do NOT remove the marker to "clean up duplicates."** We once removed the center marker to kill a phantom "2nd node" (a duplicate marker drawn at the area polygon's centroid) and accidentally removed the SOURCE pin too — so the homepage showed nothing when no area was drawn. The fix is NOT to delete the marker, it's to (a) not draw a marker at the area centroid at all, and (b) keep a dedicated source-pin marker from the geo table.

Pattern:
- Store the pin in its own state, captured in the load effect from the shared node table (survives area-center changes):
  ```ts
  const [nodePin, setNodePin] = useState<{ lon: number; lat: number } | null>(null);
  const nodeRef = useRef<any>(null);
  // in load effect, after loadNodeCenter(projectId):
  if (nodeCenter) setNodePin({ lon: nodeCenter.lon, lat: nodeCenter.lat });
  ```
- Render it as a separate marker in its own effect (never tied to `area_polygon`):
  ```ts
  useEffect(() => {
    const map = mapRef.current; const L = (window as any).L;
    if (!map || !L) return;
    if (nodeRef.current) { map.removeLayer(nodeRef.current); nodeRef.current = null; }
    if (nodePin) {
      nodeRef.current = L.marker([nodePin.lat, nodePin.lon], {
        title: projectName,
        icon: L.divIcon({
          className: "ph-node-pin",
          html: '<div style="width:14px;height:14px;border-radius:50%;background:#00e5c3;border:3px solid #04110e;box-shadow:0 0 8px #00e5c3;"></div>',
          iconSize: [14, 14],
        }),
      }).addTo(map);
    }
  }, [nodePin, mapReady, projectName]);
  ```
- The "Delete area" button clears ONLY `area_polygon` + center — never the source pin (the pin is the immutable link back to the external app).
- Rule: the source pin (geo table) and the area polygon (user-drawn, persisted on the homepage) are TWO distinct visuals. Touching one must not remove the other. If "the node I pinned is missing" appears after an edit, check whether your edit deleted the source-pin marker instead of just the centroid marker.

## 7. Annotation layer — text box + arrow pointer (freeform map notes)

A user "draws a text box and pulls an arrow to indicate something." Build it with the SAME custom-DOM-overlay + pointer-capture pattern as §4 (never Leaflet draggable/markers — same gesture-swallow). The arrow is an SVG `<line>` + `<circle>` computed from two lat/lng points; the text is a `contentEditable` div; both endpoints are draggable.

### State
```ts
const [annoDraft, setAnnoDraft] = useState<{ box: [number, number]; tip: [number, number] } | null>(null);
const [annoText, setAnnoText] = useState("");
const [annoEditingId, setAnnoEditingId] = useState<string | null>(null);
const annoDragRef = useRef<{ mode: "box" | "tip" | "resize"; startX: number; startY: number; start: [number, number]; startW?: number; startH?: number } | null>(null);
const [resizeOverride, setResizeOverride] = useState<{ id: string; w: number; h: number } | null>(null); // live size while resizing a saved box
const ANNO_DEFAULT_W = 140, ANNO_DEFAULT_H = 60;
// annotations persisted on the row, e.g. ProjectSite.annotations[]:
// { id, text, box_lat, box_lng, tip_lat, tip_lng, w, h }  // w/h = pixel size, persisted so resize survives reload
```

### Helpers + handlers (reuse §4's latLngToPixel / pixel→latlng math)
```ts
const latLngToPixel = (lat: number, lng: number) => mapRef.current?.latLngToContainerPoint([lat, lng]) ?? null;

const startAnnotation = () => {
  const c = site?.center_lat != null ? { lat: site.center_lat, lng: site.center_lon as number } : mapRef.current!.getCenter();
  setAnnoDraft({ box: [c.lat, c.lng - 0.0015], tip: [c.lat, c.lng + 0.0015] }); // box left, tip right
  mapRef.current?.dragging.disable(); mapRef.current?.boxZoom.disable(); mapRef.current?.scrollWheelZoom.disable();
};

const onAnnoBoxPointerDown = (e) => { e.stopPropagation(); (e.target as HTMLElement).setPointerCapture(e.pointerId); annoDragRef.current = { mode: "box", startX: e.clientX, startY: e.clientY, start: annoDraft!.box }; };
const onAnnoTipPointerDown = (e) => { e.stopPropagation(); (e.target as HTMLElement).setPointerCapture(e.pointerId); annoDragRef.current = { mode: "tip", startX: e.clientX, startY: e.clientY, start: annoDraft!.tip }; };
const onAnnoPointerMove = (e) => {
  const d = annoDragRef.current, map = mapRef.current; if (!d || !map || !d.start) return;
  const dxPx = e.clientX - d.startX, dyPx = e.clientY - d.startY, size = map.getSize();
  const dLng = (dxPx / size.x) * (map.getBounds().getEast() - map.getBounds().getWest());
  const dLat = -(dyPx / size.y) * (map.getBounds().getNorth() - map.getBounds().getSouth());
  setAnnoDraft((p) => p ? { ...p, [d.mode]: [d.start[0] + dLat, d.start[1] + dLng] } : p);
};
const onAnnoPointerUp = (e) => { try { (e.target as HTMLElement).releasePointerCapture(e.pointerId); } catch {} annoDragRef.current = null; };
```

Wire both move/up handlers onto the shell alongside the box's (call both from the same `onPointerMove`/`onPointerUp`).

### Save (persist array + size, merge — never replace whole row)
```ts
const saveAnnotation = () => {
  if (!annoDraft) return;
  const text = annoText.trim() || "Note";
  const list = [...(site?.annotations ?? [])];
  const w = resizeOverride?.id === annoEditingId ? resizeOverride.w : ANNO_DEFAULT_W;
  const h = resizeOverride?.id === annoEditingId ? resizeOverride.h : ANNO_DEFAULT_H;
  if (annoEditingId) { const i = list.findIndex(a => a.id === annoEditingId); if (i >= 0) list[i] = { ...list[i], text, box_lat: annoDraft.box[0], box_lng: annoDraft.box[1], tip_lat: annoDraft.tip[0], tip_lng: annoDraft.tip[1], w, h }; }
  else list.push({ id: `${Date.now()}-${Math.random().toString(36).slice(2,7)}`, text, box_lat: annoDraft.box[0], box_lng: annoDraft.box[1], tip_lat: annoDraft.tip[0], tip_lng: annoDraft.tip[1], w, h });
  setAnnoDraft(null); setAnnoEditingId(null); setAnnoText(""); setResizeOverride(null);
  mapRef.current?.dragging.enable(); mapRef.current?.boxZoom.enable(); mapRef.current?.scrollWheelZoom.enable();
  persist({ annotations: list });
};
```
Resize a saved box: a bottom-right handle. On `pointerdown` capture; on `pointermove` add pixel delta to `w`/`h` (NO lat/lng math — pure pixels), clamp to a min; on `pointerup` commit via `resizeOverride` → `persist`. Keep `resizeOverride` in state so the box renders at the new size live, and clear it on save.
```ts
const onAnnoPointerMove = (e) => {
  const d = annoDragRef.current, map = mapRef.current; if (!d || !map) return;
  const dxPx = e.clientX - d.startX, dyPx = e.clientY - d.startY;
  if (d.mode === "resize" && (d.startW != null)) {
    const w = Math.max(60, d.startW + dxPx), h = Math.max(32, d.startH! + dyPx);
    if (annoEditingId) setResizeOverride({ id: annoEditingId, w, h });
    return;
  }
  // (box/tip move math as before, pixel-delta → lat/lng)
};
```
Add `deleteAnnotation(id)` (filter + persist) and `editAnnotation(a)` (load into draft, disable map dragging, seed `resizeOverride` from `a.w/a.h`).

**Resize-handle render** (both draft + saved boxes, owner only): a 12px square at bottom-right with `cursor:"nwse-resize"`, `pointerEvents:"auto"`, `onPointerDown` setting `annoDragRef = { mode:"resize", startW, startH, start:[box] }`. The box `width`/`height` come from `resizeOverride` when its id matches, else `a.w || ANNO_DEFAULT_W`.

### Render overlay (map over saved + draft)
```tsx
{items.map((it) => {
  const b = latLngToPixel(it.box[0], it.box[1]); const t = latLngToPixel(it.tip[0], it.tip[1]);
  if (!b || !t) return null;
  return (
    <div key={it.id} style={{ position:"absolute", inset:0, zIndex:6, pointerEvents:"none" }}>
      <svg style={{ position:"absolute", inset:0, width:"100%", height:"100%", overflow:"visible" }}>
        <line x1={b.x} y1={b.y} x2={t.x} y2={t.y} stroke="#ffd23f" strokeWidth={3} />
        <circle cx={t.x} cy={t.y} r={6} fill="#ffd23f" stroke="#04110e" strokeWidth={2} />
      </svg>
      <div contentEditable suppressContentEditableWarning
        onInput={(e) => setAnnoText((e.target as HTMLElement).innerText)}
        style={{ position:"absolute", left:b.x-70, top:b.y-18, width:140, minHeight:36, background:"#04110e", border:"2px solid #ffd23f", borderRadius:8, padding:"6px 8px", color:"#ffd23f", fontSize:"0.78rem", pointerEvents:"auto", touchAction:"none", cursor: it.draft ? "text" : "move" }}
        onPointerDown={it.draft ? undefined : onAnnoBoxPointerDown}>
        {it.draft ? "" : it.text}
      </div>
      {it.draft && <div style={{ position:"absolute", left:t.x-7, top:t.y-7, width:14, height:14, background:"#ffd23f", border:"2px solid #04110e", borderRadius:"50%", cursor:"crosshair", pointerEvents:"auto", touchAction:"none" }} onPointerDown={onAnnoTipPointerDown} />}
      {!it.draft && canEdit && (<div style={{ position:"absolute", left:b.x+74, top:b.y-18, display:"flex", gap:4, pointerEvents:"auto" }}>
        <button onClick={() => editAnnotation(it)}>Edit</button>
        <button onClick={() => deleteAnnotation(it.id)} style={{ color:"var(--mb-red)" }}>×</button>
      </div>)}
    </div>
  );
})}
```
`pointerEvents:"none"` on the wrapper so map gestures (pan/zoom) still work *except* on the box/tip which set `pointerEvents:"auto"`. While a draft is active, map dragging is disabled (see `startAnnotation`) so dragging the box/tip never pans the map.

### Pitfalls (annotation layer)
- **Persist the array, not a scalar.** `annotations` is `jsonb[]` on the row. `persist({ annotations: list })` — do NOT `upsert` a single annotation; read the existing array, push/replace, write the whole array. Same merge discipline as §2b.
- **Text via `onInput`, not `value`.** A `contentEditable` div can't be a controlled `value` (React warns + cursor jumps). Capture text on `onInput`. Only persist on **Save** — not per keystroke — to avoid fighting the user mid-type. (User asked "auto-save on blur instead?" — optional; default is explicit Save.)
- **Re-enable map dragging on cancel/save.** Forgetting to re-enable `dragging`/`scrollWheelZoom` after leaving annotation mode leaves the map frozen. `saveAnnotation`/`cancelAnnotation`/`editAnnotation` must symmetrically toggle.
- **Arrow must be SVG, not a rotated div.** A line between two arbitrary points is trivial in SVG (`<line>`) but painful with CSS transforms. Keep the box as a `contentEditable` div and the arrow as an SVG overlay sharing the same `latLngToPixel` coords.
- **The annotation layer is a SEPARATE visual from the area polygon and the source pin** (§6b). Three independent layers: source pin (immutable link), area polygon/box (work area), annotations (notes+arrows). Editing one must never clear another.

## Pitfalls

- **`window.L` type erosion.** Cast: `const L = (window as any).L`. Don't use `typeof window.L` — compile errors in strict mode.
- **Coordinate format swap.** GeoJSON is `[lng, lat]`. Leaflet is `[lat, lng]`. Every coordinate must be flipped.
- **Container height collapse.** `height: 100%` on a flex child without `flex: 1` resolves to `0px`. Add `style={{ flex: 1 }}` to the map container, use `height: "100dvh"` (not `min-h-screen`) on the outer wrapper.
- **Map initialize before DOM ready.** Bootstrap in a `useEffect` with the container ref.
- **Loading indicator.** Show overlay while `!mapReady && !error`.

## Pitfalls (continued)

- **Container must stay MOUNTED — never early-return on loading/error.** A `useEffect(() => { init }, [])` that creates the Leaflet map runs ONCE, the moment the component first mounts. If the component does `if (loading) return <Spinner/>` (or `if (error) return <Err/>`) BEFORE the container div, the map div is unmounted during loading, `containerRef.current` is null when the effect fires, and when loading finishes the effect does NOT re-run (deps `[]`) → the map is never created → permanent blank. **Fix:** always render the container div; show loading/error as absolutely-positioned overlays ON TOP of it. The init effect then always has a live ref.

- **`invalidateSize()` after async init.** If Leaflet initializes while its flex/absolute container hasn't been laid out yet (zero height, or sized only after a sibling nav bar paints), it computes a 0×0 tile pane and never recovers. After `map.addTo(...)` / `setView`, call `setTimeout(() => map.invalidateSize(), 200)` so it re-measures the now-sized container.

- **Visibility-flag layers: default ON or persisted.** Any marker/entity layer gated behind a `show`/`visible` boolean that defaults to `false` will hide ALREADY-PERSISTED data after a refresh — the user sees their saved pin "vanish" and assumes the write failed. Default the flag to `true` (or read+persist the user's toggle), and render the layer's markers unconditionally from the loaded data. This bit the R-Tessera Projects layer: `showProjects` defaulted to `false`, so the saved node (which WAS in the DB) never rendered on reload.

- **Map div must have `z-index: 1` or it paints over the UI panels.** The map container is `position: absolute; inset: 0` and fills the shell. Any sibling panel that is also absolutely positioned (remarks card, draw-tools, search drawer) with `z-index: 5` will STILL be hidden IF the map div has NO z-index — an un-z-indexed absolute element paints above earlier siblings in source order, and a later sibling with `z-index:auto` sits in the same stacking context as the `z-index:5` panel but wins by DOM order. **Fix:** set `.ph-globe { z-index: 1; }` (or any value below the panels' `z-index:5`). Symptom this caused: "the whole homepage is just map, even the Project Details card is covered." The map mounted fine; it was simply stacking on top of the card.

- **Coordinate source-of-truth: the geo-pin MUST always overwrite a stale saved center.** In a geo-linked app, the user pins a coordinate (stored in a shared node table, e.g. R-Tessera `project_nodes`) and later draws an area polygon whose centroid is persisted as `center_lon/lat` (e.g. LunaV `project_sites`). On reload, if the load effect only seeds the center `if (center == null)`, the stale area center (B) survives and the fresh pin (A) is ignored — the map centers on the wrong place after the user "pinned A". **Fix:** always re-read the pin table and OVERWRITE `center_lon/lat` with the pin coordinate on every load (for the owner), so the homepage always shows where the user actually pinpointed. Only fall back to a saved center when no pin exists. Rule: the most-recent user intent (the pin) wins over a persisted derived value (the polygon centroid).

- **User preference: minimal over elaborate.** This founder explicitly rejected a Cesium 3D globe for a plain 2D Leaflet/ESRI satellite map ("no need the globe") and preferred freeform polygon-trace area selection over a rigid fixed box. Default to the SIMPLEST working map solution; don't reach for heavy 3D/globe stacks or overengineered draw tools unless asked. Offer a box AND a polygon-trace option rather than forcing one shape.

- **Keep a live-preview layer and a persisted layer in SEPARATE Leaflet refs — never share one ref.** When you draw an area you typically render a live preview (updates on every click/drag) AND later render the saved shape from `site.area_polygon`. If both use the same `polyRef`, the preview effect (which removes `polyRef.current` then only re-adds it when its guard passes, e.g. `drawMode && polyPts.length>0`) runs on draw-exit and WIPES the saved layer; because the saved-layer effect already ran, nothing re-adds it, so the drawn area silently disappears after Finish. **Fix:** give the preview its own ref (`previewRef`) and the saved area its own (`polyRef`); each effect only touches its own ref. Real case (LUNAV Project Homepage, 2026-08-09): the saved polygon vanished on Finish until the preview was split into `previewRef`. Symptom "drawn area not maintained visible" = almost always a shared-ref collision, not a persistence problem — check the refs first.

- **NEVER use Leaflet draggable: true paths or map.on("click") for draw tools inside a React+CDN-Leaflet component.** This burned 4 full iterations: the rectangle dropped fine but could not be grabbed/resized, and click-to-draw never registered because Leaflet's map gesture handler swallows the pointer before the Path or click handler sees it. The ONLY reliable draw UX is (a) a custom DOM div overlay box (see §4) with React pointer events + setPointerCapture, or (b) polygon trace via the container onClick + containerPointToLatLng (see §4b). Do not try once more with Leaflet draggable — it will fail the same way.

- **Multiple areas: APPEND to the array, render with a REF ARRAY, and give each area its own delete affordance.** When the user wants several work areas, site.area_polygons is Polygon[]. On Confirm, persist({ area_polygons: [...(site?.area_polygons ?? []), polygon] }) — never = polygon. Render by looping and pushing each Leaflet layer into a polyRefs.current array you clear+rebuild on every change (do not reuse a single polyRef for an array — you cannot remove N layers from one ref). Per-area x deletes list.filter((_,i)=>i!==idx); also offer a bulk Delete all (n). Only set center_lon/lat on the FIRST area (??) so adding areas 2..n does not recenter the map.

- **Resize a note box with PURE PIXEL delta — no lat/lng conversion.** Annotation text boxes store a pixel size w/h (persisted so it survives reload). The resize handle (bottom-right corner) on pointermove does w = Math.max(60, startW + dxPx), h = Math.max(32, startH + dyPx) — straight DOM pixels, clamped to a min. Keep a resizeOverride state so the box re-renders at the new size live, and commit it into the saved annotation on Save (then clear the override). Do NOT run the pixel-to-lat/lng math for resize — that math is only for moving the box/arrow endpoints, which are geo-anchored. Mixing the two is the classic bug that makes a resize fling the box across the map.

- **Keep THREE independent visual layers straight in a geo-linked map:** (1) the source pin (immutable R-Tessera node, §6b), (2) the area polygons/boxes (user-drawn work area, §4c/§5), (3) the annotation notes+arrows (§7). Each has its own state, its own Leaflet ref(s), and its own delete path. A save/delete on one MUST NOT clear another. The recurring failure mode this session: an edit meant to remove a duplicate centroid marker also deleted the source pin; and a shared polyRef between the live trace-preview and the saved layer made drawn areas vanish on Finish. Separate refs + separate state = no cross-clearing.

## Verification

1. `npx tsc --noEmit` clean.
2. `npm run build` green.
3. Hard-refresh: overlay flashes, satellite tiles load around pinned coordinate with marker.
4. Draw-to-polygon: toggle "Mark area of works", click 3+ points, "Finish" → polygon renders.
5. Source-pin check (geo-linked): with NO area drawn, the external pinpoint marker still shows (§6b) — don't let a centroid-marker cleanup delete the source pin.
6. Annotation layer: "Add note" → type → drag box/tip → Save → note + arrow persist after refresh.