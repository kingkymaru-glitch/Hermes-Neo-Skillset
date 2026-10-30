# S22 Ultra Consumption Console (asset-drawer HUD)

The 'ultimate consumption interface' for the phone. Slides into the LEFT command
drawer (Box 2) when the selected asset is `s22-ultra`. Reads the edge stream from
`useEdgeData()` — zero Cesium/Resium imports. Click-to-select wiring + the
`S22Console` component + matching CSS, all verified green (`VITE_EDGE_MODE=android
npm run lint` 0/0, build green, `S22 ULTRA · EDGE NODE` present in the bundle).

## 1. Wire selection in `App.jsx` (the part that didn't exist)
```jsx
// state
const [selectedAsset, setSelectedAsset] = useState(null)
const { geo, liveGeo, deviceStatus, sensorPayloads } = useEdgeData()
const isS22Selected = selectedAsset?.id === 's22-ultra'
const now = useClock()   // KEEP this — <OverviewPanel now={now} /> consumes it

// <Viewer> — REAL prop (resium cesiumEventProps). Suppress default InfoBox.
<Viewer
  infoBox={false}
  selectionIndicator={false}
  onSelectedEntityChange={(entity) => {
    if (!entity) { setSelectedAsset(null); return }
    setSelectedAsset({ id: entity.id, name: entity.name })
    setDrawerOpen(true)
  }}
  /* ...existing props... */
>
  <AssetEntities assets={assets} />
</Viewer>

// every <Entity> needs an `id` so entity.id resolves:
<Entity key="s22-ultra" id="s22-ultra" position={...} ... />

// drawer branch (inside the open drawer)
{isS22Selected ? (
  <S22Console id="s22-ultra" liveGeo={liveGeo} geo={geo}
    deviceStatus={deviceStatus} sensorPayloads={sensorPayloads}
    onBack={() => setSelectedAsset(null)} />
) : drawerView === 'overview' ? (
  <OverviewPanel now={now} camPos={camPos} onSensors={openSensors}
    onChat={() => setChatOpen(true)} />
) : (
  <SensorsPanel onBack={() => setDrawerView('overview')} />
)}
```

