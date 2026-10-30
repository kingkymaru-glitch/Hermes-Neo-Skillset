---
name: nextjs-supabase-geo-maps
description: Leaflet satellite maps with Supabase geo-data in Next.
---

## Trigger
Use when building a Next.js page that needs a live satellite map with polygon drawing, and the geo data (center coordinates, area polygons) is persisted to Supabase.

## Quick start (Leaflet, no Cesium)

**Do NOT use Cesium** in Next.js. Cesium's npm build embeds wasm as base64 with `\0` bytes — Next's production minifier emits them as illegal strict-mode escapes → browser SyntaxError. The CDN-loaded Cesium.js has flaky load timing (race conditions with React useEffect), and the Viewer requires WebGL which adds failure surface. Use **Leaflet** instead.

```tsx
// CDN loader — inject once, resolve with global L
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
    script.onload = () => resolve((window as any).L);
    script.onerror = () => reject(new Error("Leaflet CDN failed"));
    document.body.appendChild(script);
  });
}

// Free ESRI satellite tiles (no API key)
const SATELLITE_URL =
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";
```

In the bootstrap useEffect:
```ts
const L = await loadLeaflet();
const map = L.map(container, { attributionControl: false }).setView([lat, lon], 16);
L.tileLayer(SATELLITE_URL, { maxZoom: 19 }).addTo(map);
```

## Layout: flex + 100dvh for map container

When a map lives below a nav bar inside `flex flex-col`, the map container needs an explicit definite height or flex-grow. Use:

```tsx
<div className="dash-bg flex flex-col" style={{ height: "100dvh" }}>
  <nav ... />
  <div className="ph-shell" style={{ flex: 1 }}>
    <div ref={containerRef} className="ph-globe" />
  </div>
</div>
```

`min-h-screen` is NOT enough — flex only distributes space when the parent has a definite height. `100dvh` (dynamic viewport height, accounts for mobile browser chrome) plus `flex: 1` on the map shell ensures the map fills the remaining space.

## Supabase anon key: JWT rotation pitfall

Supabase can silently rotate its JWT signing secret. When this happens:
- The anon key payload (iss, ref, role, iat, exp) stays IDENTICAL
- Only the **signature** (third segment of the JWT) changes
- The old key returns `"Invalid API key"` on every request
- The `.env.local` file and any hardcoded keys become stale

**Fix:** go to Supabase Dashboard → Project Settings → API → copy the current `anon` `public` key. The JWT payload decodes with base64url so you can verify the `ref` field matches your project ID.

