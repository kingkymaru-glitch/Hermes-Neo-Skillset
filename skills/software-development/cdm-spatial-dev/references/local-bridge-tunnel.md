# Local bridge + tunnel for triggering CDM builds from the live web

Problem: the live Vercel deployment (`lunavsolution.vercel.app`) must trigger a local Blender
build (Surroundings) or Python run (Simulation) on MARU's Mac. The app only QUEUES the job in
Supabase; a local worker must claim it. But the live server cannot reach the Mac behind NAT.

## Architecture

```
live Vercel app ──POST /spawn──▶ tunnel ──▶ Mac bridge (:8790) ──spawn──▶ surroundings_worker.mjs
                                      │                                      │
                                      │                                      ▼
                                      └─────◀─── Supabase job row ◀──── claims + builds
```

## The local half — bridge server (`~/CDM/bridge/server.mjs`)

- Listens on `127.0.0.1:8790` (port 8787 occupied by LM Studio cursor-hy3-proxy).
- `POST /spawn` → returns 202 immediately, then spawns `surroundings_worker.mjs --once` (drains queue).
- `GET /health` → JSON status (`workerRunning`, `lastSpawn`, `lastError`).
- Fires macOS notifications via `osascript` on build start, success, failure.
- Optional `BRIDGE_SECRET` env var enables bearer-token auth on `/spawn`.
- No persistent background process — the worker is spawned per request.

**Start it:** `cd ~/CDM && node bridge/server.mjs` (background). Verify with `curl http://127.0.0.1:8790/health`.

## The tunnel half — what works and what doesn't

### Free quick tunnels — DO NOT USE (all failed in testing)

| Service | Result | Why it fails |
|---|---|---|
| Cloudflare `trycloudflare.com` quick tunnel | 502 Bad Gateway, "context deadline exceeded" | Rate-limited; returns 502 that looks like YOUR code is broken |
| `loca.lt` (localtunnel) | Times out, unreliable | Unstable under load |
| `bore.pub` | Not tested (requires relay server) | Needs a server you control anyway |

The 502 from Cloudflare is the dangerous one — it surfaces as "Bad gateway" and sends you
debugging the bridge server when the tunnel itself is the problem. Rule: if the bridge works
locally (`curl localhost` OK) but the public URL 502s, it is the TUNNEL, not your code.

### Durable options

1. **VPS SSH tunnel** (recommended for reliability):
   ```
   ssh -R 8790:localhost:8790 user@your-vps -N
   ```
   Exposes `your-vps:8790` → tunnels to Mac bridge. ~$5/mo (Hetzner, Oracle Free Tier).
   No rate limits, no domain needed.

2. **Named Cloudflare Tunnel** (recommended for free + persistent):
   ```
   cloudflared tunnel create cdm-bridge
   cloudflared tunnel route dns cdm-bridge cdm-bridge.yourdomain.com  # or use trycloudflare.com
   cloudflared tunnel run cdm-bridge
   ```
   Stable subdomain like `https://cdb-bridge.trycloudflare.com`. Persists across restarts.
   No rate limits on quick tunnels. Needs Cloudflare account + domain (or named trycloudflare tunnel).

## Connecting the Vercel app

Once the tunnel is up, the Vercel `POST /api/surroundings` route (and simulation route) must call
the bridge instead of silently returning. In `app/api/surroundings/route.ts`:

- Set `BRIDGE_URL` env var on Vercel to the public tunnel URL.
- In `spawnWorkerOnce()`, if `process.env.VERCEL` is set AND `BRIDGE_URL` is set, POST to
  `${BRIDGE_URL}/spawn` (with auth header if secret is set). Return 202 to the client.
- Keep the `CDM_WORKER_DISABLE` escape hatch for local testing.

## Port conflicts on MARU's Mac

- `8787` — occupied by LM Studio `cursor-hy3-proxy` (Python). Use `8790` for the bridge.
- Always verify with `lsof -i :<port>` before binding.