## 2. `S22Console` component (drop inside the provider tree)
```jsx
function S22Console({ id, liveGeo, geo, deviceStatus, sensorPayloads, onBack }) {
  const fix = geo || liveGeo
  const gpsFix = !!liveGeo
  const speedKmh = liveGeo ? (liveGeo.speed * 3.6).toFixed(1) : '0.0'
  // MJPEG is a still-image stream — browsers render it via <img>, not <video>.
  const videoOk = deviceStatus?.stream
  const snapOk = deviceStatus?.snapshot
  const audioOk = deviceStatus?.audio

  return (
    <div className="s22-console">
      <header className="s22-head">
        <div className="s22-title">
          <span className={`s22-live ${gpsFix ? 'on' : 'no'}`} />
          <div>
            <h2>S22 ULTRA · EDGE NODE</h2>
            <span className="s22-sub">Mobile Spatial Anchor · {id}</span>
          </div>
        </div>
        <button className="back-btn" onClick={onBack} aria-label="Back">‹</button>
      </header>

      <section className="s22-video">
        {videoOk ? (
          <img className="s22-feed" src={deviceStatus.stream} alt="S22 live feed" />
        ) : (
          <div className="s22-feed s22-feed--off">NO VIDEO STREAM</div>
        )}
        {snapOk && (
          <a className="s22-snap" href={deviceStatus.snapshot} target="_blank" rel="noreferrer">
            <img src={deviceStatus.snapshot} alt="S22 snapshot" />
            <span>SNAP</span>
          </a>
        )}
        {audioOk && <audio className="s22-audio" src={deviceStatus.audio} controls preload="none" />}
      </section>

      <section className="s22-grid">
        <Stat label="LAT" value={fix ? fix.lat.toFixed(5) : '—'} />
        <Stat label="LON" value={fix ? fix.lon.toFixed(5) : '—'} />
        <Stat label="ALT" value={fix ? `${(fix.alt ?? 0).toFixed(1)}m` : '—'} />
        <Stat label="ACC" value={gpsFix ? `${fix.accuracy ?? 0}m` : 'NO FIX'} />
        <Stat label="SPD" value={`${speedKmh} km/h`} />
        <Stat label="NODE" value={`${deviceStatus?.ip ?? '—'}`} />
      </section>

      <section className="s22-shm">
        <h3>SENSOR TELEMETRY</h3>
        <div className="s22-channels">
          {(sensorPayloads || []).map((s) => (
            <div key={s.id} className={`s22-chan flag-${s.flag}`}>
              <span className="s22-chan-name">{s.name}</span>
              <span className="s22-chan-val">{s.value}<i>{s.unit}</i></span>
              <span className="s22-chan-flag">{s.flag}</span>
            </div>
          ))}
        </div>
      </section>

      <footer className="s22-foot">
        <span>{deviceStatus?.host}</span>
        <span>UP {formatUptime(deviceStatus?.uptimeSec || 0)}</span>
        <span>CPU {deviceStatus?.cpuLoad ?? 0}%</span>
        <span>MEM {deviceStatus?.memUsedPct ?? 0}%</span>
      </footer>
    </div>
  )
}

function Stat({ label, value }) {
  return (
    <div className="s22-stat">
      <span className="s22-stat-l">{label}</span>
      <span className="s22-stat-v">{value}</span>
    </div>
  )
}
```
`formatUptime` already exists in App.jsx (do NOT rename to `fmtUptime` — that
helper doesn't exist and will lint-fail).

## 3. CSS (reuses `--neon-*` / `--glass-*` tokens; green `#22e07a` S22 accent)
```css
.s22-console { display: flex; flex-direction: column; gap: 16px; color: var(--ink);
  font-family: 'SF Mono', ui-monospace, 'Cascadia Code', Menlo, monospace; }
.s22-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.s22-title { display: flex; align-items: center; gap: 12px; }
.s22-title h2 { margin: 0; font-size: 15px; font-weight: 800; letter-spacing: 2px; color: #fff; }
.s22-sub { font-size: 10px; letter-spacing: 1.5px; color: var(--ink-faint); text-transform: uppercase; }
.s22-live { width: 12px; height: 12px; border-radius: 50%; flex: none; transition: background .3s, box-shadow .3s; }
.s22-live.on { background: #22e07a; box-shadow: 0 0 10px #22e07a; animation: s22-blink 1.6s ease-in-out infinite; }
.s22-live.no { background: #475569; box-shadow: none; }
@keyframes s22-blink { 0%,100% { opacity: 1; } 50% { opacity: .35; } }

.s22-video { display: flex; flex-direction: column; gap: 10px; }
.s22-feed { width: 100%; aspect-ratio: 4 / 3; object-fit: cover; border-radius: 14px;
  border: 1px solid rgba(34,224,122,.35); background: #05080f;
  box-shadow: 0 0 26px rgba(34,224,122,.18); display: block; }
.s22-feed--off { display: flex; align-items: center; justify-content: center;
  color: var(--ink-faint); letter-spacing: 3px; font-size: 12px; border-style: dashed; }
.s22-snap { position: relative; display: block; width: 92px; height: 69px; border-radius: 10px;
  overflow: hidden; border: 1px solid var(--glass-border); flex: none; }
.s22-snap img { width: 100%; height: 100%; object-fit: cover; display: block; }
.s22-snap span { position: absolute; bottom: 4px; right: 4px; font-size: 8px; letter-spacing: 1px;
  padding: 1px 5px; border-radius: 5px; background: rgba(5,8,15,.8); color: var(--neon-cyan); }
.s22-audio { width: 100%; height: 34px; filter: hue-rotate(150deg); }

.s22-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.s22-stat { display: flex; flex-direction: column; gap: 3px; padding: 9px 10px; border-radius: 10px;
  background: rgba(15,23,42,.55); border: 1px solid var(--glass-border); }
.s22-stat-l { font-size: 9px; letter-spacing: 1.5px; color: var(--neon-teal); }
.s22-stat-v { font-size: 14px; font-weight: 700; color: #fff; font-variant-numeric: tabular-nums; }

.s22-shm h3 { margin: 0 0 8px; font-size: 10px; letter-spacing: 2px; color: var(--ink-faint); }
.s22-channels { display: flex; flex-direction: column; gap: 6px; }
.s22-chan { display: grid; grid-template-columns: 1fr auto auto; align-items: center; gap: 8px;
  padding: 8px 11px; border-radius: 9px; background: rgba(15,23,42,.55); border-left: 3px solid var(--neon-teal); transition: border-color .3s; }
.s22-chan-name { font-size: 11px; color: var(--ink-dim); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.s22-chan-val { font-size: 14px; font-weight: 700; color: #fff; font-variant-numeric: tabular-nums; }
.s22-chan-val i { font-style: normal; font-size: 9px; color: var(--ink-faint); margin-left: 2px; }
.s22-chan-flag { font-size: 8px; letter-spacing: 1px; text-transform: uppercase; padding: 2px 6px; border-radius: 6px; color: var(--ink-faint); }
.s22-chan.flag-nominal { border-left-color: var(--neon-teal); }
.s22-chan.flag-warning { border-left-color: #fbbf24; }
.s22-chan.flag-warning .s22-chan-flag { color: #fbbf24; }
.s22-chan.flag-alert { border-left-color: #f43f5e; animation: s22-alert 1.2s ease-in-out infinite; }
.s22-chan.flag-alert .s22-chan-flag { color: #f43f5e; }
.s22-chan.flag-alert .s22-chan-val { color: #fda4af; }
@keyframes s22-alert { 0%,100% { background: rgba(15,23,42,.55); } 50% { background: rgba(244,63,94,.16); } }

.s22-foot { display: flex; flex-wrap: wrap; gap: 10px; padding-top: 10px; border-top: 1px solid var(--glass-border);
  font-size: 9px; letter-spacing: 1px; color: var(--ink-faint); text-transform: uppercase; }
```

## Verification
```bash
VITE_EDGE_MODE=android npm run lint     # expect 0 warnings, 0 errors
VITE_EDGE_MODE=android npm run build    # green; then:
B=$(ls -t dist/assets/*.js | head -1)
grep -qo "S22 ULTRA · EDGE NODE" "$B" && echo SHIPPED || echo MISSING
rm -rf dist
```
Runtime checks the static build can't cover: click the green S22 marker → the
console must open (proves `onSelectedEntityChange` + `id` wiring); the `<img>`
feed shows live video (proves the `/s22-api` proxy serves `/video`); audio plays
only if `/audio.wav` is a browser-decoded WAV.
