# Open-Meteo keyless Global Weather layer (R-Tessera Box 2)

Verified-working recipe for a KEYLESS ambient weather overlay on the Cesium globe.
Used by `WeatherEntities.jsx` (added 2026-08-07). No API key, no signup.

## Why Open-Meteo
- Fully keyless (no token header, no quota key). CORS-enabled for browser fetch.
- Two endpoints, same param shape:
  - Point forecast: `https://api.open-meteo.com/v1/forecast`
  - Marine (wave height/dir/period): `https://marine-api.open-meteo.com/v1/marine`
- Returns a JSON object (single coord) OR a JSON **array** (multiple coords) — see below.

## Batched multi-station call (the key trick)
Open-Meteo accepts comma-separated `latitude`/`longitude` lists and returns an
ARRAY of per-station objects in the SAME order. One request for all stations:

```
GET https://api.open-meteo.com/v1/forecast
  ?latitude=51.5074,1.3521,-33.8688
  &longitude=-0.1278,103.8198,151.2093
  &current=temperature_2m,wind_speed_10m,weather_code
  &timezone=GMT
```

Response: `[ {current:{...}}, {current:{...}}, {current:{...}} ]` — index-aligned
with the input station list. Map `WEATHER_STATIONS[i]` → `list[i].current`.

Live check (verified 2026-08-07): returns London 23.4°C code 0 + Singapore next,
HTTP 200.

## Station list shape
```js
export const WEATHER_STATIONS = [
  { id: 'lon', name: 'London', lat: 51.5074, lon: -0.1278 },
  // ... curated major ports/cities so the globe reads globally
]
```

## Driver skeleton (egressDrivers.js)
```js
const WMO_LABEL = { 0:'Clear', 1:'Mainly clear', 2:'Partly cloudy', 3:'Overcast',
  45:'Fog', 48:'Rime fog', 51:'Light drizzle', 53:'Drizzle', 55:'Dense drizzle',
  61:'Light rain', 63:'Rain', 65:'Heavy rain', 71:'Light snow', 73:'Snow',
  75:'Heavy snow', 80:'Rain showers', 81:'Showers', 82:'Violent showers',
  95:'Thunderstorm', 96:'Thunderstorm + hail', 99:'Severe thunderstorm' }

function stationToEvent(st, cur) {
  const temp = Number(cur?.temperature_2m)
  const wind = Number(cur?.wind_speed_10m)
  const code = Number(cur?.weather_code)
  return {
    id: `wx-${st.id}`, kind: 'weather', lon: st.lon, lat: st.lat, name: st.name,
    tempC: temp, windKph: wind, code: Number.isFinite(code) ? code : null,
    label: `${st.name} · ${Number.isFinite(temp) ? `${Math.round(temp)}°C` : '—'} · ${Number.isFinite(code) ? WMO_LABEL[code] : ''}`,
  }
}

export async function fetchWeather() {
  try {
    const res = await fetch(buildUrl(WEATHER_STATIONS, false))
    if (!res.ok) throw new Error(`Open-Meteo ${res.status}`)
    const json = await res.json()
    const list = Array.isArray(json) ? json : [json]
    return { events: WEATHER_STATIONS.map((st, i) => stationToEvent(st, list[i]?.current)).filter(Boolean), error: null }
  } catch (error) {
    const message = error instanceof TypeError
      ? 'Network error — cannot reach Open-Meteo (check connection / DNS).'
      : error?.message || 'Weather feed request failed.'
    return { events: [], error: { code: 'WEATHER_OFFLINE', message } }
  }
}
```

`buildUrl` joins station lat/lon with commas and sets `current=...` per endpoint.

## Hook (useFeeds.js)
```js
export function useWeather() {
  const { data, error, isLoading, isFetching } = useQuery({
    queryKey: ['weather'], queryFn: fetchWeather,
    staleTime: TEN_MIN, refetchInterval: TEN_MIN,
    placeholderData: { events: [], error: null },
  })
  return {
    events: data?.events ?? [],
    error: data?.error ?? (error ? { code: 'QUERY_ERROR', message: error.message } : null),
    isLoading, isFetching,
  }
}
```
NOTE: oxlint flags an unused destructure binding — only pull `{ events, error }`
from `useWeather()` in the component (drop `isLoading` unless rendered).

## Entity render + HUD (WeatherEntities.jsx)
- Pin = `<Entity position={Cartesian3.fromDegrees(lon,lat,0)} heightReference={CLAMP_TO_GROUND}>`
  with `<PointGraphics>` + `<LabelGraphics>` (reuse the SituationalEntities pattern).
- Color by temp: cold blue → cyan → green → amber → hot red (see `tempColor()`).
- Click → `ScreenSpaceEventHandler` LEFT_CLICK pick; `id` starts with `wx-`.
- HUD shows temp / wind / WMO condition; OFFLINE error badge on `connError`.
- When `showWeather` is false → `return null` (zero entities, zero pollers).

## Map Control wiring (MapControlPanel.jsx)
- Add `useWeather()` to the panel, compute `wxCount = showWeather ? qWx.events.length : 0`.
- Add a `<Row id="weather" label="Global Weather" active={showWeather} count={wxCount} onToggle={...} />`.
- It is NOT key-gated — always enabled (unlike Maritime).

## App.jsx
- `const [showWeather, setShowWeather] = useState(false)`
- `<WeatherEntities showWeather={showWeather} />` inside `<Viewer>`.
- Pass `showWeather`/`setShowWeather` to `<MapControlPanel>`.

## open-meteo marine variant (NOT yet used)
Swap base to `marine-api.open-meteo.com/v1/marine` and `current=wave_height,
wave_direction,wave_period` to render wave state at coastal stations. Same
array-response shape. Left as a future extension — keep keyless.
