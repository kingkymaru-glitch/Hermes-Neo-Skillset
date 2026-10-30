# DEFAULT_IP drift — proxy aims at a stale LAN subnet after the Mac hops networks

## Symptom (MARU `my-digital-twin`, S22 Ultra "IP Webcam" via `/s22-api`)
You "fixed" localhost:5174 (killed stale zombie, restarted `npm run dev -- --host` so the
S22 can reach the Mac). The dashboard loads on the phone. But the live feed / snapshot still
**502s**. The dev server is clearly reachable (`lsof` shows `*:5174`), so why no feed?

## Real cause
`DEFAULT_IP` in `vite.config.js` is hardcoded to the device's OLD LAN IP
(`192.168.0.6:8080`). The Mac was now on a different subnet (`172.20.10.x` from a phone
hotspot / office / etc.), so the S22 is at `172.20.10.x` — but the proxy still targets
`192.168.0.6`. The proxy's `router` falls back to `DEFAULT_IP` whenever the override cookie
is absent, and a fresh `npm run dev` re-reads `DEFAULT_IP` (the cookie may not have persisted
across the restart). So: dev server reachable, but proxy mis-aimed → 502.

This is a *subset* of the generic 502-cause "(b) proxy mis-aimed", but it specifically bites
right after you've solved the binding problem, because connectivity "looks" fixed.

## Two-state fix
- **Quick, no restart:** open the app's Settings → enter the device's CURRENT LAN IP (the one
  that works in the device's own browser tab) → Save. The UI writes `device_ip_override`
  cookie + bumps `connSeq`; `resolveTarget()`'s `router` re-points live traffic on the next
  request. No dev-server restart.
- **Durable:** set `DEFAULT_IP` in `vite.config.js` to the device's real current LAN IP, then
  restart dev. Now a fresh start points correctly before the user types anything.

## Detection recipe
```bash
lsof -nP -iTCP:5174 -sTCP:LISTEN                 # expect '*:5174' (reachable)
curl -sS -o /dev/null -w "feed %{http_code}\n" http://<LAN-IP>:5174/s22-api/shot.jpg   # 502 => proxy mis-aimed
ipconfig getifaddr en0                            # Mac's real LAN IP
# compare with DEFAULT_IP in vite.config.js; mismatch = the bug
```
If the S22's own browser tab at `http://<S22-IP>:8080/shot.jpg` returns 200 but the proxied
path 502s, the proxy target is the stale subnet.

## Note
Don't confuse with the loopback-only binding trap (`vite-build-verification` Pitfall 8):
that one means the device can't reach the dev server AT ALL (timeout). This one means the
device reaches the server but the proxy points at the wrong device IP (502). Fix the binding
first, then this.
