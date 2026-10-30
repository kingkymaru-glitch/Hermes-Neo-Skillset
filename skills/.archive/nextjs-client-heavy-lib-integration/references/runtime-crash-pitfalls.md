# Runtime-only crashes that build/lint CANNOT catch (Next/Vite + client libs)

These bite during the Cesium-in-Next integration work and similar client-heavy
refactors. `next build` / `oxlint` / `tsc` stay green; the browser alone fails.

## 1. Hardcoded "not configured" sentinel -> misleading runtime error
Pattern (seen in R-Tessera `src/lib/supabaseClient.js`):
```js
export function createSupabase() {
  const url = import.meta.env.VITE_SUPABASE_URL
  const key = import.meta.env.VITE_SUPABASE_ANON_KEY
  if (!url || !key) return null            // <- silent null
  return createClient(url, key)
}
```
Caller then does `const sb = createSupabase(); if (!sb) return { error: { message: 'Supabase not configured' } }`.

Symptom the user reports: "node visible, but save says Supabase not configured."
Root cause is ONE of:
- **Env vars missing in the deployed build.** Vite `import.meta.env.VITE_*` is
  inlined at build time. If `.env.local` exists locally but the Vercel project
  has no matching Env Var (or a different name), the production bundle has
  `undefined` -> `createSupabase()` returns null -> sentinel error.
  - Verify: check the Vercel dashboard Env vars match the local `.env.local`
    names. A `node` script using the SAME anon key from `.env.local` can also
    confirm the function path runs. Note: for App Router the var is often NOT
    visible in the served HTML, so grep-the-HTML is inconclusive.
  - For two-app shared DB (LunaV Supabase consumed by R-Tessera anon client)
    the anon key is the SAME value; copy it across both projects' Env Vars.
- **Wrong client / anon not readable.** If RLS blocks anon, the call fails with
  a permission error, NOT "not configured" — so "not configured" almost always
  means the key itself is empty/absent at runtime.

Fix: ensure the Vercel project has `VITE_SUPABASE_URL` + `VITE_SUPABASE_ANON_KEY`
env vars set (matching local `.env.local`), then redeploy.

Diagnostic order when user says "X not configured":
1. Is it a sentinel (hardcoded string) or a real network error? Grep the repo
   for the exact string -> find the `if (!x) return null` + sentinel site.
2. Confirm the env var is present in the DEPLOYED build, not just locally.
3. Confirm the function/client the sentinel guards is what's actually failing.

## 2. Deleted useRef/useState during a refactor -> ReferenceError at runtime
The static tooling does NOT catch a removed hook reference if a closure still
uses the variable name. Seen: a `useEffect` `onClick` handler called
`markerRef.current` after the `const markerRef = useRef(null)` line was deleted
in an earlier edit. Symptom: clicking the map throws
`ReferenceError: Can't find variable: markerRef` and the marker never draws.

Why lint misses it: in a 1-file refactor the variable is genuinely undefined
but TS's noUnusedLocals/oxlint can pass because the closure is typed loosely
(e.g. inline arrow in a `setInputAction` with `any` params). The ReferenceError
only fires on the user's click (code path not exercised at import/parse time).

Guard during refactors: when you DELETE a `useRef`/`useState`/`const` that a
callback references, search the WHOLE file for that identifier before
committing. If a handler uses it, either keep the declaration or replace the
handler. Re-read the edited region's full function after a patch.

## 3. Mind the env-gating DCE trap
`if (!url) return null` is dead-code-eliminated only when the build KNOWS the
value. Because Vite inlines `import.meta.env` at build, a present local var that
is absent in prod becomes `undefined` in the prod bundle (not eliminated) ->
null path taken at runtime. This is indistinguishable from "I forgot the var"
without checking the deploy env. (See vite-build-verification for the DCE
false-"stale" trap.)
