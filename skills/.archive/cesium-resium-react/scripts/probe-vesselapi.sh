#!/usr/bin/env bash
# Probe the live VesselAPI maritime feed through the SAME Vite dev proxy the app
# uses, to explain why the map shows N markers for M returned records.
#
# WHY THIS EXISTS: resium <Entity id> dedup (skill G25) collapses each vessel's
# historical AIS pings (the 4h time window returns PINGS, not a current snapshot)
# into ONE marker per distinct mmsi. So 20 records across 2 vessels -> 2 markers.
# This script counts records vs distinct mmsi vs valid coords so you can SEE that
# the "few markers" is correct dedup, NOT a render/normalizer bug.
#
# PREREQS: dev server on :5174 running, .env with VITE_VESSEL_API_KEY present.
# USAGE:   bash scripts/probe-vesselapi.sh   (run from the my-digital-twin repo root)
set -euo pipefail

# CORRECT .env extraction: `source <(...)` spawns a subshell that does NOT export
# into the child `curl`'s env -> spurious HTTP 401. Use grep|cut so the key lives
# in THIS shell.
KEY=$(grep '^VITE_VESSEL_API_KEY=' .env | cut -d= -f2-)
if [ -z "$KEY" ]; then echo "VITE_VESSEL_API_KEY not found in .env" >&2; exit 1; fi

# Port Klang box at the 4deg-span cap + 4h window (mirrors egressDrivers.js).
Q=$(python3 -c "
import urllib.parse, datetime
now = datetime.datetime.now(datetime.timezone.utc)
past = (now - datetime.timedelta(hours=4)).strftime('%Y-%m-%dT%H:%M:%SZ')
now = now.strftime('%Y-%m-%dT%H:%M:%SZ')
print(urllib.parse.urlencode({
  'filter.latBottom':'2.0','filter.lonLeft':'100.5',
  'filter.latTop':'4.0','filter.lonRight':'102.5',
  'time.from':past,'time.to':now}))
")
URL="http://localhost:5174/api-vessel/v1/location/vessels/bounding-box?$Q"
echo "GET $URL"
curl -s "$URL" -H "Authorization: Bearer $KEY" -o /tmp/va_probe.json -w "HTTP %{http_code}\n"

python3 - <<'PY'
import json
d = json.load(open('/tmp/va_probe.json'))
arr = d.get('vessels') or d.get('data') or []
print(f"records: {len(arr)}  envelope keys: {list(d.keys())}")
m = {}
ok = bad = 0
for x in arr:
    lat, lon = x.get('latitude'), x.get('longitude')   # CORRECT keys
    if isinstance(lat,(int,float)) and isinstance(lon,(int,float)) and abs(lat)<90 and abs(lon)<180:
        ok += 1
        e = m.setdefault(x.get('mmsi'), {'name':x.get('vessel_name'),'pings':0,'pos':set()})
        e['pings'] += 1
        e['pos'].add((round(lat,3), round(lon,3)))
    else:
        bad += 1
print(f"valid coords: {ok}/{len(arr)}  invalid: {bad}")
print(f"DISTINCT vessels (by mmsi): {len(m)}  <- markers you'll see after G25 dedup")
for k,v in m.items():
    print(f"  mmsi={k} {v['name']} pings={v['pings']} positions={len(v['pos'])}")
print("NOTE: real field names are vessel_name / latitude / longitude; there is NO 'destination' field.")
PY
