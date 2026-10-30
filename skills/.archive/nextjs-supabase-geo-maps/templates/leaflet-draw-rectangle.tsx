// Copy-paste starter: Leaflet draggable-rectangle area selection in a React
// component that loads Leaflet from CDN. Replaces the broken click-to-add-point
// pattern (Leaflet's pan-drag eats the click). Drop a box, user drags/resizes,
// Confirm reads getBounds() -> closed GeoJSON ring.
//
// Assumes:
//   - containerRef:   ref to the map <div>
//   - mapRef:        ref to the Leaflet map instance
//   - rectRef:       ref to the current draft L.rectangle (or null)
//   - site:          { center_lon, center_lat } | null  (the pin)
//   - persist(patch): saves { area_polygon, center_lon, center_lat } to backend
//   - mapReady:      boolean set true after L.map() init

const rectRef = useRef<any>(null);
const [drawMode, setDrawMode] = useState(false);
const [error, setError] = useState<string | null>(null);

// Drop box when draw mode turns on; remove it when off.
useEffect(() => {
  const map = mapRef.current;
  const L = (window as any).L;
  if (!map || !L || !mapReady) return;
  if (drawMode) {
    if (rectRef.current) { map.removeLayer(rectRef.current); rectRef.current = null; }
    const c = site?.center_lat != null
      ? [site.center_lat, site.center_lon as number]
      : map.getCenter();
    const span = 0.004; // ~400m at equator; tune to your scale
    rectRef.current = L.rectangle(
      [[c[0] - span, c[1] - span], [c[0] + span, c[1] + span]],
      { color: "#00e5c3", weight: 3, fillOpacity: 0.15, draggable: true },
    ).addTo(map);
  } else if (rectRef.current) {
    map.removeLayer(rectRef.current);
    rectRef.current = null;
  }
}, [drawMode, mapReady, site?.center_lon, site?.center_lat]);

const confirmRect = useCallback(() => {
  const rect = rectRef.current;
  if (!rect) { setError("Start the area tool first to drop a box."); return; }
  const b = rect.getBounds();
  const sw = b.getSouthWest();
  const ne = b.getNorthEast();
  const ring: [number, number][] = [
    [sw.lng, sw.lat], [ne.lng, sw.lat], [ne.lng, ne.lat], [sw.lng, ne.lat], [sw.lng, sw.lat],
  ];
  const polygon = { type: "Polygon" as const, coordinates: [ring] };
  const lon = (sw.lng + ne.lng) / 2;
  const lat = (sw.lat + ne.lat) / 2;
  setDrawMode(false);
  if (rectRef.current) { mapRef.current?.removeLayer(rectRef.current); rectRef.current = null; }
  persist({ area_polygon: polygon, center_lon: lon, center_lat: lat });
}, [persist]);

const cancelRect = useCallback(() => {
  setDrawMode(false);
  if (rectRef.current) { mapRef.current?.removeLayer(rectRef.current); rectRef.current = null; }
}, []);

// Render an EXISTING saved polygon (GeoJSON [lng,lat] -> Leaflet [lat,lng]).
useEffect(() => {
  const map = mapRef.current;
  const L = (window as any).L;
  if (!map || !L || !site?.area_polygon) return;
  const coords = (site.area_polygon.coordinates[0] as number[][]).map((p) => [p[1], p[0]]);
  L.polygon(coords, { color: "#00e5c3", fillOpacity: 0.15, weight: 3 }).addTo(map);
}, [site?.area_polygon]);

// UI (owner only):
//   {!drawMode
//     ? <button onClick={() => setDrawMode(true)}>Mark area of works</button>
//     : (<>
//         <span>Drag the box to move · drag edges to resize</span>
//         <button onClick={confirmRect}>Confirm area</button>
//         <button onClick={cancelRect}>Cancel</button>
//       </>)}
