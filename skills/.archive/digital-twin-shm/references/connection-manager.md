# Dual-Mode Connection Manager (S22 + iPhone edge nodes)

Reference for the portable connection layer in `my-digital-twin`. Lets the user
demo on ANY network without code changes: save a device IP at runtime
("Manual Override") or leave it blank and fall back to a default last-known IP
("Auto-Detect").

## The sharp catch (why we do NOT use the literal spec)
The user's 4-step spec said: `getBaseUrl()` returns `http://${manualIp}:8080`.
That is WRONG for this project — the edge node is IP Webcam on **HTTPS +
self-signed cert on :8080**. A browser hitting `http://192.168.x.x:8080` or
`https://...` directly trips the mixed-content / cert wall and the connection
dies. The fix (in `s22-edge-node.md`): every request rides the Vite dev
proxy `/s22-api`, which carries traffic server-side with `secure:false`. So we
make the proxy TARGET dynamic, NOT the browser URL.

## Files (all built + lint-clean)
- `src/apiUtils.js` — pure resolver, no React. Exports:
  - `getDeviceIp()` -> `localStorage.device_ip_override` || `DEFAULT_HOST`.
    The resolver's default is a hard-coded last-known IP — in this project
    `vite.config.js` sets `DEFAULT_IP = '192.168.0.84'` (NOT an mDNS host;
    the phone is reached via the proxy, so a raw `.local` would never resolve
    in-browser). Keep the resolver default and the vite `DEFAULT_IP` in sync.
  - `getNodeType()` -> `localStorage.edge_node_type` || `'s22'` -> `{ id, label }`.
  - `getFeedUrls()` -> `{ stream, snapshot, audio, telemetry }` built from
    `/s22-api/*` + the node type's endpoint suffixes.
  - `isManualOverride()` -> `!!localStorage.device_ip_override`.
  - `getBaseUrl()` -> kept for spec-compat; returns `/s22-api` (the proxy path),
    NOT a raw IP — callers stay same-origin.
- `vite.config.js` (server.proxy `/s22-api`) — adds a `router(req)` that reads
  the override (mirrored into a Cookie by the UI on save) and re-points the
  target per-request: `https://${ip}:8080`. Default fallback = `DEFAULT_IP`.
- `src/context/EdgeDataContext.jsx` — imports the resolver; exposes
  `reconnect()`, `connSeq`, `manualOverride`, `nodeType`, `deviceIp`.
- `src/ConnectionSettings.jsx` — the modal, fully built:
  - Scaffold (UI only) FIRST, then logic in a second small step (the user's
    "break into small chunks" rule — see SKILL.md Pitfalls).
  - On open: syncs `ip` + `nodeType` from localStorage.
  - Save -> writes `device_ip_override` + `edge_node_type` to localStorage,
    mirrors the IP into a `document.cookie` (so the vite middleware sees it
    server-side), calls `ctx.reconnect()`, closes.
  - Reset ("Auto-Detect") -> clears both keys + the cookie, resets state,
    `reconnect()`, closes.
  - Live Mode label: `manualOverride ? 'Manual Override' : 'Auto-Detect'`.
  - CSS lives in `App.css` under `.conn-overlay / .conn-modal / .conn-chip /
    .conn-input / .conn-btn` — reuses `--glass-bg`, `--glass-border`,
    `--neon-cyan`, `--neon-teal` tokens.
- `App.jsx` — `OverviewPanel` header trigger (the only place the modal opens
  from). Added in the FINAL small step, NOT with the modal file:
  - `import ConnectionSettings from './ConnectionSettings'`.
  - `const [connOpen, setConnOpen] = useState(false)`.
  - `const { manualOverride, deviceIp, nodeType } = useEdgeData()` — the
    trigger lives inside `OverviewPanel` (a child under `<EdgeDataProvider>`),
    so this call is legal; `App` itself still has NO hooks.
  - Header renders a `.conn-head-btn` (link-icon SVG + live
    `${nodeName} · ${manualOverride ? 'Manual' : 'Auto'}` + `deviceIp`) that
    does `setConnOpen(true)`. `.conn-head-btn.manual` gets a teal border via
    its own CSS block in `App.css`.
  - `<ConnectionSettings open={connOpen} onClose={() => setConnOpen(false)} />`
    mounted at the end of `OverviewPanel`'s tree.

## Verified build sequence (one file per turn)
The user halted a prior loop for max-output-token truncation and mandated
"always break into small chunks". The Connection Manager was delivered as:
1. `ConnectionSettings.jsx` scaffold — modal structure + layout only, stub
   handlers (`handleSave`/`handleReset` no-ops), `open`/`onClose` props.
   Verify the file exists + `npm run lint` (0/0).
2. Add logic to THAT file — `useEffect` syncs from localStorage on `open`;
   `persist()` writes `device_ip_override` + `edge_node_type`, mirrors IP to a
   `document.cookie`, calls `ctx.reconnect()`; `Reset` clears both + cookie
   + `reconnect()`. Lint again.
3. Append CSS to `App.css` (`.conn-overlay/.conn-modal/.conn-chip/
   .conn-input/.conn-btn`), then `npm run build` (only real check for CSS) +
   `rm -rf dist`.
4. Wire the header trigger in `App.jsx` (`OverviewPanel`): import + state +
   context destructure + button + `<ConnectionSettings>` mount. Lint + build.
Do NOT concatenate steps 1-4 into one turn — keep the stale-evidence gate
happy and the diffs reviewable.

## iPhone vs S22 endpoint mapping (node-type switch)
Both route through `/s22-api`; only the suffix differs:
- S22 (IP Webcam): `/video` (MJPEG), `/shot.jpg`, `/audio.wav`, `/sensors.json`.
- iPhone (placeholder mapping): `/live`, `/capture.jpg`, `/mic.wav`,
  `/motion.json`. Swap the suffix table in `getFeedUrls()` when the real iPhone
  app is chosen — do NOT fork the proxy.

## Persistence without refresh (the `connSeq` token)
Saving an IP must re-route live traffic with NO browser refresh. Mechanism:
1. UI writes `localStorage.device_ip_override` AND mirrors it into
   `document.cookie` so the vite middleware (server-side) sees it next request.
2. UI calls `ctx.reconnect()` -> `setConnSeq(n=>n+1)` and (android) `setLiveGeo(null)`.
3. The provider's poll `useEffect` depends on `[pollMs, connSeq]`, so bumping
   `connSeq` tears down + restarts the loop against the new proxy target.
4. Consumers that hold a feed `<img src>` watch `connSeq` and append
   `?t=${connSeq}` to bust the cached URL.

## Verification
Lint must stay 0/0 (the context+hook colocation file needs the file-top
`/* oxlint-disable react/only-export-components */`). For env-gated features
build WITH the gate: `VITE_EDGE_MODE=android npm run build && grep -o '/s22-api'
dist/assets/*.js`. CSS changes are best verified with `npm run build` (no CSS
linter) then `rm -rf dist`.
