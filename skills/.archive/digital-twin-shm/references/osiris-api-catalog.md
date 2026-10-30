# OSIRIS API Catalog (osiris-master)

Full inventory of OSIRIS's 56 Next.js API routes and the external endpoint each
hits. Built by scanning `src/app/api/**` + `src/lib/*` with the regex extractor
`scripts/scan-nextjs-api-endpoints.py`. Re-run that script against a fresh
osiris-master checkout to refresh this list (paths/endpoints change between
releases).

Use this when porting an OSIRIS feed into R-Tessera Box 1 or diagnosing a
dead layer. The MARU/R-Tessera adoption rule borrows OSIRIS *patterns* only —
see `references/osiris-adoption.md` and `references/osiris-layer-adoption-recipe.md`.

## Keyless public feeds (no API key) — directly adoptable by R-Tessera Box 1

### Situational / Hazard (highest Box-1 relevance)
- `/api/earthquakes`      → `earthquake.usgs.gov/.../summary/2.5_day.geojson`
- `/api/country-risk`     → `earthquake.usgs.gov/.../summary/4.5_day.geojson`
- `/api/infrastructure`   → `earthquake.usgs.gov/.../summary/4.5_day.geojson`
- `/api/weather`          → `eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=100`
                             + `www.gdacs.org/xml/rss.xml` + `api.weather.gov/alerts/active`
- `/api/fires`            → `eonet.gsfc.nasa.gov/.../category=volcanoes`
                             + `firms.modaps.eosdis.nasa.gov` MODIS C6.1 + VIIRS C2 24h CSV
- `/api/gdelt`            → `www.gdacs.org/xml/rss.xml`
- `/api/gdelt-events`     → `data.gdeltproject.org/gdeltv2/lastupdate.txt`
- `/api/news`             → `feeds.bbci.co.uk` + `aljazeera.com` + `gdacs` + `t.me/s/<channel>`
- `/api/region-dossier`   → `nominatim.openstreetmap.org/reverse`
                             + `en.wikipedia.org/api/rest_v1/page/summary`
                             + `query.wikidata.org/sparql`

### Aviation
- `/api/flights`          → `api.adsb.lol/v2/{ladd,mil,pia,point,squawk/7700}`
                             + `api.airplanes.live/v2/...`
                             + `opensky-network.org/api/states/all` (+ OAuth2 token)

### Maritime
- `/api/maritime`         → `wss://stream.aisstream.io/v0/stream` (NEEDS `AIS_API_KEY`)
                             + 39 hardcoded static ports/chokepoints (no call)

### Space
- `/api/satellites`       → `celestrak.org/NORAD/elements/gp.php?GROUP=`
                             + `celestrak.org/.../sup-gp.php?FILE=starlink`
                             + `db.satnogs.org/api/tle/`

### Cyber / Threat
- `/api/cyber-attacks`    → `feodotracker.abuse.ch/downloads/ipblocklist.json`
- `/api/malware`          → `feodotracker.abuse.ch` + `urlhaus.abuse.ch/downloads/csv_online/`
- `/api/cyber-threats`    → `dashboard.shadowserver.org` + `cisa.gov` KEV json
- `/api/osint/threats`    → `otx.alienvault.com/api/v1/...` + `check.torproject.org`

### Markets / Crypto
- `/api/crypto`           → `api.coingecko.com/api/v3/simple/price` (BTC/ETH/SOL)
- `/api/markets`          → `api.coingecko.com` + `query1/query2.finance.yahoo.com`

### Geo / IP
- `/api/geo`              → `ip-api.com` + `freeipapi.com` + `ipapi.co`
- `/api/radar`            → `api.ioda.inetintel.cc.gatech.edu/v2/` (internet outages)
- `/api/cloudflare-radar` → `api.cloudflare.com/client/v4/radar` (**NEEDS `CLOUDFLARE_API_TOKEN`**)

### Satellite imagery
- `/api/sentinel`         → `catalogue.dataspace.copernicus.eu/stac/search`
                             + `earth-search.aws.element84.com/v1/search`

### Misc
- `/api/air-quality`      → `api.openaq.org/v2/latest`
- `/api/arcgis`           → `www.arcgis.com/sharing/rest/search`
- `/api/frontlines`       → `deepstatemap.live/api/history/last`
- `/api/conflicts`        → `liveuamap.com` (13 zones) + BBC/NYT/AlJazeera RSS
- `/api/live-news`        → ~25 YouTube channel live streams
- `/api/cctv/*`           → 30+ country traffic-cam / webcam / YouTube-embed sources
                             (TfL, Caltrans, WSDOT, Digitraffic FI, SkylineWebcams, etc.)
