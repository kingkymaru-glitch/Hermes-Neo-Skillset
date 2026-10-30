# Durable node persistence (Supabase + localStorage fallback)

## Why this exists
The original MARU node store used a LOCAL Obsidian-file bridge
(`server/nodes-bridge.mjs` at `http://localhost:8799/api/nodes`). That server
cannot run on Vercel, so on every fresh load (and after deploy) the `GET`
returned nothing and **every node vanished on refresh/deploy**. That was the
real root cause behind "nodes don't persist".

Replacement: `src/nodesService.js` — a single transport that writes to the
Supabase `nodes` table when configured AND mirrors to `localStorage`, so
refresh/deploy retention works even before the table exists or RLS is applied.

## Shape of the service (`src/nodesService.js`)
- `loadNodes()` — tries Supabase `select('*')` ordered by `created_at`; on ANY
  failure (not configured / network / missing table / RLS block) falls back to
  the `localStorage` cache so nodes still render. Always returns an array.
- `saveNode(node)` — normalizes, upserts to Supabase (`onConflict: 'id'`) AND
  writes `localStorage`; fails soft (warns, keeps in-memory list).
- `deleteNode(id)` — removes from both.
- All calls fail soft: a thrown error is swallowed and the in-memory list (or
  `[]`) is returned so the globe never crashes.

## Field normalization
Supabase rows are snake_case; the legacy bridge used camelCase. `nodesService`
accepts both and normalizes to:
`{ id, name, type, lat, lon, height, model, portal_url, status, tags, body }`.
`toDb()` converts back to snake_case (`lat`, `lon`, `portal_url`, ...) for the
Supabase write. `portal_url` is the clickable external-digital-twin URL.

## Frontend wiring (App.jsx)
- ONE import: `import { loadNodes, saveNode, deleteNode as deleteNodeStore } from './nodesService'`
  (alias the service delete so it doesn't collide with the local `deleteNode` handler).
- Boot hydration: `useEffect(() => { loadNodes().then(list => setNodes(list)) }, [])` wrapped in a `cancelled` guard.
- CRUD handlers call `saveNode` / `deleteNodeStore` then `reloadNodes()` (re-read after write).
- Removed the old `const NODES_API = 'http://localhost:8799/api/nodes'` constant entirely.

## SQL migration (manual — no DB token in local .env)
File: `sql/nodes_table.sql` in the repo root. Apply in Supabase Dashboard ▸
SQL Editor for the project whose `VITE_SUPABASE_URL` is set in `.env`. It creates
`public.nodes` (id PK text + lat/lon/height/model/portal_url/status/tags jsonb/
body/created_at/updated_at), an `updated_at` trigger, and OPEN RLS
(`nodes_anon_all` for anon). RLS is open for single-owner demo only — tighten
(auth.uid() = owner, or service role) before any multi-tenant launch.

## Node modal field additions (Items #4 / #6)
`NodeEditorModal` now has an `EXTERNAL DIGITAL TWIN URL (portal_url)` input
(`type="url"`, placeholder `https://`). For existing nodes with a value it
renders a clickable link:
`<a className="node-portal-link" href={...} target="_blank" rel="noopener noreferrer">↗ Open external digital twin</a>`
(CSS for `.node-portal-link` lives in `src/App.css`, styled like the focus button.)

## Gotchas
- `isSupabaseConfigured` comes from `src/supabaseClient.js` (null when env vars
  absent). The service keys off it — no Supabase import-time throw.
- localStorage key is `maru_nodes_v1`. After the table is created AND RLS
  applied, the service does NOT auto-migrate legacy localStorage rows into
  Supabase. If you need old local rows in Supabase, write a one-off backfill
  that reads `localStorage['maru_nodes_v1']` and upserts each.
- Do NOT re-introduce scattered `fetch(NODES_API)` calls. The bridge is now
  legacy (local Obsidian sync only, not production persistence).
