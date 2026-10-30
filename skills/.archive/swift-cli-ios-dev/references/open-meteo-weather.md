# Open-Meteo key-free weather (iOS / Swift)

Reusable pattern for fetching real weather in an iOS app with NO API key. Came up
in the AnglerGO Calendar rework (Task C) where all-weather data was previously hardcoded.

## Endpoint
`https://api.open-meteo.com/v1/forecast?latitude=..&longitude=..&daily=..&hourly=..&timezone=auto`
No key, no `Authorization`/`X-API` header. If you ever see `?key=` in the URL, you
are using the wrong (paid) provider — Open-Meteo is public.

## Typical request params
- daily: `weather_code,temperature_2m_max,temperature_2m_min,wind_speed_10m_max`
- hourly: `temperature_2m,wind_speed_10m,wind_direction_10m,weather_code`
- `timezone=auto` so the API returns local-day arrays for the requested coordinate.

## Decode defensively (key lesson)
Mirror Open-Meteo's nested `daily`/`hourly` shape with Codable structs whose every
field is Optional (`let wind_speed_10m_max: [Double]?`). Then pull values with
optional binding. This way a missing field degrades gracefully instead of crashing
the decode (and the whole fetch). There is no guaranteed field order, so never assume.

## Derived fields worth computing locally
- **Dominant wind direction**: Open-Meteo returns an hourly `wind_direction_10m`
  array. Pick the direction at the hour of MAX `wind_speed_10m` (argmax), not a
  "mostFrequent" helper. Then map degrees to a 16-point compass label
  (`N,NNE,NE,...`) for display.
- **Weather symbol/label**: map WMO `weather_code` to SF Symbol + text
  (0 clear to `sun.max.fill`, 95 thunder to `cloud.bolt.rain.fill`, etc.).
- **Moon phase**: astronomical, computed from a known new-moon epoch + synodic
  period. Not from the weather API.

## Tide: there is no good key-free source
Open-Meteo has a *marine* API but it is sparse/station-limited. Until a keyed tide
provider (StormGlass, WorldTides24/7) is added, ship a CLEARLY-LABELED estimate:
a semi-diurnal curve from a couple of station constants (mean range, diurnal
inequality) modulated by moon phase, then pick next high/low after the selected
time. Label the card "Tide (est.)" and label derived wave height as "(est.)" so it
is never presented as measured.

## UI integration (when no Xcode build is available)
- `@State weather: MarineWeather?`, `@State weatherLoading`, `@State weatherError`.
- `.task(id: <date|location>)` to auto-reload on change; `.refreshable` for manual retry.
- Set an estimated baseline immediately so cards are never empty; replace with live
  data on success; on failure keep the estimate and show a "Retry" button + error string.
- This is AD-HOC behavior, not a compiled check — real confirmation needs Xcode + simulator.

## Marine API + "Experience Readiness" scoring (Task 7C, AnglerGO "Suasana" trigger)
Open-Meteo's **marine** API is ALSO key-free — used it to replace the labeled tide estimate
with REAL tide once available, and to derive a go/no-go score. Pattern:
- **Weather current**: `https://api.open-meteo.com/v1/forecast?latitude=..&longitude=..&current=temperature_2m,weather_code,wind_speed_10m,is_day&timezone=auto`
- **Marine current + hourly tide**: `https://marine-api.open-meteo.com/v1/marine?latitude=..&longitude=..&current=wave_height&hourly=tide_height&timezone=auto`
- Two separate `URLSession` calls. Wrap the marine call in `do/catch` and on failure FALL BACK
  to (a) wave estimated from wind (`max(0.1, wind/25.0)`) and (b) the local semi-diurnal tide
  estimate. The weather call is required; a weather failure should abort the whole fetch.
- **Tide extrema from hourly `tide_height`**: parse `time`/`tide_height` arrays → find local
  maxima/minima (peak higher than both neighbors) → `nextOrNearest` = first future extreme, else
  the nearest overall. Pick the current height as the series point closest to `now`. This gives
  "next high tide 14:32" without a tide-provider key.
- **Readiness score (0-100)**: weighted blend → weather 40 / wind 30 / wave 20 / daylight 10.
  - weather: WMO code buckets (0-3 clear→100, fog 60, drizzle/rain 30, snow 20, storm 25).
  - wind: <15 →100, <25 →60, else 20. wave: <1.0→100, <2.0→60, else 20.
  - daylight: `is_day==1` →100, night →40.
  - Bands: 85+ "Optimal", 65+ "Good", 40+ "Fair", else "Poor".
- **Graceful degradation is a feature, not a fallback**: every external failure hides the
  readiness banner (never crashes). Use `do/catch` per-source; decode with Optionals; never force-unwrap.
- **Date parsing gotcha**: Open-Meteo returns `yyyy-MM-dd'T'HH:mm` in the requested tz (`timezone=auto`).
  Parse with a `DateFormatter` (`dateFormat="yyyy-MM-dd'T'HH:mm"`, no seconds). Display back in the
  same formatter so round-trips are consistent; exact cross-tz math is an edge case, not worth solving here.
- Verify the pure scoring + extrema logic with an executable mirror test (multi-line Swift, no
  ternary-as-statement) — the network/`Decodable` layer only runs in Xcode. See `swift-cli-ios-dev`.