- `/api/space-weather`    → `services.swpc.noaa.gov/json/{alerts,xray-flares,planetary-k}`

### OSINT (RECON subset — DROPPED by R-Tessera adoption rule; listed for completeness)
- `/api/osint/whois`      → `rdap.org/domain/<domain>`
- `/api/osint/dns`        → `dns.google/resolve`
- `/api/osint/certs`      → `crt.sh/?q=%25.<domain>`
- `/api/osint/cve`        → `cve.circl.lu` + `cveawg.mitre.org`
- `/api/osint/github`     → `api.github.com/users/<user>`
- `/api/osint/leaks`      → `api.xposedornot.com/v1/breach-analytics`
- `/api/osint/mac`        → `api.maclookup.app/v2/macs/<mac>`
- `/api/osint/shodan`     → `internetdb.shodan.io/<ip>`
- `/api/osint/bgp`        → `stat.ripe.net/data/as-overview`
- `/api/osint/ip`         → `ip-api.com/json/<ip>`
- `/api/osint/sweep`      → `ip-api.com/json/<ip>`
- `/api/osint/sanctions`  → `data.opensanctions.org/.../us_ofac_sdn` (CSV, keyless, 24h cache)
- `/api/osint/phone`      → LOCAL only (`google-libphonenumber`, no network call)

### AI (needs key)
- `/api/ai/analyze`, `/api/ai/briefing`, `/api/ai/overview`
  → Google Generative Language API via `@google/generative-ai`
    (host `generativelanguage.googleapis.com`, not hardcoded in repo).
    Auth: `GEMINI_API_KEY_1..N` env OR `x-gemini-key` request header.

## Needs key / external backend
- `cloudflare-radar`  → `CLOUDFLARE_API_TOKEN`
- `maritime`          → `AIS_API_KEY` (WebSocket)
- `scanner`           → `SCANNER_URL`/`SCANNER_KEY` (separate scanner backend, `/scan/*`)
- `ai/*`              → `GEMINI_API_KEY_*`
- `entity/expand`     → `osiris-intel:4000` container (`/resolve`)
- `github-webhook`    → `GITHUB_WEBHOOK_SECRET` + `GITHUB_WEBHOOK_FORWARD_URL`

## Internal-only (no external network call)
- `/api/health`            → static status object
- `/api/stats`             → fans out to local `/api/*` with per-route revalidate TTLs
- `/api/sdk/ingest`        → in-memory Polybolos SDK entity store (needs `SDK_INGEST_KEY`)
- `/api/sdk/stream`        → SSE stream of that store
- `/api/proxy-tiles`       → `cartocdn.com` only (domain-locked tile proxy)
- `/api/cctv/proxy`        → internal CCTV proxy
- `/api/cctv/stream-status`→ internal
- `/api/scm-suppliers`     → fans out to local `/api/fires` + `/api/gdelt` + USGS
- `/api/osint/phone`       → local libphonenumber lookup

## Architecture notes (useful when porting)
1. **Keyless by design.** README + `.env.example` confirm the app runs with zero
   keys; only SCANNER/CLOUDFLARE/GEMINI are consumed by code. Everything situational
   (USGS/EONET/FIRMS/GDACS/GDELT) is keyless — the exact adoption profile for Box 1.
2. **Dedup / cache discipline** (the pattern MARU already borrowed):
   - `/api/stats` fans out to all heavy routes with per-route `revalidate` TTLs
     (flights 45s, weather 300s, gdelt 300s, satellites 3600s, cctv 3600s, infra 86400s)
     so 10k users hit upstream only once per window.
   - `src/lib/stealthFetch.ts` = drop-in `fetch()` with timeout/UA/retry.
   - `src/lib/ssrf-guard.ts` canonicalises + resolves hostnames before fetch (blocks
     `169.254.169.254`, `::1`, decimal-IP SSRF bypasses).
3. **Box 1 already adopts a subset**: USGS 2.5_day, EONET open events, and the
   viewport-aware + `TILE_FETCHED_AT` dedup guard (from `egressDrivers.js`).
   FIRMS is EXCLUDED in MARU (needs key) even though OSIRIS uses the keyless FIRMS CSV.
4. **RECON** (whois/dns/cve/sanctions/shodan/mac/leaks) is the OSIRIS part the
   R-Tessera adoption rule DROPS — MARU's RECON is UI-only scouting links.
