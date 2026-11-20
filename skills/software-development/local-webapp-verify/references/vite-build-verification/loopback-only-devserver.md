# Pitfall 8 — dev server bound to loopback only → device/127.0.0.1 fails

## Symptom
`http://localhost:5174` returns HTTP 200 in the Mac browser, but:
- `http://127.0.0.1:5174` → connection refused
- `http://<LAN-IP>:5174` (e.g. S22 Ultra / any phone on the LAN) → timeout

From the device's side "localhost:5174 not working" is literally true, even though the
Mac browser loads it. A naive `curl localhost:5174` "proves the server is up" and hides it.

## Real cause (MARU `my-digital-twin`)
Two compounding issues:
1. `vite.config.js` had `server: { port: 5174 }` with **no `host`** → Vite binds IPv6
   loopback `[::1]:5174` ONLY, not `0.0.0.0`. `lsof -nP -iTCP:5174 -sTCP:LISTEN` shows
   `TCP [::1]:5174` (loopback) not `TCP *:5174` (all interfaces).
2. The running process (PID 7584) was a **stale zombie** from two days earlier — it
   wouldn't pick up today's edits via HMR even after the binding was fixed.

LAN devices can only reach the Mac by its LAN IP, so loopback-only = unreachable from the
phone. (Contrast: the riina project on 5173 was launched with `--host` and IS reachable
from devices — `TCP *:5173`.)

## Fix (encode into the launch step)
Launch with `--host` so it binds all interfaces:
```bash
npm run dev -- --host
# surfaces both:
#   Local:   http://localhost:5174/
#   Network: http://172.20.10.6:5174/
```
Kill any stale dev server first (zombies hold the port and won't reflect edits):
```bash
lsof -nP -iTCP:5174 -sTCP:LISTEN   # PID is column 2
kill <PID>; sleep 1
lsof -nP -iTCP:5174 -sTCP:LISTEN && echo STILL-UP || echo freed
npm run dev -- --host   # background=true, watch_patterns ['ready in','Local:']
```
Permanent alternative: `server: { port: 5174, host: true }` in vite.config.js (exposes the
dev server to the LAN — fine for a field/edge dashboard, be aware on untrusted nets).

## Verification (one pass)
```bash
lsof -nP -iTCP:5174 -sTCP:LISTEN          # expect '*:5174', NOT '[::1]:5174'
curl -sS -o /dev/null -w "localhost %{http_code}\n" http://localhost:5174/
curl -sS -o /dev/null -w "LAN %{http_code}\n" http://<LAN-IP>:5174/
```
Both 200. If only localhost is 200 → loopback-only → restart with `--host`.

## Note
Fixing the binding only makes the S22 *reach* the dev server. The `/s22-api` proxy's
`DEFAULT_IP` in vite.config.js still pointed at a stale `192.168.0.x` while the LAN was
`172.20.10.x`, so the live IP-Webcam feed still missed until the UI override was set. That
is a separate (`vite-edge-proxy`) live-feed miss — see that skill.
