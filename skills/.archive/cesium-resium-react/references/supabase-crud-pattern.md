# Supabase + React + Cesium CRUD patterns (optional Supabase layer)

## Project wiring

- `src/supabaseClient.js` should only export `supabase` + `isSupabaseConfigured` using `import.meta.env.VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`.
- Do NOT import Electron or any Node `window.electron` access from this SPA module. Resium/Cesium apps are Vite SPA; Electron references will throw `ReferenceError: electron is not defined` and kill the whole boot path because `supabaseClient` is imported at module top-level by `App.jsx`. Fix: remove the Electron bridge call, or gate it in a lazy script/code-split it.

## Schema conventions for spatial entities

- spatial tables: `lat`/`lon`/`height` double precision plus `heading`, `pitch`, `roll`, `scale`.
- Supabase auto-creates `id` (uuid) + `created_at` (timestamptz) by default; do NOT declare them explicitly unless you want a custom PK type.
- Use `text` PK (`id text primary key`) only when entities carry natural-map IDs or when you need deterministic IDs across devices.
- Match DB column names to UI field names: use `lat`/`lon` everywhere. Mapping `latitude` to `lat` and `longitude` to `lon` at read/write boundaries is fine, but be consistent or the column names will lie about the shape.

## React context pattern

- Keep a single `EdgeDataContext.jsx` owning both default-state AND cloud-state.
- Updaters/normalize: collapse fetch/CRUD noise at the boundary with a `normalizeXxx()` helper so local UI state and DB schema never have to look identical.
- Prefer optimistic local updates first, then a background reconcile (`reloadFromCloud`) to catch server-generated defaults (e.g. timestamps, default `type` columns) without visible lag.
- Export all CRUD if consumers need them; otherwise keep them internal and expose only high-level operations (`saveXxxToCloud`, `deleteXxxFromCloud`).

## Migrations

- Preferred schema notes: `default 'structural'` on `type text`, `timestamptz` for `created_at` so Supabase auto-fills it.
- Run: `supabase db push` (times out on large schemas); if it times out, rerun in background with a higher timeout and `notify_on_complete=true`.
- If schema got committed into `supabase/` but migration files were omitted, recreate them idempotently — migrations are additive and the directory is in git, so duplicates are rejected by Postgres; clean or rename historically-hashed filenames.
- Rebrand renaming a project: changing the supabase project `name` in `supabase/config.toml` does NOT rename the actual hosted DB. Live DB rename must happen in the Supabase Dashboard or CLI; otherwise every deploy targets the OLD project.

## Vercel + Supabase deploy constraints

- Vercel does NOT run Supabase migrations on deploy. Push schema changes manually via the Supabase Dashboard SQL Editor or `supabase db push` with a valid access token.
- `.env.local` and `dist/` must stay out of git. Removing them from a commit should be done via `git rm --cached...` + `git add -A && git commit --amend` + force push if needed; never rewrite history into a shared branch.
- Always commit a new `dist/` artifact after build; Vercel reads `dist/` for static hosting.

## Common bug traps

- `useEdgeData()` destructuring collisions: helpers in the context can share names with React state updaters (`addNode`, `updateNode`, `removeNode`). If the context exports both, importers MUST rename-on-destructure: `addNode: addNodeFromCloud` or the inner updater shadows the helper and you get "x is not a function" or optimistic-update identity bugs. Verify by searching the importer for the same bare word used as both destructure key and standalone function definition.
- GlbStudioPanel `glbCloudStatus` undefined: if `GlbStudioPanel.jsx` destructures `glbCloudStatus` from `useEdgeData()` but the context consumer wrapper re-exports it by a different key, the local binding resolves to `undefined`. Fix: add the exact key to the destructuring list AND pad JSX reads with `(glbCloudStatus || 'idle')` fallback so the component never crashes before hydration.
- Field-name mismatches between UI shapes and DB schema: a "not-null violation" often masks a mapper that sends `uri` instead of `url` or `lat` instead of `latitude`; grep the data flow first before blaming Postgres. Use a single map over the entity shape at the boundary, or normalize in a helper so both sides see the same key set.
- `fetch('/api/nodes')` 404: do not silently swallow 404. If the API path is intentionally removed, replace it with a Supabase-backed helper and remove the fetch entirely; otherwise unrelated Node.js monitoring hoovers will fail to detect the 404 and the error stays hidden.
