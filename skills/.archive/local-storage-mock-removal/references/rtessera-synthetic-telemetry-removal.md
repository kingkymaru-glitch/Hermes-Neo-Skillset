# R-Tessera synthetic telemetry removal — exact symbol/file map

Target: `~/my-digital-twin` (Vite + React + CesiumJS; branded MARU / R-Tessera).
Class: CesiumJS dashboard that synthesizes a telemetry stream when no real edge
hardware is connected. "Remove all mock data" here = kill the synthetic stream
AND the Demo Sensors authoring feature.

## Mock surface inventory (discovered 2026-08-01)

### src/context/EdgeDataContext.jsx  (the synthetic engine)
- `MOCK_SENSOR_TYPES` — the 8-type demo sensor registry (temp/humidity/aqi/wind/
  strain/tilt/rms/crack), each with baseline/spread/driftBias for a lively sim.
- `MOCK_TYPE_MAP` — `Object.fromEntries(MOCK_SENSOR_TYPES...)`.
- `MAX_SLOTS = 3` — placements per type (A/B/C).
- `seedSensors()` — seeds 4 real-named channels (Tilt/Strain/Vibration/Temp)
  geo-tagged to EDGE_ANCHOR. THE base synthetic telemetry.
- `tickSensors(prev)` — jitters each channel, classifies flag by THRESHOLDS.
- `bootDeviceStatus()` — mock defaults (host 'edge-sim.local', ip '127.0.0.1').
- `const [mockSensors, setMockSensors] = useState([])` + `addMockSensor` /
  `removeMockSensor` / `clearMockSensors`.
- `historyRef` + `getMockSeries(id)` — rolling mini time-series for the sparkline.
- `placement` / `setPlacement` — opt-in "drop on map" mode for authoring.
- `const allSensors = [...sensorPayloads, ...mockSensors]` — combined feed.
- Second `useEffect` — jitters mockSensors on the poll cadence.
- `EDGE_MODE === 'mock'` branch in the poll loop (pure synthetic).
- Exported `MOCK_MAX_SLOTS = MAX_SLOTS`.
- `connection` initial state `'mock'`; `value` exposes mockSensors, addMockSensor,
  removeMockSensor, clearMockSensors, getMockSeries, MOCK_TYPES, MOCK_MAX_SLOTS,
  placement, setPlacement.

### src/App.jsx  (ACTUAL 2026-08-17 map — the 2026-08-01 list MISSED these)
The original inventory listed a few sites, but the real half-applied refactor left
dangling references at ALL of the following. Grep each before claiming done:
- `SETTING_ITEMS` entry `{ key: 'demo', label: 'Demo Sensors', ... }` — removed OK.
- `DemoSensorsPanel()` function (the authoring UI) — must be deleted entirely.
- `useEdgeData()` destructure at App.jsx:943 pulling `placement, setPlacement,
  addMockSensor, mockSensors, MOCK_SENSOR_TYPES, MAX_SLOTS` → all gone from context.
- `handleMapPick` at App.jsx:1206-1214 — `if (placement)` block calls
  `addMockSensor(...)`, `setPlacement(null)`; remove the whole intercept.
- Placement banner at App.jsx:1529-1543 — `placement && (() => { const t =
  MOCK_SENSOR_TYPES.find(...); const placed = mockSensors.filter(...); ...MAX_SLOTS })
  ()}` → delete the whole block.
- `AssetEntities` at App.jsx:1976 destructures `mockSensors`; App.jsx:2002-2015
  `.map((m) => <Entity ...>)` over `mockSensors` → delete the iteration.
- `MOCK_CHAT` seed at App.jsx:~1014 — delete the const + any `ChatPanel` use.
- `DEMO_ASSETS` (3 fake sensors A/B/C) + every `setAssets(DEMO_ASSETS)` fallback
  in `loadAssets()` (the graceful-degradation fallback) → replace with empty array.
- `connLabel` includes `'Simulated Feed'` for the mock connection state.
- Inline comments referencing "demo sensor placement" / "demo-authored mock
  sensors" (App.jsx:824, 1200-1201, 1972-1973) — clean up stale doc strings.

**Trap:** the 2026-08-01 list omitted the `handleMapPick` intercept, the
`AssetEntities` `mockSensors.map`, and the `placement` banner. Those three are what
make the half-stripped app crash at runtime even though `npm run build` is green
(undefined-destructure trap — see `vite-build-verification`). Always grep, never
trust the partial inventory.

### src/App.css
- `.demo-author`, `.demo-grid`, `.demo-card`, `.demo-swatch`, `.demo-slots`,
  `.demo-slot`, `.demo-card-actions`, `.demo-drop`, `.demo-coord*`, `.demo-input`,
  `.demo-clear`, `.demo-err`, `.placement-*`, and `.dt-edge.edge-mock`.

### src/supabaseClient.js
- Comment: "leave it null so the app can gracefully fall back to seeded demo
  data instead of throwing at import time." (cosmetic; update wording.)

## KEEP (NOT mock — do not delete)
- `sensorPayloads` driven by a real `VITE_EDGE_API_URL` fetch or `android` node
  (iPhone/S22 GPS fix). That is live data.
- `nodesService` localStorage fallback for user-authored map Nodes — durable
  offline storage, not demo data (unless Scope C).

## Verification (build-green is NOT enough)
- `npm run build` green.
- **Grep zero matches** for every removed identifier across `src/`:
  `mockSensors|MOCK_SENSOR_TYPES|DemoSensorsPanel|seedSensors|tickSensors|
  getMockSeries|MOCK_CHAT|DEMO_ASSETS|placement` (also `MAX_SLOTS`,
  `addMockSensor`, `removeMockSensor`). A remaining reference = a guaranteed
  runtime crash (undefined-destructure), which the build does NOT catch.
- Manual/render check: with no `VITE_EDGE_MODE`/`VITE_EDGE_API_URL` set, the
  dashboard shows no sensor channels (empty until real hardware connects) AND the
  map does not throw on render (no `Cannot read .map of undefined`).
- If any consuming component still destructures a removed context property, fix
  that component too — the build will stay green otherwise.
