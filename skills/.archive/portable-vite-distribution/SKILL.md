---
name: portable-vite-distribution
description: 'Make a Vite/React app run self-contained from a USB drive or any local folder — no cloud, no DB, no hardcoded host/port. One zero-dependency Node server serves the prebuilt dist/ AND a same-origin /api data API backed by plain JSON files inside the project. Covers relative API paths, file-based node/record store, cross-platform start scripts, committing dist/, and the oxlint config plus dev-proxy plus Cesium-asset pitfalls. Trigger: user wants the app to "run from a USB", "transfer to client as a folder", "store all data locally in files", "no Supabase/external DB", or "portable build".'
---

# Portable Vite distribution (USB / self-contained folder)

## When to use
User wants to hand the whole app to a client on a USB stick / as a zip, and have it
just run — with all data living as files *inside the project folder*, no database,
no Supabase, no hardcoded `localhost:PORT`, no external Obsidian/vault dependency.

## The architecture (one server, two jobs)
A single zero-dependency Node `http` server (`server/local-server.mjs`) does BOTH:
1. Serves the static production build from `dist/` (the app).
2. Serves a data API at `/api/nodes` (or any `/api/*`) — same origin as the app.

Node records are stored as **one JSON file per record** under `data/nodes/` inside
the project. Because the API is **relative** (`/api/nodes`), the app works on any
host/port — the client's machine, a USB mount, anywhere. No port guessing.

## Steps
1. **Make the app call a relative API.** Change `const NODES_API = 'http://localhost:8799/api/nodes'`
   → `const NODES_API = '/api/nodes'`. This is the single most important change;
   hardcoding a host/port is what breaks portability.
2. **Write `server/local-server.mjs`** (see `templates/portable-local-server.mjs`).
   Key points:
   - `NODES_DIR = join(ROOT, 'data', 'nodes')` (or `RT_DATA_DIR` env override).
   - `GET /api/nodes` → `readdir` + parse each `*.json`.
   - `POST /api/nodes` → validate `{id,name}`, `writeFile(id.json)`.
   - `PUT /api/nodes/:id` / `DELETE /api/nodes/:id` → update/remove file.
   - Static serving: `safe = normalize(join(DIST, urlPath))`; reject if not under
     `DIST` (path-traversal guard); SPA fallback to `index.html`; correct MIME
     (`.glb`→`model/gltf-binary`, `.js`→`text/javascript`, etc.).
   - Listen on `PORT` (default 4173), `HOST` default `0.0.0.0`.
3. **Dev proxy** so `npm run dev` also hits the store: in `vite.config.js`:
   `proxy: { '/api': { target: 'http://localhost:4173', changeOrigin: true } }`.
4. **package.json scripts:** add `"start": "node server/local-server.mjs"` and point
   `"dev:all"` at `node server/local-server.mjs & vite`.
5. **Cross-platform launchers** (double-click for the client):
   - `start.command` (mac/linux): `cd "$(dirname "$0")"`; check `node` exists;
     `npm install` if no `node_modules`; `npm run start`. `chmod +x`.
   - `start.bat` (windows): `cd /d "%~dp0"`; `where node`; `npm install`; `npm run start`.
   Client only needs **Node.js 18+** (free). Nothing else.
6. **.gitignore:** COMMIT `dist/` (ships prebuilt, so client needs no build step) and
   keep `data/` tracked so records travel. Add `data/` with a comment; keep `dist/` unignored.
7. **`mkdir -p data/nodes && touch data/nodes/.gitkeep`** so the empty folder ships.
8. **README:** add a "Run it (portable / USB build)" section — double-click launcher,
   or `npm install && npm run start` → http://localhost:4173.

## Verification recipe (must actually run it)
Start the server as a **background** process (use `terminal(background=true)`, not `&`),
then curl:
- `curl -s -o /dev/null -w "%{http_code}" http://localhost:4173/` → `200`
- `curl -s http://localhost:4173/api/nodes` → `[]` (clean/empty initially)
- `POST` a node → assert `{"ok":true,"id":...}`; `ls data/nodes/` shows `<id>.json`
- `GET` list returns it; `DELETE` removes the file too
- Cesium assets: `curl -s -o /dev/null -w "%{http_code}" http://localhost:4173/cesium/Cesium.js` → `200`
Then `kill` the server and confirm ports are free + no test files left behind.

## Pitfalls
See `references/portable-pitfalls.md` for the full list. Highlights:
- **oxlint config key is `ignorePatterns`, NOT `ignore`** — `ignore` fails to parse
  (`unknown field ignore`). Always use `ignorePatterns: ["dist","node_modules"]`.
- **Don't scan `dist/` in lint** — it's a minified Cesium bundle (18k warnings). Ignore it.
- **Dev `/api` proxy is dead unless Vite is running AND the app calls through it.**
- **The static server MUST serve `dist/cesium/*`** or the globe never renders
  (Cesium's `CESIUM_BASE_URL` points at `/cesium`). A Vite `base` change can break this.
- **`&` backgrounding in one `terminal()` call is rejected** — use `background=true`.
- Kill stray servers from earlier sessions (5174/5175/5176/8799) before testing, or
  you'll be testing the wrong instance.

## Support files in this skill
- `templates/portable-local-server.mjs` — known-good zero-dep Node server (static + `/api/nodes`, file store). Copy into the target project's `server/` and adjust paths/route.
- `references/portable-pitfalls.md` — verbose pitfall list (oxlint `ignorePatterns` vs `ignore`, dist lint, dev proxy, Cesium assets, backgrounding, stray servers, committing dist).
