# Layer 2 → Layer 1 UI: consuming `useEdgeData()` in the Box 2 drawer

Copy-paste recipe for wiring the decoupled edge stream (see `edge-data-layer.md`)
into a visible dashboard panel. Used by the `SensorsPanel` ("Sensor Clusters")
deep-dive inside the left command drawer. Zero Cesium/Resium imports — the
component only knows about `useEdgeData()`.

## Component pattern (`SensorsPanel`)

```jsx
import { useEdgeData } from './context/EdgeDataContext'

function SensorsPanel({ onBack }) {
  const { connection, sensorPayloads, deviceStatus } = useEdgeData()

  const connLabel =
    connection === 'live' ? 'Live Edge'
      : connection === 'offline' ? 'Edge Offline'
        : 'Simulated Feed'

  return (
    <>
      <button className="back-btn" onClick={onBack}>← Back to Overview</button>

      <header className="cmd-header sub">
        <h2 className="cmd-subtitle">Sensor Clusters</h2>
        <span className={`shm-conn conn-${connection}`}>
          <i className="shm-conn-dot" />
          {connLabel}
        </span>
      </header>

      {/* 4 live SHM channels. Color/animation is driven ENTIRELY by s.flag
          from the data layer — do NOT re-evaluate thresholds here. */}
      <div className="shm-list">
        {sensorPayloads.map((s) => (
          <div key={s.id} className={`shm-row flag-${s.flag}`}>
            <span className="shm-dot" />
            <span className="shm-name">{s.label}</span>
            <span className="shm-value">
              {s.value.toFixed(1)}<em className="shm-unit">{s.unit}</em>
            </span>
            <span className="shm-flag">
              {s.flag === 'alert' ? 'ALERT' : s.flag === 'warning' ? 'WARN' : 'NOM'}
            </span>
          </div>
        ))}
      </div>

      {/* Edge Gateway diagnostics sub-panel (deviceStatus) */}
      <section className="gateway-panel">
        <header className="gateway-head">
          <h3>Edge Gateway</h3>
          <span className={`gw-online ${deviceStatus.online ? 'on' : 'off'}`}>
            {deviceStatus.online ? 'ONLINE' : 'OFFLINE'}
          </span>
        </header>
        <div className="gw-host">{deviceStatus.host} · {deviceStatus.ip}</div>

        <Gauge label="CPU Load" value={deviceStatus.cpuLoad} />
        <Gauge label="Memory Used" value={deviceStatus.memUsedPct} />
        <div className="gw-row">
          <span className="gw-label">Uptime</span>
          <span className="gw-value">{formatUptime(deviceStatus.uptimeSec)}</span>
        </div>
      </section>
    </>
  )
}

function Gauge({ label, value }) {
  const pct = Math.max(0, Math.min(100, value))
  const state = pct >= 90 ? 'alert' : pct >= 70 ? 'warn' : 'ok'
  return (
    <div className={`gw-row gw-gauge ${state}`}>
      <span className="gw-label">{label}</span>
      <span className="gw-value">{value.toFixed(0)}%</span>
      <span className="gw-track"><i style={{ width: `${pct}%` }} /></span>
    </div>
  )
}

function formatUptime(sec) {
  const d = Math.floor(sec / 86400)
  const h = Math.floor((sec % 86400) / 3600)
  const m = Math.floor((sec % 3600) / 60)
  if (d > 0) return `${d}d ${h}h`
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}
```

## CSS (theme tokens: `--neon-teal`, `--neon-cyan`, `--ink-dim`, etc. — see App.css)

