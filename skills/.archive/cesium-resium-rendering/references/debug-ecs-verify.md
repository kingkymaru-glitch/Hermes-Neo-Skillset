# ECEF → lon/lat verification (proves rendered geometry matches source)

Use when the viewer shows a cable and you must confirm it's at the correct coords.

```js
// in browser console, with window.__viewer exposed:
const v = window.__viewer;
const e = v.entities.values.find(x => x.id && String(x.id).startsWith('cable-marea'));
const pos = e.polyline.positions.getValue(v.clock.currentTime);
console.log('first ECEF:', pos[0].x, pos[0].y, pos[0].z);
```

Then in Node, convert ECEF (meters) → lon/lat:

```js
function ecefToLonLat(x, y, z) {
  const a = 6378137.0, f = 1/298.257223563, e2 = f*(2-f);
  const r = Math.sqrt(x*x + y*y);
  let lat = Math.atan2(z, r*(1-e2));
  for (let i=0;i<5;i++){
    const N = a/Math.sqrt(1-e2*Math.sin(lat)**2);
    lat = Math.atan2(z + e2*N*Math.sin(lat), r);
  }
  const lon = Math.atan2(y, x);
  return { lon: lon*180/Math.PI, lat: lat*180/Math.PI };
}
// MAREA source: lon -76.05 lat 36.75 (Virginia Beach) -> lon -2.94 lat 43.27 (Bilbao)
```

Expected for MAREA first point: lon ≈ -76.06, lat ≈ 36.76 (matches source → no coordinate bug).

# Kumul repro (the collapse bug, before vs after)

Source `Kumul Domestic Submarine Cable System` (submarinecablemap.com):
- 14 sub-lines (MultiLineString), e.g. branch lengths [6, 9, 17, ...] points, spanning PNG
  (lon 141–156, lat -11 to -2).

BEFORE fix (multiple Polylines in one Entity):
- `viewer.entities` had 718 cable entities, but Kumul entity exposed only
  `1 polyline with 5 points` → branches collapsed/merged. User saw "only few cables."

AFTER fix (one Entity per sub-line):
- Kumul = `14 entities`, total `81 points` across them → matches source 14 branches exactly.

Takeaway: count sub-lines per feature in BOTH the source GeoJSON and the rendered viewer;
if they diverge, you have the collapse bug, not a data problem.
