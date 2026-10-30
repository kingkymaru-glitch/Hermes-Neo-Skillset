---
name: live-feed-debug
description: "Diagnose a live external data feed returning no data (e.g. a maritime/weather/stock WebSocket or polling API showing zero results or silently failing). Covers the three-way split — bad credentials vs wrong query/box vs sandbox-can't-reach-host — and the exact probe recipe to pin the cause without guessing. Trigger: user reports 'no ships / no data / feed is empty / it stopped working today' for a live upstream source, or 'X WebSocket won't connect'."
version: 1.0.0
---

# Live Feed Debug (no-data / empty upstream)

## When to use
- A live upstream feed (WebSocket push like AISStream, or polling REST like VesselAPI/weather)
  shows **nothing** — zero entities, empty map, silent failure, or "worked yesterday, dead today".
- User says "no ship at all", "the feed is empty", "X WebSocket won't connect", "it gives me nothing".

## The 3 causes — split them before acting
"Empty feed" is almost always exactly ONE of:
1. **Bad/inactive key** — server rejects auth (WebSocket closes with code 1008 + a text reason;
   REST returns 401/403). Key may be unverified, expired, wrong project, or rate-limited.
2. **Wrong query** — key is fine but the bbox/filter/params match nothing (empty area, wrong
   MessageType filter, bad coordinate order). Busy seas still return data; a dead box returns 0.
3. **Sandbox-blind-spot** — the agent's execution sandbox can't reach the host at all, so a
   connection probe FAILS FROM THE AGENT but would SUCCEED from the user's Mac. A sandbox
   `ENOTFOUND`/`timeout`/WebSocket code 1006 with no reason is NOT proof the key is bad.

Never conclude "the key is broken" from a sandbox negative alone. Confirm reachability first.

4. **Local DNS sinkhole (host resolves to a dead IP)** — the hostname resolves fine on the
   user's own machine, BUT local DNS returns a poisoned/blocked/dead regional IP (e.g. Bybit
   → 175.139.142.25, a TM-Malaysia range that times out), while the REAL host sits on a CDN
   (CloudFront 13.35.202.x) that IS reachable. TCP to the *real* IP works; TCP to the *resolved*
   IP hangs. This looks exactly like cause #3 from the agent, but it is the USER'S MACHINE that
   is blind — not the sandbox. Symptom: `socket.gethostbyname` succeeds, yet WS/REST to that
   host times out; meanwhile `8.8.8.8:443` and other sites connect fine.

## Decision flow
1. Is the key/env present and well-formed? (grep `.env` for the var; check length/charset/no
   trailing CR/space). If absent → that's the bug (app usually shows a `*_NOKEY` status).
2. Can the agent even reach the host? DNS + TCP:
   `python3 -c "import socket; print(socket.gethostbyname('<host>'))"` then
   `curl -sS -m 6 -I https://<host>[/path]`. DNS-resolves-but-TCP-times-out = sandbox blind spot.
3. If reachability is uncertain, run the real probe from the USER'S MAC (where net works).
   Do NOT fabricate "key is bad" from an inconclusive sandbox result.

## WebSocket close-code cheat-sheet (the server's own verdict)
- `1006` with empty reason → socket never established TLS/connection. Network/sandbox block or
  host down — NOT a credential verdict.
- `1008` (Policy Violation) + reason text → server rejected you: invalid/unverified API key,
  wrong BoundingBoxes format, or account not activated. The `reason` string names it.