**Hardcoding for Vercel (no env vars needed):** the anon key is public by design (it's the same key shipped to every browser client). You can hardcode it directly in the client factory to bypass Vercel env var configuration entirely (free Hobby plan, zero settings). Create a file like `src/lib/supabaseClient.js`:

```js
import { createClient } from '@supabase/supabase-js'

export function createSupabase() {
  return createClient(
    'https://<project-id>.supabase.co',
    '<full-anon-key>',
    { auth: { persistSession: false, autoRefreshToken: false } },
  );
}
```

## Area selection — use a DRAGGABLE RECTANGLE, not click-to-add points

Leaflet's map is pan-draggable. A "click map to add a polygon point" handler fights the
drag handler: the `click` event either never fires (drag wins) or fires after a tiny drag
→ points land in the wrong place → "button does nothing / can't draw". **This pattern is
broken in practice — do not use it.**

Use a draggable + resizable `L.rectangle` instead:

```tsx
const rectRef = useRef<any>(null);

// When draw mode turns ON, drop a box at the pin center.
useEffect(() => {
  const map = mapRef.current; const L = (window as any).L;
  if (!map || !L || !mapReady) return;
  if (drawMode) {
    if (rectRef.current) { map.removeLayer(rectRef.current); rectRef.current = null; }
    const c = site?.center_lat != null
      ? [site.center_lat, site.center_lon as number] : map.getCenter();
    const span = 0.004; // ~400m box; tune to your scale
    rectRef.current = L.rectangle(
      [[c[0]-span, c[1]-span], [c[0]+span, c[1]+span]],
      { color: "#00e5c3", weight: 3, fillOpacity: 0.15, draggable: true },
    ).addTo(map);
  } else if (rectRef.current) {
    map.removeLayer(rectRef.current); rectRef.current = null;
  }
}, [drawMode, mapReady, site?.center_lon, site?.center_lat]);

// Confirm: read the rectangle bounds → build a 5-point GeoJSON ring (closed).
const confirmRect = useCallback(() => {
  const rect = rectRef.current;
  if (!rect) { setError("Start the area tool first to drop a box."); return; }
  const b = rect.getBounds();
  const sw = b.getSouthWest(), ne = b.getNorthEast();
  const ring: [number, number][] = [
    [sw.lng, sw.lat], [ne.lng, sw.lat], [ne.lng, ne.lat], [sw.lng, ne.lat], [sw.lng, sw.lat],
  ];
  const polygon = { type: "Polygon" as const, coordinates: [ring] };
  const lon = (sw.lng + ne.lng) / 2, lat = (sw.lat + ne.lat) / 2;
  setDrawMode(false);
  if (rectRef.current) { mapRef.current?.removeLayer(rectRef.current); rectRef.current = null; }
  persist({ area_polygon: polygon, center_lon: lon, center_lat: lat });
}, [persist]);

// Render an EXISTING saved polygon (GeoJSON → Leaflet [lat,lng] flip):
const coords = (area_polygon.coordinates[0] as number[][]).map((p) => [p[1], p[0]]);
L.polygon(coords, { color: "#00e5c3", fillOpacity: 0.15, weight: 3 }).addTo(map);
```

User drags the box to move it and drags the corner/edge handles to resize — no mode
switch, no click-conflict. The cursor stays the normal pan hand the whole time.

A copy-paste starter with all the hooks wired (`rectRef`, `confirmRect`, `cancelRect`,
existing-polygon render, UI snippet) is in `templates/leaflet-draw-rectangle.tsx`.

## Controlled inputs with async save (no cursor jump)

When an input's value comes from a Supabase-upserted row and every keystroke triggers an async persist → re-render, the cursor resets to position 0. Fix by decoupling local state from the async save:

```tsx
const [form, setForm] = useState(() => ({ ...(loadedData ?? {}) }));
const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

const onField = (k: string, v: string) => {
  setForm((f) => ({ ...f, [k]: v }));  // immediate, cursor stays
  if (timer.current) clearTimeout(timer.current);
  const snapshot = { ...form, [k]: v };
  timer.current = setTimeout(() => {
    persist({ remarks: snapshot });  // one write after user pauses
  }, 600);
};

// Input binds to local form, NOT to the async-loaded prop
<input value={form[k] ?? ""} onChange={(e) => onField(k, e.target.value)} />
```

## Pitfalls

- **Cesium in Next.js**: the ESM build causes `\0`-in-template-literal syntax errors in production. The CDN-loaded build has race conditions with React's useEffect timing. Just use Leaflet.
- **`min-h-screen` vs `height: 100dvh`**: flex children (`flex: 1`) need a DEFINITE parent height. `min-h-screen` sets minimum, not actual height. Use `height: 100dvh` or `h-screen` on the flex container.
- **Supabase JWT rotation**: the payload looks identical but the signature fails. Get the fresh key from the dashboard, not from `.env.local`.
- **GeoJSON coordinate order**: GeoJSON is `[lng, lat]`. Leaflet is `[lat, lng]`. Always flip when rendering.
- **Globe/map paints OVER the side panels (z-index bug).** `position: absolute; inset: 0` map container with NO z-index stacks above later-in-DOM `z-index: 5` panels (remarks card, draw tools) → the map covers them. Fix: give the map container `z-index: 1` so the `z-index: 5` UI always sits above it.
- **Map never initializes because of an early `return` on loading.** If the component returns a `<Loading/>` before the map container is mounted, `containerRef` is null when the Leaflet `useEffect([])` runs → map is never created and stays blank after load completes (the effect doesn't re-run). Fix: ALWAYS mount the map container; render loading/error as OVERLAYS on top, and call `map.invalidateSize()` after load (the container may have been 0-height during init).
- **Remove don't fix**: when asked to fix a broken UI button that duplicates existing autosave behavior, comply by removing it rather than debugging it.