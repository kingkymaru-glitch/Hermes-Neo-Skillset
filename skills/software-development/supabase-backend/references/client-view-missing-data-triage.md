# Client / Portal View Missing Data — Triage (LUNAV 2026-07-29)

## Symptom (as reported)
"Client link opened — the defect markers I put on the model DON'T show, and the
audit-report evidence photos are missing. Also the spatial-proxy box/plane is
visible in the client view but shouldn't be."

Three defects were filed together. **Two were FRONTEND, one was DB.** Knowing
which is which before touching SQL saves a wasted migration cycle.

## Fast triage: separate FRONTEND bugs from DB bugs

### 1. Proxy tab doesn't close when clicking another node → FRONTEND (React state)
- Root cause: the model/node click handler only calls `setActiveModelId(m.id)`
  and never clears the proxy drawer.
- Fix (`src/components/ProjectWorkspace.tsx`, model list `onClick` ≈ line 914):
  add `setActiveProxyId(null)` alongside `setActiveModelId(m.id)`.
- If a single `setActiveModelId` setter is reused elsewhere, clear the proxy id there too.

### 2. Spatial-proxy box/plane visible in client/share view → FRONTEND (prop guard)
- Root cause: `<Viewer3D proxies={proxiesForActiveModel} … />` is rendered in
  `readOnly` share mode with no guard; Viewer3D's proxy effect renders every
  proxy mesh unconditionally (no `readOnly` check).
- Fix (ProjectWorkspace): `proxies={readOnly ? [] : proxiesForActiveModel}`.
  Proxies are inspector-only planning placeholders and must NEVER reach the
  client/share view.
- Alt fix: `if (readOnly) return;` at the top of Viewer3D's proxy effect.

### 3. Markers + evidence photos missing in client link → DB (live RPC stale)
- Frontend is CORRECT: `share/[token]/page.tsx` passes `models` (with `markers`
  + `photos_json`) + `proxies` into `<ProjectWorkspace readOnly …>`; the
  report / 3D / defect-detail renderers show markers + `photos_json` regardless
  of `readOnly`. So the data is dropped at the `get_shared_project` RPC on the
  LIVE DB.
- The repo `schema.sql` already returns `photos_json`, but `supabase status`
  showed the CLI was never linked → migrations never applied to live. Applying
  the canonical RPC via the SQL Editor fixed it. (Full reasoning: P35 in SKILL.md.)

## General diagnostic order (reuse for ANY "client view missing X")
1. Does the share/portal handler pass the data to the readOnly component?
   (no → frontend wiring bug)
2. Does the frontend render it regardless of `readOnly`?
   (a `readOnly &&` guard hiding it → frontend bug)
3. If 1+2 pass, diff repo RPC `jsonb_build_object` vs the TS type it feeds →
   any field the type has but the RPC omits = missing in the client.
4. Is the live RPC current? `supabase status` / presence of `supabase/config.toml`.
   Not linked ⇒ live = last manual SQL Editor run ⇒ apply canonical SQL.

## Applying the fix to live
- SQL Editor (dashboard → SQL → paste `get_shared_project` from `schema.sql`
  → Run). Needs only the dashboard login — no extra creds (`.env.local` has no
  DB string).
- CLI: `supabase link --project-ref <ref>` (ref = `<ref>` in
  `NEXT_PUBLIC_SUPABASE_URL`) + access token (dashboard Account → Access
  Tokens), then `supabase db push --linked`.
- Verify: open a real share link, confirm markers + evidence thumbnails render
  and the 3D tab shows pins; confirm no proxy box/plane in the client view and
  that switching nodes closes the proxy drawer.
