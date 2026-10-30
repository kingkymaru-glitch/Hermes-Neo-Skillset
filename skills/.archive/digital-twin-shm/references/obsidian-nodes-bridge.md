---
title: Obsidian-backed node store for MARU (local bridge server)
desc: Technique for giving MARU map features a persistent, human-readable memory
  in the Obsidian vault via a zero-dep node-http bridge that reads/writes
  Markdown files. Covers the gotchas that bit us (localhost proxy/port
  collision, CORS, list-with-body, buffer() body parsing, dangling helper refs).
---

# Obsidian-backed node store (MARU)

The user's standing rule: Obsidian vault = MARU's working DB / primary update
surface. For features that need persistence but not yet a real backend, back
them with Markdown files in the vault, served to MARU through a tiny local REST
bridge. This keeps every record legible + hand-editable, and the swap path to
Supabase later only replaces the transport (same API shape).

## Architecture
MARU (Vite, :5174) --GET/POST/PUT/DELETE--> http://localhost:8799/api/nodes
        (fail-soft fetch)                         |
                                  server/nodes-bridge.mjs  (node:http, zero-dep)
                                                  |
                                  ~/Documents/obsidian_maru_1/DT Nodes/*.md

Each node = one .md file. Frontmatter = structured fields; body sections =
free-form notes. The file IS the record.

## PORT: use 8799, NOT 8787 (avoid a real collision)
On this machine port 8787 is ALREADY taken by an unrelated proxy
(`cursor-hy3-proxy`, listening on IPv4 127.0.0.1:8787). If the bridge binds to
`*:8787` (all interfaces / IPv6), it "works" only because `localhost` resolves
to IPv6 `::1` first on macOS -- but the moment `localhost` resolves IPv4-first,
MARU silently hits the *proxy* and gets `proxy_error`, not JSON. Fragile flake.

Rule: before binding a local bridge, check for collisions:
    for p in 8799 8890 8855 8788; do
      if lsof -nP -iTCP:$p -sTCP:LISTEN >/dev/null 2>&1; then echo "$p busy"; else echo "$p FREE"; fi
    done
Use a dedicated free port (8799). Keep the port in exactly TWO places that must
stay in sync: `MARU_NODES_PORT` in `server/nodes-bridge.mjs` AND the `NODES_API`
constant in `src/App.jsx`.

## Bridge server (server/nodes-bridge.mjs)
- Zero dependencies: import { createServer } from 'node:http'.
- Honour MARU_NODES_DIR / MARU_NODES_PORT env (defaults to the vault's
  DT Nodes folder, port 8799) so it's relocatable.
- CORS is mandatory: the browser origin is :5174, the bridge is :8799 ->
  cross-origin. Without it, every fetch is blocked.
    res.setHeader('Access-Control-Allow-Origin', '*')
    res.setHeader('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type')
    if (req.method === 'OPTIONS') { res.writeHead(204); return res.end() }
- Request body: use buffer(req).toString('utf8') from node:stream/consumers.
  Do NOT for await (const c of req) -- it fails under node -c syntax check
  (quirk) and is awkward. buffer() is clean + sync-ish.
- Markdown helpers (zero-dep, regex-based):
  - parseFrontmatter(raw) -- match ^---\n([\s\S]*?)\n---\n?([\s\S]*)$;
    coerce [...] / "..." values via JSON.parse; drop empty values.
  - buildFile(fm, body) -- ['---', ...`${k}: ${v}`..., '---', '', body].join('\n').
- Endpoints:
  - GET /api/nodes -> list INCLUDING body (see pitfall below).
  - GET /api/nodes/:id -> { ...fm, body } (404 if missing).
  - POST /api/nodes -> require id+name; 409 if file exists.
  - PUT /api/nodes/:id -> overwrite.
  - DELETE /api/nodes/:id -> unlink.
- listNodes filter: only .md not starting with _ AND having an id
  frontmatter. (Excludes README.md, _NODE_TEMPLATE.md.)

## Markdown schema (node example)
Frontmatter: id, name, type, lat, lon, height, model, status, created,
updated, tags. Body sections: ## Location, ## Model / Viewer,
## Inspection Marks, ## Findings, ## Reports. Seed file + template +
README live in the vault group.

## Frontend wiring (MARU)
- EdgeDataContext: add nodes, setNodes, showNodes, setShowNodes.
- App.jsx: define ONE constant `NODES_API = 'http://localhost:8799/api/nodes'`
  and use it for every fetch (no scattered hardcoded URLs). On mount, fetch
  /api/nodes FAIL SOFT (catch -> leave empty, no crash). Cancel the fetch on
  unmount to avoid stale setState.
- After each write (create/update/delete) call a `reloadNodes()` helper that
  re-fetches the list and setNodes(data) -- do NOT reference a removed
  `refreshNodes()` wrapper (see pitfall #8).
- MapNodePins: map nodes -> resium <Entity> with <PointGraphics> (green)
  + <LabelGraphics> name; onClick -> open editor with the resolved node.
- NodeEditorModal: fields (name, lat, lon, height, model, type, marks,
  findings, report) + Save / Delete. Build body via ## sections; save via
  PUT if id exists else POST; reload list after write. Strip `_none yet_` /
  placeholder lines when seeding from existing body (firstSection helper:
  trim `_` wrappers, treat /none yet|no marks|tbd|todo/i as empty).
- Toggle: a DIRECT context toggle row in MapControlPanel (not a
  LayerManager tile) bound to showNodes.
- Pin click that should open a node: resolve the FULL node from the nodes
  list (nodes.find(n => String(n.id) === id)) so the editor seeds marks/findings.

## Pitfalls (all hit across sessions)
1. localhost curled through proxy -> returns a proxy_error HTML page, not
   JSON. Fix: curl --noproxy '*' http://localhost:8799/... OR export
   NO_PROXY='localhost,127.0.0.1' / no_proxy=... in the shell.
2. No CORS -> browser fetch 5174->8799 blocked. Set Access-Control-Allow-Origin: *.
3. listNodes returned frontmatter only -> editor couldn't seed existing
   Inspection Marks / Findings. Fix: include body in the list response
   (out.push({ ...fm, body })).
4. for await body read fails node -c. Use buffer(req) from node:stream/consumers.
5. Bridge not running must degrade gracefully (nodes empty, no crash) -- the
   user may run MARU without the bridge during real-backend dev.
6. Transient 702-byte curl race on localhost:5174 static assets -- re-fetch
   to confirm true size (Vite dev just hadn't flushed yet).
7. PORT COLLISION (new): another process (e.g. cursor-hy3-proxy) may already
   own your chosen port on IPv4. `localhost` may resolve IPv6-first and
   "work" by luck, then flake. PICK A FREE PORT (8799 here), verify it on
   BOTH 127.0.0.1 AND [::1], and keep it in sync in both server + NODES_API.
8. DANGLING HELPER REF (new): refactoring a helper OUT (e.g. removing a
   useCallback-wrapped `refreshNodes`) leaves call sites calling a now-undefined
   symbol -> ReferenceError on every Save/Delete at runtime, even though lint
   passes (lint shows 0 errors; the undefined call only throws when invoked).
   Always grep for the old name after deleting a helper and add a real
   replacement (reloadNodes()).

## Verification checklist
- Pick a free port: `lsof -nP -iTCP:8799 -sTCP:LISTEN` -> empty (FREE).
- node server/nodes-bridge.mjs -> background; confirm it answers on BOTH stacks:
    curl --noproxy '*' http://127.0.0.1:8799/api/nodes   -> JSON array (with body)
    curl --noproxy '*' "http://[::1]:8799/api/nodes"      -> same (proves no proxy collision)
- End-to-end CRUD through the running bridge (run then delete the probe node):
    curl -s --noproxy '*' -X POST http://localhost:8799/api/nodes -H 'Content-Type: application/json' \
      -d '{"id":"__e2e_test","name":"E2E Test Node","type":"test","lat":"4.0","lon":"102.0","body":"\n# E2E Test Node\n\n## Inspection Marks\n- welded seam OK\n"}'
    curl -s --noproxy '*' http://localhost:8799/api/nodes/__e2e_test   # body has "welded seam OK"
    curl -s --noproxy '*' -X DELETE http://localhost:8799/api/nodes/__e2e_test
    curl -s --noproxy '*' http://localhost:8799/api/nodes             # back to seed node only
- npm run lint (0 errors) + npm run build pass.
- Dev server transforms App.jsx: curl --noproxy '*' localhost:5174/src/App.jsx -o /dev/null -w "%{http_code}" -> 200.
- Can't click in-browser: ask user to eyeball toggle/pin/modal placement.
