---
name: cloudflared-tunnel-demo
description: "Tunnel a local server via cloudflared for live https demos."
version: 1.0.0
---

# cloudflared tunnel for live demos (fix mixed-content)

## Trigger / When to use
You have a LOCAL server (Flask/Node/etc.) on the Mac streaming over `ws://localhost:PORT`
and a LIVE `https://` site (Vercel/Netlify) needs to connect to it for a demo. Plain
`ws://localhost` fails on the live https page with a **mixed-content** error (browsers
block insecure ws from a secure page). Also use when you need a public URL your phone
or a remote viewer can reach, or to tunnel a local IP-cam feed out.

## The fix: cloudflared quick tunnel (no account needed for a demo)
```bash
brew install cloudflared
# quick tunnel = random URL, rotates every restart, FREE, no login
cloudflared tunnel --url http://localhost:8000
# prints: https://<random>.trycloudflare.com
```
- The WS endpoint becomes `wss://<random>.trycloudflare.com/ws` (http→https, ws→wss automatically).
- The live https site points its `stream_url`/`feed URL` at that `wss://.../ws`. Mixed-content gone.

## End-to-end verification (headless, no browser)
The tunnel URL returns **530** for ~30–60s while Cloudflare provisions it — that is
NORMAL, not a failure. Wait, then:
```bash
TUN=https://<random>.trycloudflare.com
curl -s -m5 -o /dev/null -w "HTTP %{http_code}\n" $TUN          # expect 200 after warmup
# prove the wss→local ws actually carries frames:
python3 - <<'PY'
import asyncio, websockets
async def m():
    async with websockets.connect("wss://<random>.trycloudflare.com/ws") as c:
        await c.send("hello"); print("WS_CONNECT_OK", len(await asyncio.wait_for(c.recv(),5)))
asyncio.run(m())
PY
# expect WS_CONNECT_OK GOT_FRAME_BYTES <n>
```

## For a STABLE URL (named tunnel) — needs one-time user login
Quick-tunnel URLs rotate on every restart, so the live site's DB/stored URL breaks
after a reboot. For a stable URL you must create a NAMED tunnel, which needs
`cloudflared login` (opens a browser — the AGENT cannot click it; the USER must do it):
```bash
cloudflared login    # user clicks Allow in browser → writes ~/.cloudflared/cert.pem
cloudflared tunnel create roverkit          # one-time, mints tunnel credentials
# then launch via the tunnel's fixed name (stable URL):
cloudflared tunnel run --url http://localhost:8000 roverkit
```
- `cloudflared login` without a browser cert errors: `Cannot determine default origin
  certificate path` (NO_CERT). That is the signal the user still needs to log in.
- Free Cloudflare account is sufficient for a named tunnel.

## Pipeline shape that worked (ROVER-KIT live demo)
```
webcam → Luna EDGE (ws://localhost:8000) → cloudflared wss tunnel → R-Tessera (live https)
```
- Only a Supabase CCTV row's `stream_url` changes to the `wss://` tunnel URL — the local
  server (Luna EDGE) itself is untouched. Provide a re-runnable SQL updater for the user
  to paste (the agent has no DB creds):
  ```sql
  update public.cctv_cameras set stream_url='wss://<random>.trycloudflare.com/ws'
  where name='Test CAM 02';
  ```
- After the tunnel URL changes (reboot/relaunch), re-run that SQL with the new URL.

## Pitfalls
1. **530 on first hit = provisioning, wait 60s** — not broken.
2. **Quick-tunnel URL rotates** — for anything beyond a one-shot demo, do the named
   tunnel + `cloudflared login` (user action) so the URL is stable.
3. **Agent cannot complete `cloudflared login`** — it opens a browser for human auth.
   Hand that single step to the user; everything else is scriptable.
4. **Kill the tunnel when the demo ends** (it holds a public ingress to the Mac).
   `pkill -f cloudflared` or kill the background session.
5. **`cloudflared tunnel --name X` (old flag) errors without a cert** — use the
   `--url` quick form for instant demos, or the named `tunnel create` + `tunnel run`
   flow after login.
6. **DNS timeout warnings** (`Failed to fetch features` / 192.168.0.1) are harmless
   and unrelated — ignore them.
7. **PIN THE TUNNEL TO IPv4: `--edge-ip-version 4`.** This is the failure that makes a
   demo die an hour after it started working, with nothing wrong locally.

   When an IPv6 route exists at launch, cloudflared registers the tunnel over IPv6. If
   the network then **withdraws IPv6** — a phone hotspot, a laptop moving between Wi-Fi
   and tethering, a router re-lease — cloudflared keeps sending udp6 packets into a route
   that no longer exists. The log fills with:

   ```
   ERR failed to accept incoming stream requests error="failed to accept QUIC stream:
     write udp6 [::]:58411->[2606:4700:a0::7]:7844: sendmsg: no route to host"
   INF Retrying connection in up to 1m4s
   ```

   The local server stays perfectly healthy the whole time, so every local check passes
   and the public URL simply stops answering (curl `000`, DNS `NXDOMAIN` because the quick
   tunnel hostname is released). IPv4 is present on every network a demo runs on, so
   pinning it removes the entire failure mode for no measurable cost:

   ```bash
   cloudflared tunnel --edge-ip-version 4 --url http://localhost:8000
   ```

   Diagnose it in one line: `ifconfig <iface> | grep -c 'inet6.*global'` → `0` while the
   tunnel is failing means exactly this.

8. **A launcher that re-asserts a CACHED tunnel URL without checking the tunnel is
   alive will point your live site at a dead host — and everything will look fine.**
   The collision-safe pattern ("server already up, so just re-assert the URL and exit")
   is convenient and dangerous: it skips the step that would have noticed the tunnel
   died. Before re-asserting a stored URL, **verify the tunnel actually answers**
   (`curl -s -o /dev/null -w '%{http_code}' $TUNNEL` → expect 200); if it does not,
   restart the tunnel instead of re-asserting.

9. **Distinguish "tunnel process running" from "tunnel serving".** `pgrep cloudflared`
   only proves a process exists. A live process with a dead connection is the exact
   state that reads as healthy. Check for a real registration in the log:

   ```bash
   grep "Registered tunnel connection" "$TUNNEL_LOG" | tail -1   # must be present
   # and nothing fatal AFTER it:
   awk '/Registered tunnel connection/{n=NR} /no more connections active/{if(NR>n) c++} END{print c+0}' "$TUNNEL_LOG"
   ```
   Surface "process up, NOT connected" as its own status, distinct from "down".

10. **Match `cloudflared tunnel`, not the full launch command line.** A `pgrep -f`
    pattern containing flags (`cloudflared tunnel --url`) silently stops matching the
    moment the launch line gains a flag — and then a healthy tunnel reports as down.

## See also
- `macos-desktop-launcher` — bundle a double-click `.app` that starts the local server
  + tunnel so the whole demo boots from one Desktop icon.
- `r-tessera-dev` / `luna-edge-dev` — the ROVER-KIT project this was built for.
