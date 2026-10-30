# Submarine Cable Layer — Verification Recipe (G33/G34/G38/G39)

Source: submarinecablemap.com `cable-geo.json` (718 MultiLineString features).
Keyless, CORS-free: bundle into `public/submarine-cables.json` and `fetch('/submarine-cables.json')`.

## Verified-good render rules (R-Tessera, final state)
- ONE `<Entity>` per cable. Inside, map each sub-line (MultiLineString = array of point-arrays) to ONE `<PolylineGraphics>` with `positions` = that sub-line's points. NOT per-segment entities.
- Key + Cesium `id` = `cable-${properties.feature_id || properties.id || name}` (feature_id is unique 718/718; properties.id has 21 dups → collision drops routes).
- NO lat/lon swap: GeoJSON is `[lon,lat]`; `Cartesian3.fromDegrees(lon, lat, 0)` — pass straight through.
- Height 0 (source-verbatim). No `clampToGround` (vanishes over ocean).
- Click: `ScreenSpaceEventHandler` on `viewer.scene.canvas`, `viewer.scene.pick(click.position)`, resolve by `obj.id.id`.

## Coordinate sanity check (catches G33 mirror bug)
From raw GeoJSON, known cables must land in these ranges:
- FEA: lon 32.5-100.6, lat 4.4-30.0 (Egypt/Red Sea to SE Asia)
- MAREA: lon -76.1..-2.9, lat 36.8-46.6 (Virginia Beach to Bilbao)
- JUPITER: lon spans -180..180, lat 14-45 (US to Japan to Europe)
If a transatlantic cable shows latitude ~ -76 (South Pacific), you swapped [lon,lat]->[lat,lon].

## Viewer introspection (G38 — decisive, do this BEFORE more code changes)
Temporarily in the useCesium bridge: `if (typeof window !== 'undefined') window.__viewer = viewer`. Then browser console:
```
const v=window.__viewer;
const cables=v.entities.values.filter(e=>String(e.id).startsWith('cable-'));
let nan=0; for(const e of cables){const p=e.polyline.positions.getValue(v.clock.currentTime); for(const q of p) if(isNaN(q.x)||isNaN(q.y)||isNaN(q.z))nan++;}
const m=v.entities.getById('cable-marea-0');
const pos=m.polyline.positions.getValue(v.clock.currentTime);
console.log({count:cables.length, mode:v.scene.mode, nan, first:pos[0], last:pos[pos.length-1]});
```
ECEF to lon/lat (Node, WGS84):
```
function ecef2ll(x,y,z){const a=6378137,e2=8.1819190842622e-2;const r=Math.sqrt(x*x+y*y);
 let lat=Math.atan2(z,r*(1-e2));for(let i=0;i<8;i++){const N=a/Math.sqrt(1-e2*Math.sin(lat)**2);const h=r/Math.cos(lat)-N;lat=Math.atan2(z,r*(1-e2*N/(N+h)));}
 return [Math.atan2(y,x)*180/Math.PI, lat*180/Math.PI];}
```
If `count===718`, `nan===0`, and MAREA's first/last ECEF convert to ~(-76.06,36.76)/(-2.95,43.27) -> CODE IS CORRECT. The user is seeing a STALE CACHE (G39): hard-refresh, compare live build hash `curl -s https://<site>/ | grep assets/index-` to your local `npm run build` hash.

## Region count comparison (NOT a visual-fidelity proof — G36)
Counting features touching a bbox (e.g. Singapore/Malaysia) only proves DATA parity, not that the render looks right. R-Tessera 718 vs OSIRIS 717 — R-Tessera has MORE (OSIRIS is a Jul-30 snapshot). Use counts to answer "are cables missing from data?", never to answer "why does it look sparse?" (that's projection + visibility, G36/G37).
