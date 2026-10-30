# Cloudflared WSS Tunnel — expose localhost Luna EDGE to live R-Tessera

Class: ROVER-KIT CCTV live-feed mixed-content fix. Used when a `ws://localhost`
Luna EDGE stream must be shown on the deployed `https://r-tessera.vercel.app`
(https page blocks `ws://` → "mixed content" error, stream never connects).

## The problem
- Luna EDGE serves `ws://localhost:8000/ws` (or `0.0.0.0:8000/ws`) on MARU's Mac.
- The live Vercel page is `https://`, so the browser refuses to open a `ws://`
  subresource → floating window shows "Stream error".
- Fix: wrap the local WS in a public `wss://` via a Cloudflare quick tunnel. The
  browser talks `wss://<tunnel>` (secure, same-origin policy satisfied), Cloudflare
  terminates TLS and forwards to `http://localhost:8000` (which upgrades to ws).

## Install (one-time, macOS)
```
brew install cloudflared
```
(If `brew` missing: `which brew` — MARU's Mac has it. No sudo needed for user install.)

## Run a quick tunnel (no account, free, ephemeral URL)
```
cloudflared tunnel --url http://localhost:8000
```
First lines print the public URL, e.g.:
```
INF +--------------------------------------------------------------------------------------------+
INF |  Your quick Tunnel has been created! Visit it at (it may take a few seconds to be reachable) |
INF |  https://session-supplier-cole-silent.trycloudflare.com                                     |
INF +--------------------------------------------------------------------------------------------+
```
The WS endpoint is then `wss://<that-host>/ws`.

### Ignore these benign log lines
- `ERR Failed to fetch features ... lookup cfd-features.argotunnel.com ... i/o timeout`
  → MARU's router (192.168.0.1) doesn't resolve Cloudflare's feature API. Tunnel still
  works; features just disable. We PROVED frames flow despite this.
- `ERR Cannot determine default origin certificate path` → that's a NAMED tunnel attempt
  (`--name ...`) needing a Cloudflare account `cert.pem`. Don't use `--name` for quick mode.
- Early `HTTP 530` on curl before the tunnel is "Registered" → wait ~30–60s for
  `INF Registered tunnel connection ... location=kul01 protocol=quic`. (kul01 = Kuala Lumpur edge.)

## Point Supabase `cctv_cameras.stream_url` at the wss URL
MARU pastes this in the Supabase SQL Editor (project `okzmblyboudjffaixa`, anon). The
agent env has NO psql/supabase creds, so deliver `.sql`, never run it:
```sql
-- Update ROVER-KIT CCTV camera stream_url to the secure Cloudflare tunnel (wss).
-- Quick-tunnel URL rotates each restart -> re-run with the new host after restarting cloudflared.
update cctv_cameras
set stream_url = 'wss://session-supplier-cole-silent.trycloudflare.com/ws'
where id = '8754d665-a6c1-444d-87d7-b4174ee31e58';   -- Test CAM 02 (MARU's Luna EDGE)
-- verify:
select id, name, stream_url from cctv_cameras;
```
After running: hard-refresh r-tessera.vercel.app → toggle "ROVER-KIT · CCTV Cameras"
→ click node → floating window paints the live feed.

## VERIFY the tunnel reaches Luna EDGE (real WS client, not just curl)
`curl -i` against the WS path returns a plain HTTP `400` (its own incomplete probe),
which looks like failure but is NOT — use a real WebSocket client. One-liner with the
`websockets` package:
```
pip3 install --user websockets
T=wss://session-supplier-cole-silent.trycloudflare.com/ws
python3 -c "
import asyncio, websockets
async def t():
    try:
        async with websockets.connect('$T', max_size=None, ping_interval=None) as ws:
            print('WS_CONNECT_OK')
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            print('GOT_FRAME_BYTES', len(msg))
    except Exception as e:
        print('WS_FAIL', type(e).__name__, str(e)[:160])
asyncio.run(t())
"
```
Expected (proves end-to-end, Luna EDGE streaming):
```
WS_CONNECT_OK
GOT_FRAME_BYTES 98
```
(98 = first binary JPEG frame from Luna EDGE. Any positive byte count = live.)

## Caveats
- Quick-tunnel URL ROTATES every time you restart `cloudflared` → re-run the SQL with the
  new host. For a STABLE URL use a named tunnel (free Cloudflare account):
  `cloudflared tunnel login` (drops `~/.cloudflared/cert.pem`), then
  `cloudflared tunnel --name rt-ctv --url http://localhost:8000` → fixed `*.trycloudflare.com`
  or a custom domain route.
- Kill the tunnel when the demo ends: `process action=kill` the cloudflared proc, or
  Ctrl-C. Anyone with the URL can view the webcam while it's up.
- Keep the Luna EDGE detection engine RUNNING (not just the server) while showing live;
  a black/frozen window = detector stopped, not a URL problem.
- Insta360 Link webcam on macOS is UVC-class → works with Luna EDGE unchanged. A 360°
  Insta360 needs its app and is NOT a drop-in source. Don't switch to an S22 IP camera:
  self-signed cert rejected by browsers, MJPEG needs frontend change, phone is fragile.

## Alternatives (if cloudflared blocked)
- `localhost.run` (`ssh -R 80:localhost:8000 localhost.run`) → wss subdomain, free, no account.
- `ngrok http 8000` → wss forwarding, free tier, account needed.
- Tailscale Funnel → expose `:8000` over your tailnet with TLS, needs Tailscale.
