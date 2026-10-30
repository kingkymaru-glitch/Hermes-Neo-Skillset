---
name: leaflet-react-interactive-overlay
description: Leaflet map elements ignore drag/click in React.
---

# Leaflet + React: interactive overlays without the gesture fight

## Symptom
You add a `L.rectangle({draggable:true})` or `L.marker({draggable:true})` and the
user can't grab it — every pointerdown just pans the map, or the drag never
starts. This is especially common with **CDN Leaflet loaded into React** (L is a
global, not a hook) and with `react-leaflet` version mismatches. Leaflet's map
gesture handler intercepts the pointer before the path element sees it.

## Fix — render the interactive element as a CUSTOM DOM OVERLAY, not a Leaflet path
1. Keep the Leaflet map for tiles + the read-only polygon/area display.
2. For anything the user drags/resizes, render a plain `<div>` absolutely
   positioned OVER the map container. Position it by converting lat/lng → pixels:
   `map.latLngToContainerPoint([lat, lng])` → `{x, y}`.
3. Attach React `onPointerDown` to that div. In the handler:
   - `e.stopPropagation()` (so Leaflet never sees it),
   - `(e.target).setPointerCapture(e.pointerId)` (drag keeps tracking even if the
     cursor leaves the element),
   - store start pointer + start geometry in a ref.
4. On `onPointerMove` (on the map container or shell), compute pixel delta and
   convert to lat/lng delta:
   ```
   dLng = (dxPx / size.x) * (bounds.getEast() - bounds.getWest())
   dLat = -(dyPx / size.y) * (bounds.getNorth() - bounds.getSouth())  // y inverted
   ```
5. **Disable the map's competing handlers while drawing**: `map.dragging.disable()`,
   `map.boxZoom.disable()`, `map.scrollWheelZoom.disable()`,
   `map.doubleClickZoom.disable()`; re-enable on Finish/Cancel.
6. Re-render the overlay from state (lat/lng box or point list). The map container
   must stay mounted (never early-return on loading/error) or `latLngToContainerPoint`
   returns null — call `map.invalidateSize()` after the container becomes visible.
7. For resize handles, add small corner divs with their own `onPointerDown` that
   set a different drag mode (`"se"`/`"nw"`/`"tip"`); pixel delta maps directly to
   width/height (no lat/lng needed for size).

## Why this wins
Leaflet never gets the pointer event, so there's no race. The overlay is just
DOM, fully under React's control, and pointer-capture makes the drag robust.

## Pattern sketch
```tsx
const onBoxPointerDown = (e) => {
  e.stopPropagation();
  (e.target as HTMLElement).setPointerCapture(e.pointerId);
  drag.current = { mode: "move", sx: e.clientX, sy: e.clientY, start: box };
};
const onPointerMove = (e) => {
  const d = drag.current; if (!d) return;
  const dx = e.clientX - d.sx, dy = e.clientY - d.sy;
  const size = map.getSize(), b = map.getBounds();
  const dLng = (dx / size.x) * (b.getEast() - b.getWest());
  const dLat = -(dy / size.y) * (b.getNorth() - b.getSouth());
  setBox({ s: d.start.s + dLat, w: d.start.w + dLng, n: d.start.n + dLat, e: d.start.e + dLng });
};
```

## Keep Leaflet for display only
The saved area polygon / node pin can still be a real `L.polygon` / `L.marker`
(rendered from saved data, `interactive:false`) — only the *interactive* layer
needs to be the DOM overlay.

## Multi-area + resize extension (proven on a live geospatial homepage)
- **Multiple saved areas**: render every saved polygon with its OWN Leaflet ref
  (e.g. `polyRefs` array) OR a ref group, and remove-then-re-add on change.
  CRITICAL GOTCHA: the live trace **preview** must use a SEPARATE ref
  (`previewRef`) from the saved-area ref (`polyRef`). If both share one ref, the
  preview-clear effect wipes the saved area and it never redraws → "area
  disappears after Finish". Keep `previewRef` and `polyRef` distinct.
- **Resizable box/annotation**: the box is a DOM div. Add a corner handle div
  with its own `onPointerDown` setting `mode:"se"`. On move, size is pure pixel
  math — `w = max(60, startW + dxPx)`, `h = max(32, startH + dyPx)` — no lat/lng
  conversion. Persist `w`/`h` so resize survives reload; render uses
  `left: px.x - w/2, top: px.y - h/2, width: w, height: h`.
- **Arrow pointer**: an annotation = box (top-left anchor) + arrow line (SVG
  `<line>` from box center to tip) + tip dot. Tip is a draggable dot (separate
  drag mode `"tip"`) so the user aims it at a feature. Store `tip_lat/tip_lng`
  separately from `box_lat/box_lng`.

## The "blank / frozen / covered map" lesson (leaflet CDN in React)
- The map container MUST stay mounted even while `loading`/`error` — render those
  as OVERLAYS, never an early `return` before the container. An early return
  leaves `containerRef.current` null when the init effect runs.
- After the container becomes visible (it was `display:none`/zero-size during
  load), call `map.invalidateSize()` (setTimeout ~200ms) or tiles render at 0×0.
- Keep `z-index` discipline: map panes ~ layer 1; panels (remarks, draw tools)
  `z-index: 5+`; interactive overlay `z-index: 6`. A Leaflet overlay with no
  explicit z-index paints UNDER the `z-index:5` panels and looks "covered".