- Normal open then zero frames → key OK, but nothing matches your filter/box (cause #2).
- `1000`/`1001` clean close → server-initiated (quota/limit), not your bug.

## Reusable probe recipe (run from user's Mac, not the sandbox)
For a keyed WebSocket (AISStream pattern), one node -e command opens the socket with the SAME
key + box the app uses, prints OPEN / MSG bytes / CLOSE code+reason, and self-exits:
```
K=$(grep VITE_AISSTREAM_API_KEY /path/to/.env | cut -d= -f2)
node -e "const w=new WebSocket('wss://HOST/PATH');w.onopen=()=>{console.log('OPEN');w.send(JSON.stringify({APIKey:K,BoundingBoxes:[[[latSW,lonSW],[latNW,lonNW],[latNE,lonNE],[latSE,lonSE]]],FilterMessageTypes:['PositionReport']}))};w.onmessage=e=>console.log('MSG',e.data.length,'bytes');w.onerror=e=>console.log('ERR',e.message||'no-detail');w.onclose=e=>console.log('CLOSE',e.code,JSON.stringify(e.reason));setTimeout(()=>process.exit(0),20000)"
```
Copy the `OPEN` / `MSG n bytes` / `CLOSE <code> "<reason>"` output — that is the diagnosis.
`OPEN` + `MSG` bytes = key good, feed live (your bbox is the only remaining suspect).
`CLOSE 1008 "..."` = key/reason named. `ERR`/`CLOSE 1006` = cannot even connect.

## Local DNS sinkhole — diagnosis + fix (cause #4)

**Diagnose (run on the user's Mac):**
```python
import socket, urllib.request, json, time

# 1. Does the OS-resolved IP actually connect?
host = "stream.bybit.com"
try:
    ip = socket.gethostbyname(host)
    print("DNS says", host, "->", ip)
    t = time.time()
    try:
        socket.create_connection((ip, 443), timeout=8); print("TCP to DNS IP OK", round(time.time()-t,2))
    except Exception as e:
        print("TCP to DNS IP FAILED:", e)   # <-- sinkhole signature
except Exception as e:
    print("DNS fail", e)

# 2. Is it a DNS lie? Ask a non-poisoned resolver (Cloudflare DoH) for the REAL IPs:
req = urllib.request.Request(f"https://1.1.1.1/dns-query?name={host}&type=A",
                             headers={"accept":"application/dns-json"})
real = json.load(urllib.request.urlopen(req, timeout=8))
print("DoH real IPs:", [a["data"] for a in real.get("Answer", [])])

# 3. Does the real IP connect?
real_ip = [a["data"] for a in real.get("Answer", []) if a["type"] == 1][0]
socket.create_connection((real_ip, 443), timeout=8); print("TCP to real IP OK")
```
A dead DNS-IP + reachable real-IP = confirm sinkhole.

**Fix without sudo (in-process, scoped to the bot):** override `socket.getaddrinfo` so the
blocked hostnames resolve to the pinned good IP. Put this BEFORE any network call (WS/requests/
ccxt). See `references/dns-sinkhole-fix.md` for a copy-paste snippet + the CloudFront-rotation
caveat. Works for websocket-client, urllib, requests, and ccxt (all go through getaddrinfo).
Do NOT hardcode the IP into the URL — override DNS instead, so TLS SNI/cert validation still
matches the hostname.

**Why not /etc/hosts?** Needs `sudo` (denied in agent sessions). The in-process override is
preferred and self-contained.
Most feeds surface a status banner/console line. For AISStream MARU: the HUD prints
`🔴 VESSEL TELEMETRY OFFLINE — <message>` where `<message>` is the WebSocket close code+reason;
a `?aisdebug=1` URL flag prints a per-frame `[aisstream] frame N bytes` heartbeat in DevTools
Console — confirms bytes ARE arriving even when nothing falls inside the viewport box.
Always ask the user for that banner text or console line before deep-diving.

## Gotchas specific to AISStream (maritime WebSocket)
- Free, CORS-clean, no proxy. Key from aisstream.io; account must be EMAIL-VERIFIED or the
  socket closes instantly on first frame.
- BoundingBoxes is an ARRAY of boxes, each a 4-corner `[lat,lon]` tuple list (SW,NW,NE,SE).
  One narrow box (e.g. ~55km×90km around Lumut/Malacca) stays inside the free quota.
- `FilterMessageTypes: ['PositionReport']` is what yields the visible ships. Subscribe without
  it and you get only Metadata/StaticData (no positions).
- Key is 40 hex chars; a trailing CR/space in `.env` silently breaks it — validate with python3.

## See also
- `references/dns-sinkhole-fix.md` — copy-paste `getaddrinfo` override snippet + CloudFront
  rotation caveat (the pinned IP can change; re-resolve via DoH when it dies).
- `software-development:supabase-auth-gate` — Pitfall #5 generalizes "sandbox can't reach host"
  to any external feed; the same DNS-verify-before-blaming rule applies here.
- `software-development:systematic-debugging` — root-cause before fixing; this skill is the
  feed-specific application of it.
