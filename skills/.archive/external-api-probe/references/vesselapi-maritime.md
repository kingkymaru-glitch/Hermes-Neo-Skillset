# VesselAPI — Maritime AIS feed (from MARU my-digital-twin)

Endpoint (GET):
  https://api.vesselapi.com/v1/location/vessels/bounding-box

Query params (discrete, NOT nested JSON):
  filter.latBottom, filter.lonLeft, filter.latTop, filter.lonRight
  time.from, time.to            # lookback window bounds (ISO8601, `…Z` form)

Auth:  Authorization: Bearer <VITE_VESSEL_API_KEY>   (key in .env, gitignored)

## Hard limits
- Total span cap of 4°: |dLat| + |dLon| ≤ 4. A box spanning whole peninsular MY (~11°)
  returns HTTP 400. Tile into ≤4°-span boxes. Johor→Penang = 4 tiles:
    A Johor S   [1.0, 4.0, 100.5, 101.5]
    B Penang NW [3.5, 6.5, 100.5, 101.5]
    C Malacca E [1.0, 4.0, 101.5, 102.5]
    D NE        [3.5, 6.5, 101.5, 102.5]
- Time window ceiling = 4h. Larger → 400.

## Response envelope
Read `data` first, then `vessels`, then bare array:
  list = json.data ?? json.vessels ?? (json if Array)
Vessel fields: latitude, longitude, vessel_name, mmsi (or imo), course/cog,
  speed/sog, destination (often absent).

## Nature: HISTORICAL PING ARCHIVE, not a live tracker
- bounding-box WITHOUT time params → 200 but 0 records (no "current" concept).
- `/location/vessels/current` → 404. `/location/vessels` → 404.
- `include=current` flag → 400 (param rejected).
- No OpenAPI/swagger/docs exposed (all 404).
Answer: "which ships pinged in this box in the last N hours" — NOT "ships on water now."
Live map (MarineTraffic) shows positions NOW → will show more dots than this feed in quiet
corners (e.g. Penang/tile B). That is a semantics gap, not a defect. Data IS authentic
(real MMSIs / vessel names).

## Known-good Python probe (mirrors the JS app's request exactly)
```python
import re, json, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta

key = None
with open("/Users/kamarulhk/my-digital-twin/.env") as f:
    for line in f:
        m = re.match(r"\s*VITE_VESSEL_API_KEY\s*=\s*(.+?)\s*$", line)
        if m:
            key = m.group(1).strip().strip('"').strip("'"); break

WH = 4
now = datetime.now(timezone.utc)
past = now - timedelta(hours=WH)
def z(dt): return dt.strftime('%Y-%m-%dT%H:%M:%S.') + f"{dt.microsecond//1000:03d}Z"  # JS toISOString() form

tiles = {"A":(1.0,4.0,100.5,101.5),"B":(3.5,6.5,100.5,101.5),
         "C":(1.0,4.0,101.5,102.5),"D":(3.5,6.5,101.5,102.5)}
for n,(la,lt,lo,lr) in tiles.items():
    q = (f"filter.latBottom={la}&filter.lonLeft={lo}&filter.latTop={lt}"
         f"&filter.lonRight={lr}&time.from={z(past)}&time.to={z(now)}")
    url = f"https://api.vesselapi.com/v1/location/vessels/bounding-box?{q}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
        arr = data.get("data") or data.get("vessels") or (data if isinstance(data,list) else [])
        seen = {v.get("mmsi") for v in arr if isinstance(v,dict)}
        print(n, r.status, "records", len(arr), "distinct", len(seen))
    except urllib.error.HTTPError as e:
        print(n, e.code, e.read().decode()[:200])
```

## Through Vite proxy (app path)
App hits `/api-vessel/v1/location/vessels/bounding-box` (vite.config proxy → api.vesselapi.com).
Terminal probes above hit the API directly (key from .env) — equivalent result, bypasses CORS.