```css
.shm-list { display: flex; flex-direction: column; gap: 8px; margin: 4px 0 14px; }
.shm-row {
  display: grid; grid-template-columns: 12px 1fr auto auto; align-items: center;
  gap: 10px; padding: 10px 12px; border-radius: 10px;
  background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
  transition: border-color .3s, background .3s;
}
.shm-dot { width: 9px; height: 9px; border-radius: 50%; background: var(--neon-teal);
  box-shadow: 0 0 8px var(--neon-teal); }
.shm-name { font-size: 13px; color: var(--ink); }
.shm-value { font: 600 15px/1 ui-monospace, monospace; color: var(--neon-cyan);
  font-variant-numeric: tabular-nums; }
.shm-unit { font-style: normal; font-size: 11px; color: var(--ink-dim); margin-left: 3px; }
.shm-flag { font-size: 10px; letter-spacing: .06em; padding: 2px 6px; border-radius: 5px;
  background: rgba(45,212,191,.15); color: var(--neon-teal); }

/* alert = red + pulsing border; warning = amber. Data layer sets the class. */
.shm-row.flag-warning { border-color: rgba(251,191,36,.4); }
.shm-row.flag-warning .shm-dot { background: #fbbf24; box-shadow: 0 0 8px #fbbf24; }
.shm-row.flag-warning .shm-value { color: #fbbf24; }
.shm-row.flag-warning .shm-flag { background: rgba(251,191,36,.18); color: #fbbf24; }
.shm-row.flag-alert { border-color: rgba(248,113,113,.6); background: rgba(248,113,113,.08);
  animation: shm-pulse 1.2s ease-in-out infinite; }
.shm-row.flag-alert .shm-dot { background: #f87171; box-shadow: 0 0 10px #f87171; }
.shm-row.flag-alert .shm-value { color: #fca5a5; }
.shm-row.flag-alert .shm-flag { background: rgba(248,113,113,.22); color: #fca5a5; }
@keyframes shm-pulse { 0%,100% { box-shadow: 0 0 0 rgba(248,113,113,0); }
  50% { box-shadow: 0 0 14px rgba(248,113,113,.35); } }

.gateway-panel { margin-top: 6px; padding: 12px; border-radius: 12px;
  background: rgba(56,189,248,.05); border: 1px solid var(--glass-border); }
.gateway-head { display: flex; align-items: center; justify-content: space-between; }
.gateway-head h3 { margin: 0; font-size: 13px; color: var(--ink); }
.gw-online { font-size: 10px; letter-spacing: .06em; padding: 2px 7px; border-radius: 999px; }
.gw-online.on { background: rgba(52,211,153,.18); color: #6ee7b7; }
.gw-online.off { background: rgba(248,113,113,.2); color: #fca5a5; }
.gw-host { font: 11px/1.4 ui-monospace, monospace; color: var(--ink-faint);
  margin: 4px 0 10px; word-break: break-all; }
.gw-row { display: grid; grid-template-columns: 1fr auto; align-items: center;
  gap: 8px; margin-top: 8px; font-size: 12px; }
.gw-label { color: var(--ink-dim); }
.gw-value { font: 600 13px/1 ui-monospace, monospace; color: var(--ink);
  font-variant-numeric: tabular-nums; }
.gw-track { grid-column: 1 / -1; height: 5px; border-radius: 3px;
  background: rgba(255,255,255,.08); overflow: hidden; margin-top: 4px; }
.gw-track i { display: block; height: 100%; background: var(--neon-cyan);
  border-radius: 3px; transition: width .4s ease; }
.gw-gauge.warn .gw-track i { background: #fbbf24; }
.gw-gauge.warn .gw-value { color: #fbbf24; }
.gw-gauge.alert .gw-track i { background: #f87171; }
.gw-gauge.alert .gw-value { color: #fca5a5; }
```

## Rules
- The component reads `s.flag` and renders color via a class — it NEVER decides
  what "alert" means. All threshold logic stays in `EdgeDataContext.jsx`.
- Values come from the mock/real loop every `VITE_EDGE_POLL_MS` (2s default), so
  the numbers visibly jitter with no extra wiring.
- To force an ALERT for a visual check, temporarily flip a channel's `flag` in
  the mock generator (or lower its threshold) — do NOT add threshold logic here.
