---
name: ss-rover-cloud-dev
description: >-
  Build, verify, and ship LunaV Solutions (formerly "SS Rover Cloud"; GitHub
  kingkymaru-glitch/ss-rover-cloud, folder ~/Documents/ss-rover-cloud) 3D
  inspection platform. Stack: Next.js 16 + React 19 + TS, Supabase @supabase/ssr,
  Cloudflare R2 direct upload via r2-presign Edge Function, raw Three.js cockpit.
  Covers local-first deploy gate, live Supabase CLI migrations, Documents +
  Spatial-Proxy, the LunaV rebrand, ref/cwd gotchas. NOTE: "R-Tessera" is a
  SEPARATE CesiumJS task inside the MARU/my-digital-twin repo — NOT a LunaV fork.
  LOAD for ss-rover-cloud / LunaV 3D inspection app / its Supabase+R2 backend.
---

# LunaV Solutions — Dev Playbook (LEGACY — old repo `~/Documents/ss-rover-cloud`)

> **DEPRECATED for new codebase:** This skill covers the older LunaV worktree
> at `/Users/kamarulhk/Documents/ss-rover-cloud`. The current production LunaV
> repo is `kingkymaru-glitch/lunavsolution` at `~/lunavsolution-code`. Load
> `lunav-studio` for the current codebase.
> This skill is retained for historical procedural patterns only.

Ongoing production app: **LunaV Solutions** (formerly "SS Rover Cloud"; GitHub
`kingkymaru-glitch/ss-rover-cloud`, folder `~/Documents/ss-rover-cloud`).
Civil-audit digital-twin platform — inspectors upload 3D models + photos to
Cloudflare R2, pin defects in a Three.js cockpit, and share a read-only portal
via a token.

> **REBRAND (2026-07-26):** product name is now **LunaV Solutions** (not "SS Rover
> Cloud" / "Digital Twin Inspection Reporting"). Logo = `public/logo.png` (the
> LUNA.png, transparent, floats on the dark UI — NO light plinth). Footer copy =
> "Visualising Asset Maintenance — © LunaV Solutions". External brand link →
> `https://luna-v.io`. The repo folder is still `ss-rover-cloud` and the GitHub
> repo is still `kingkymaru-glitch/ss-rover-cloud` — only the *display* name
> changed. When grepping for residual brand, search `SS Rover`, `SS ROVER`,
> `Rover-R`, `ssrover`, `Digital Twin Inspection Reporting` (all must be gone).

## R-Tessera clarification (do NOT confuse with LunaV)
- **R-Tessera** = an internal CesiumJS base-map refactor task spec (Esri 2D
  default + lazy Google Photorealistic 3D Tiles toggle) inside the MARU /
  `my-digital-twin` repo. It is a MARU-side engineering task, NOT a product
  rename and NOT a LunaV fork.
- LunaV's display name changed SS Rover Cloud -> LunaV Solutions (2026-07-26), but
  the **repo folder** (`~/Documents/ss-rover-cloud`) and **GitHub repo**
  (`kingkymaru-glitch/ss-rover-cloud`) are unchanged. Only the *display* brand
  changed. If you see "R-Tessera" in a LunaV context, treat it as a stale/misrouted
  reference and verify against the vault before acting.

## Repo location (cwd gotcha)
The repo is at `/Users/kamarulhk/Documents/ss-rover-cloud`, NOT the shell's
nominal cwd (`~/my-digital-twin`). **Always `pwd` + `ls` (or `find`) before
reading/writing files.** `read_file` by an assumed path fails silently with
"File not found" if the cwd drifted — that wasted a turn in a prior session.

## Stack & file map
- **Next.js 16** app-router (`src/app`), React 19, `tsconfig` strict.
- **Supabase**: browser client `src/lib/supabase/client.ts`, server client
  `src/lib/supabase/server.ts` (both `@supabase/ssr`).
- **Cloudflare R2** direct upload: `src/lib/r2-upload.ts` calls the
  `r2-presign` Edge Function (`supabase/functions/r2-presign/index.ts`), which
  returns a presigned PUT URL (S3 SigV4). File bytes never touch Supabase.
  Allowed exts include `pdf` + a `"doc"` kind (for project documents).
- **Three.js** (RAW — not react-three-fiber) in `src/components/Viewer3D.tsx`.
  MBUX visual language (near-black, turquoise `#00e5c3`/`#2f9bff` accent).

## Model MOVE + ROTATE in the cockpit (Phase 2 — shipped 2026-08-04)
Persisted model transform (position_x/y/z + rotation_x/y/z in `models`). Reusable
pattern for any future "transform the model in 3D" work — full recipe in
`references/viewer3d-model-transform.md`. Essentials:
- `Viewer3D.place()` re-centers the geometry at origin (`obj.position.sub(center)`)
  THEN scales uniformly to 25 units — so rotation pivots about the model's OWN
  centre, not the world origin. Captures `modelBasePosRef` (re-centered base).
- Persisted offset is applied on top at load; a `useEffect([modelTransform])`
  re-applies live on slider drag WITHOUT reloading the model.
- Rotation stored in DEGREES in DB → `THREE.MathUtils.degToRad` in the viewer.
- Click the model in-scene (`raycaster.intersectObject(modelGroupRef.current, true)`)
  fires `onModelClick` → opens a 6-slider transform drawer (Move X/Y/Z ±50, Rotate
  X/Y/Z ±180) + "Reset to Origin". `saveModelTransform()` writes to `models`.
- `page.tsx` loads models with `.select("*")` so new columns flow for free — but an
  EXPLICIT column list elsewhere must add them.
- Data contract: `src/lib/types.ts` (`Marker`, `Model3D`, `ProxyShape`,
  `ProjectDocument`, `SharedProjectBundle`…).

## Local-first deploy gate (STANDING RULE — validated by user)
- Build + verify features LOCALLY (dev server, `npm run build` green, plus a real
  geometry/computed-style check) BEFORE any `git push`. Never push an unverified build.
- For small verified UI tweaks the founder wants it PUBLISHED so he can look at the
  live site — "publish it first, i need to have a look at it, otherwise show me."
  Verify first, then push, then hand him BOTH urls in one message: the live
  `https://lunavsolution.vercel.app` (Vercel auto-builds + auto-promotes from a `main`
  push, ~1–2 min — say so) and a localhost fallback (`:3210`).
- `git push` to `origin/main` = go-live: Vercel's Git pipeline builds AND
  auto-promotes the prod alias.
- **Conflict handling (important):** if a task brief's "EXECUTION" block says
  "commit / push / deploy" but the opening instruction or the standing gate says
  local-first, FLAG the conflict and HOLD the push until the user explicitly
  says "go". The user re-affirmed this: "stick to the plan… only push to GH
  after we both agree." Do NOT blindly follow a contradictory "push" line.
- **`npm run build` is authoritative.** `npm run lint` reports ~130 "errors" that are
  PRE-EXISTING ESLint-rule nits in the original code (`react-hooks/refs` on
  `liveRef.current`, `set-state-in-effect`) — they do NOT fail the build and are not
  from your edits. Don't chase them.
- **Custom Next.js warning (2026-08-07):** the repo's root `AGENTS.md` states
  "This is NOT the Next.js you know" — a Next.js 16 build with breaking changes
  (APIs/conventions/file structure differ from training). **Before any framework-level
  change, read `node_modules/next/dist/docs/` and heed deprecation notices.** The
  `middleware` → `proxy` deprecation is one example already surfacing in the build.
  When verifying edits, run a full `npm run build` (it typechecks + lints via the
  Next compiler); a green build is the proof, not `next dev` (which caches stale
  parse errors in `.next/dev/logs`).

## USER RULE — NO dev-only auth bypass (2026-07-26)
The user explicitly rejected the localhost skip-login dev-bypass: "stop with this
local dev only thing now", "no localhost drama again", "make the changes directly
push to GH". **Do NOT add `/dev-login`, `devbypass.ts`, or "Dev: skip login"
buttons** to this project unless the user asks. If the user can't log in on
localhost, fix the REAL cause (wrong email spelling — it's `inventedmaru@gmail.com`
with an **E**, not `innovatedmaru`; email-confirm toggle; approval gate) instead of
bolting on a bypass. The `dev-only-auth-bypass` skill exists but is OFF for this
user/project by standing preference.

## Login / unlock a user (auth diagnostics + reset)
When a user reports "can't log in", run the **full-spectrum** diagnostic in
`references/auth-diagnostics.md` — check live site (200), `auth.users`
(`email_confirmed_at` / `banned_until` / `last_sign_in_at`), the `profiles.approved`
gate, and the middleware code path — BEFORE concluding. On LunaV the account is
usually healthy and the block is client-side (stale cookie → incognito, or forgotten
password). Full implementation recipe + pitfalls in `references/auth-reset.md`.

**Self-serve reset is SHIPPED (2026-07-29, commit `a76b035`):** login page has a
"Forgot password?" toggle that calls `supabase.auth.resetPasswordForEmail(email, { redirectTo: \`${window.location.origin}/update-password\` })`; new route `src/app/update-password/page.tsx` reads the recovery session via `getSession()`, calls `updateUser({ password })`, then routes to `/dashboard`. Reset is inspector-only by design — the client share never needs it.

> **redirectTo rule:** Supabase only emails the link if `redirectTo` host is in **Auth →
> URL Configuration → Allowed Redirect URLs** (Site URL = `https://lunavsolution.vercel.app`).
> On the deployed site `window.location.origin` === Site URL, so it's covered. For **local
> dev** you must add `http://localhost:3210` (or the running port) to the allow-list or
> the emailed link 404s.

> **Rate-limit pitfall:** `resetPasswordForEmail` is throttled per-email (anti-abuse).
> Two calls close together return **`email rate limit exceeded`**. If you trigger it
> programmatically, don't loop — wait minutes. A prior attempt in the same session
> already consumed the bucket, so a second call fails even though the user is fine.
> Prefer telling the user to request it themselves from the UI.

> **Next 16 debt:** the build warns the `middleware` convention is deprecated →
> migrate to `proxy` when touching auth routing. Don't add new auth logic assuming
> `middleware.ts` is the long-term home.

## Applying schema / RPC changes to live Supabase (CLI, no local DB)
DB changes ship as idempotent SQL files (e.g. `supabase/phase1_5.sql`). Apply
remotely WITHOUT a local Postgres container:

1. **Find the ACTIVE ref:** read `NEXT_PUBLIC_SUPABASE_URL` from `.env.local`.
   That decides the target project. **Do not trust stale ref notes** — a prior
   memory claimed `eobk…` was live, but `.env.local` pointed at
   `okzmblyboudjffaifixa`. The running app is the source of truth.
2. `supabase link --project-ref <ref>` (re-link per session).
3. `supabase db query --linked --file <sql>` — runs the file against the linked
   project via the Management API (no DB password needed).
   - The old `supabase sql -f <file>` subcommand is GONE in CLI 2.109+ (it now
     dumps global help). Use `supabase db query --linked --file`.
   - `db query` does NOT accept `--project-ref`; link first.
4. Verify: `supabase db query --linked --file /dev/stdin <<'SQL' … SQL` to
   `select` the new tables / routines.

### Pitfall: `CREATE POLICY IF NOT EXISTS` is invalid Postgres
`CREATE POLICY` has no `IF NOT EXISTS` → `ERROR: 42601: syntax error at or near
"not"`. Make policies idempotent with:
```sql
drop policy if exists "name" on public.table;
create policy "name" on public.table for all using (...) with check (...);
```
(`create table if not exists` / `alter table … add column if not exists` ARE fine.)

### Pitfall: large JSX patches can swallow a sibling closing tag
Inserting a big block via `patch` when the anchor matches multiple occurrences
can eat a neighboring `</div>`. After any complex JSX edit, re-read the region
catch unbalanced tags early. (The `next dev` server
may cache a stale parse error in `.next/dev/logs` — a fresh `npm run build` is
the truth.)

Also: when adding a `tab === 'x' ? <A/> : <B/>` switch around an EXISTING block that
already contains a sibling `{...}` expression (e.g. wrapping the dashboard's create
panel + the project-list `{loading ? …}`), the `: (` branch needs a `<>…</>` fragment
wrapper — bare two-sibling JSX inside a branch is a parse error. Verify with `npm run build`.

### Pitfall: `patch` replace_all can duplicate/mangle a multi-occurrence pattern
`patch` with `replace_all=true` matches EVERY occurrence of `old_string`,
including when `old_string` is a SUBSTRING of longer lines. In a session this
mangled a 2-line union (`brand_theme: ...;\n theme: ...;`) by also matching the
partial `theme:` line inside a different interface, producing duplicated and
corrupted lines. **Prefer unique full-line (or full-block) anchors; never use
replace_all on a pattern that also appears as a substring elsewhere.** If a
replace_all produces odd duplicates, immediately re-read the region and fix by
pasting the exact intended block (the tsc error list pinpoints the damage).

## USER RULE — NO dev-only auth bypass (2026-07-26)
The `/project/[id]/home` (ProjectHomepage) view is shared with logged-out viewers
via R-Tessera's public "View Homepage" button. The access model:

- `project_sites` has NO anonymous `SELECT` policy (only `sites_owner_all` = owner, via
  session `auth.uid()`). So a **direct `project_sites.select()` returns NULL for anon** —
  the saved area polygons / annotations silently vanish for public viewers.
- The ONLY anon-readable site path is the SECURITY DEFINER RPC **`get_shared_project(share_token)`**,
  whose `'site'` key carries the `project_sites` row (`coalesce(select to_jsonb(s) ...)`).
- Therefore the **page must pass a `?share=<token>`** and the component must load via the RPC
  when `shareToken` is present, NOT a direct table read.

**Two-sided fix (both required):**
1. **R-Tessera** `ProjectNodes.jsx` `homepageUrl(n)`: for a public node with `lunav_share_token`,
   emit `${LUNO_URL}/project/${n.lunav_project_id}/home?share=${n.lunav_share_token}`.
   (Its sibling `goToUrl` already does this for `/share/<token>` — mirror it.)
2. **LunaV** `ProjectHomepage.tsx` load effect:
   ```ts
   let s: ProjectSite | null;
   if (shareToken) s = await loadSharedSite(shareToken);   // anon-safe RPC path
   else s = await loadProjectSite(projectId);              // owner direct read
   ```
   Add `loadSharedSite(token)` to `src/lib/projectSites.ts`:
   ```ts
   export async function loadSharedSite(token: string) {
     const { data, error } = await createClient().rpc("get_shared_project", { share_token: token });
     if (error) throw new Error(`Shared site load failed: ${error.message}`);
     return ((data as any)?.site as ProjectSite | null) ?? null;
   }
   ```
3. The page `src/app/project/[id]/home/page.tsx` already does `notFound()` unless
   `canEdit || shareBundle?.project` — so the `?share=` param is what makes anon resolve
   (no 404). Owner (authed) still works via `canEdit`.

**Symptom → cause:** "logged out, I can see the homepage but my box area isn't there" =
component used the direct `loadProjectSite` for anon. Use `loadSharedSite`.

## Next 16 `middleware.ts` `isPublic` gate — SILENT 307 BLOCKS NEW ROUTES (CRITICAL, 2026-08-08)
Next.js 16 App Router still runs `src/middleware.ts` (build warns it's deprecated →
`proxy`, but it is live TODAY). The LunaV middleware gates every route behind an
`isPublic` allow-list:

```ts
const isPublic = path === "/" || path.startsWith("/login") || path.startsWith("/share") || path.startsWith("/auth");
if (!user && !isPublic) return NextResponse.redirect("/login");
```

**Trap:** ANY new route you add that isn't in `isPublic` returns **HTTP 307 → /login**
for unauthenticated (and even some authed) requests. Symptom looks like "I clicked the
project / button and NOTHING happened" — because the browser was bounced to /login (or,
for an already-logged-in user, to `/login?reason=pending` if the `profiles.approved`
check also fires). This bit the `/project/[id]/home` Project Homepage: dashboard cards
linked to it, but every request 307'd to /login, so the page appeared dead.

**Rule:** when you add ANY new App Router route that must be reachable without a full
auth gate (public read-only views, share-style pages, geo-link landing pages), ADD it to
`isPublic` in `middleware.ts` — explicitly. The route itself should enforce real access
(owner via session, viewers via `?share=` token; invalid access → `notFound()`). Example
for the Project Homepage:
```ts
path.startsWith("/project/") && path.endsWith("/home")
```
Then VERIFY with the dev server: `curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/<new-route>`
— expect `404` (notFound for invalid id) NOT `307` (redirect = still blocked).
NEVER trust "the build passed" alone — the build won't catch a middleware redirect.
Also: for a LOGGED-IN but unapproved user, the `profiles.approved` check ALSO redirects to
`/login?reason=pending`; if a "does nothing" report comes from an owner, confirm their
profile is `approved` too.

## Popup-blocker: `window.open` after `await` is dead (2026-08-08)
A `window.open(url, "_blank")` call placed AFTER `await supabase.rpc(...)` (or any async
`await`) is treated by the browser as a popup NOT initiated by a user gesture → silently
blocked → "the button did nothing / no new tab opened". This broke the "Link to R-Tessera"
button. **Fix:** open the window SYNCHRONOUSLY on the click gesture first, then navigate
it after the await:
```ts
const popup = window.open("", "_blank");   // synchronous, within the click handler
try {
  const { data, error } = await supabase.rpc("mint_handoff_token", { p_project_id: p.id });
  if (error) throw error;
  const url = `https://r-tessera.vercel.app/?link=1&project=${p.id}&token=${data}`;
  if (popup) popup.location.href = url; else window.open(url, "_blank");
} catch (e) { if (popup) popup.close(); alert(`... ${e.message}`); }
```
Applies to ANY "open external link after fetching a token/URL" button. Keep the `window.open`
call in the same synchronous tick as the user event.

## LIVE migration gate — untracked SQL = pending live-DB work (discovered 2026-08-05)
Vercel builds the frontend only; it NEVER runs migrations. A migration file + a frontend PR
can both ship to prod while Postgres is still stale, and the breakage stays invisible until a
real write hits the missing column. **Rule: any time you open the repo, run**
`git status --porcelain -- 'supabase/*.sql'`. **Any untracked/modified `.sql` under
`supabase/` is pending live-DB work that is very likely already fronted by shipped UI.** Apply
it to the live DB (recipe below) AND commit it in the SAME session as the frontend that depends
on it — an untracked SQL file is not backed up on GitHub and can be lost. Full detection +
apply + commit checklist in `references/live-migration-gate.md`.

## Known state (header date is stale — last real feature commit 3982a01, 2026-08-04)
- `supabase/migrations/20260730_metrics.sql` added two SECURITY DEFINER count-only
  RPCs: `public.model_count()` and `public.marker_count()` (granted to `anon,
  authenticated`). They aggregate counts only — no PII, safe to expose.
- **Backend half is done; frontend consumer is NOT.** `src/app/admin/page.tsx`
  still renders only the user-approvals table — nothing calls `model_count()` /
  `marker_count()` yet. A "growth dashboard" is half-scaffolded: the data fns
  exist and are deploy-safe; you only need to call them from a client component
  and render the numbers.
- Both RPCs are `stable security definer` — call via `supabase.rpc("model_count")`
  (no args). Do NOT re-create them in a migration if already applied.

## Dev server
A `next dev` server is usually ALREADY running on **port 3210** (local-first
gate). Starting another `npm run dev` fails with "Another next dev server is
already running." Hit `:3210` for verification; don't spawn a second one.

## Known UI gaps / pending features
- **Executive Summary / report links: SHIPPED (Phase 5, commit chain ending 3982a01).**
  `linkify()` in `ProjectWorkspace.tsx` now wraps bare `http(s)://…` URLs as clickable
  `<a target="_blank" rel="noopener noreferrer">` in the executive summary, the audit-report
  table (finding title + description/remarks), and the Defect Detail popup — for BOTH the
  inspector view and the client share portal (same component). Safe React-node rendering,
  NO `dangerouslySetInnerHTML`. Do not re-implement; if a URL is still dead somewhere, check
  it's routed through `linkify()` first. See `references/known-gaps.md`.

## Spatial Proxy model isolation fix (2026-07-29)
When adding `model_id` to the proxies table for model-isolated display, the filtering
logic in `ProjectWorkspace.tsx` must handle:
1. **No active model**: Show all proxies (backward compatibility)
2. **Active model exists**: Filter to `model_id === activeModelId` OR `!p.model_id`
   (for legacy proxies that may have null model_id before migration)

The fix in `proxiesForActiveModel` useMemo:
```typescript
const proxiesForActiveModel = useMemo(() => {
  if (!activeModelId) return proxies;
  return proxies.filter((p) => p.model_id === activeModelId || !p.model_id);
}, [proxies, activeModelId]);
```

This prevents the 400 error when:
- Migration hasn't been applied (model_id column missing)
- Existing proxies have null model_id
- User switches between models with no active model selection

## LUNASCAN desktop integration (2026-08-07)

LUNASCAN is a **separate macOS desktop app** (`~/Documents/LUNASCAN`, builds
`dist/LUNASCAN.dmg`) that turns drone footage into `.glb`. LunaV is the web
viewer/inspector. The integration model the founder chose:

- **NO in-app R2 import from LUNASCAN.** The old "+ Import from LUNASCAN" button
  (+ `ImportScanModal`, `handleImportScan` R2 browse) was REMOVED from
  `ProjectWorkspace.tsx`. LUNASCAN's pipeline does NOT export to R2 (user directive:
  local-only output). So the R2 import seam is dead — if you see it referenced,
  remove it; do not rebuild it.
- **LUNASCAN download lives in Settings, not the workspace.** Added a Settings
  panel to `src/app/dashboard/page.tsx` with a "↓ Download LUNASCAN (.dmg)" link
  sourced from `process.env.NEXT_PUBLIC_LUNASCAN_DMG_URL` (falls back to a disabled
  button + "set NEXT_PUBLIC_LUNASCAN_DMG_URL" note when unset). The `.dmg` is hosted
  on Cloudflare R2 as a **static public-read object** (serving an installer — this
  is separate from LUNASCAN's pipeline output, so it's compatible with the
  no-R2-export rule). Set the env var in LunaV's `.env.local` to the R2 public URL.

Edit checklist when touching this:
- Removing the Import button: also drop the `ImportScanModal` import, the
  `importOpen`/`setImportOpen` state, the `handleImportScan` fn, and any
  `ScanGroup` import that becomes unused (grep the file after).
- The Settings panel uses the existing `dash-panel` / `mb-btn mb-btn-primary` class
  vocabulary — keep visual consistency.

## LunaV UI nav convention (2026-08-09 — USER PREFERENCE, durable)
The founder standardized the navigation chrome. Treat these as standing rules for
any LunaV UI work:

### 1. Text-only labels — NO leading emoji/icon glyphs
Every **nav tab button** and every **Settings dropdown entry** is plain text. No
`⌂ 🌐 🧊 📋 📊 📁 ⚙ 📤 🎨 ⏻` prefixes. If you add a nav/tab/Settings item, name it
in words only. (In-canvas drawing controls — the ✎ toggle, ▭ Box area, ✏️ Trace
polygon, 📝 Add note, 🗑 Delete all areas, × close — are FUNCTIONAL map tools, not
nav chrome; those keep their glyphs. Don't strip them.)
Standard owner nav set on the Project Homepage:
`Home · Project Home · 3D Digital Twin · Audit Report · Analytics · Documents · Settings`
Workspace top tabs: `3D Digital Twin · Audit Report · Analytics · Documents` (the
old `LunaV Studio` *builder* tab was REMOVED from the tab row).

### 2. "LunaV Studio" = a SETTINGS dropdown entry, not a top-level tab
After removing the builder tab, the founder wanted the "LunaV Studio" button to
live INSIDE the ⚙ Settings menu (between Appearance and Logout). It routes to the
geo-linked Project Homepage: `router.push(\`/project/${id}/home\`)`. Do NOT
re-add it as a standalone nav tab.

### 3. Project Homepage owner nav wires into the workspace via `?tab=`
The homepage "3D Digital Twin / Audit Report / Analytics / Documents" buttons deep-
link into the inspection workspace, which now reads `?tab=` from the URL:
- Homepage: `window.location.href = \`/project/${id}?tab=3d\`` (etc.)
- `src/app/project/[id]/page.tsx` reads `searchParams.tab` and passes `initialTab`
  to `ProjectWorkspace`; `effectiveInitialTab` honors it (owner default `3d`,
  client default `report`). Valid tabs: `3d | report | analytics | docs`.
- "Settings" on the homepage routes to `/project/${id}` (the gear dropdown lives there).

### 3a. ARRAS Spatial tab ordering rule
For ARRAS/reservoir work, the workspace tab order is:
`Spatial | 3D Digital Twin | Audit Report | Analytics | Documents`.
The Spatial tab is FIRST, before the existing 3D Digital Twin tab. Do not append
it at the end. This was an explicit founder requirement so the reservoir control
surface is the primary entry point, not an afterthought.

### 3b. ARRAS Spatial model selection UX
The Spatial model selector is a **dropdown** in the 3D Digital Twin tab's model
sidebar, positioned **under the Add Model button**. It lists all uploaded models
plus a `None — Spatial tab will be blank` option. Do NOT put a per-model
"Spatial" button in the model list; the founder rejected that as untidy.

### 3c. ARRAS demo-mode: local-only spatial selection
When the live Supabase project does not yet have the `spatial_model_id` column,
keep spatial selection **local-only** to avoid demo breakage:
- `saveProjectSpatialModel()` updates `spatialModelId` state only
- Do NOT write to `projects.spatial_model_id` until the migration is applied to
  the target DB
- Spatial tab renders blank when `spatialModelId` is null; otherwise it finds the
  model via `models.find(m => m.id === spatialModelId)` and renders `Viewer3D`
  with that model's transform/scale
- When the ARRAS Supabase project is ready, re-enable the DB write and apply
  `supabase/20260908_arras_model_slots.sql` there

### 3d. ARRAS branch + deploy isolation
ARRAS feature work lives on `arras/*` branches:
- `arras/reservoir-tab` in LunaV
- `arras/fleet-dashboard` in R-Tessera
These branches are for localhost development + GitHub record only. Do not merge
to `main` and do not push to Vercel unless the founder explicitly says "go".
Use `[skip deploy]` in commit messages on ARRAS branches as an extra guard.

### 3c. ARRAS Supabase project
ARRAS uses a separate Supabase project from LunaV production:
- Project ref: `lxmmxpxjercmhmiuqegq`
- Linked from `~/ARRAS` repo via `supabase init` + `supabase link --project-ref lxmmxpxjercmhmiuqegq`
- Local dev points `.env.local` at this project; LunaV production remains untouched.
- "Home" → `/dashboard`. "Project Home" is the current page (rendered active/disabled).

### 4. Anon (public viewer) homepage chrome
Logged-out viewers keep a MINIMAL bar: `← Back` + `Home` (→ `/login`). No edit
buttons, no full nav array. (The shared/owner access model is in the Anonymous
Project Homepage read path section above.)

### 5. Login → dashboard → project homepage flow
Login redirects to `/dashboard` (the project SELECTOR / "homepage"). Dashboard
project cards link to `/project/${id}/home` (the Project Homepage), NOT the
workspace. This flow is already wired — don't reroute it.

> **STALENESS FLAG (2026-08-09):** the header of this skill calls the repo
> "DEPRECATED / legacy" and says the current code is at `~/lunavsolution-code`
> (skill `lunav-studio`). But THIS session's actual edits were made in
> `~/Documents/ss-rover-cloud` and `git push` went to
> `kingkymaru-glitch/lunavsolution` — so `~/Documents/ss-rover-cloud` IS the active
> working checkout for the lunavsolution project (GitHub repo renamed; local folder
> name unchanged). The `lunav-studio` skill may be redundant. Recommend the curator
> verify/consolidate; do not treat this skill as dead.

## ROVER-KIT CCTV camera registry (shared LunaV/R-Tessera backend)
Concrete extension of the single shared Supabase project with a CCTV camera registry so
R-Tessera can render camera nodes and an edge device can write detection events — no
second backend, no second auth. Phase 0 SQL + Phase 1 LunaV "Vision" tab are BUILT
(`~/lunavsolution-code`, `next build` green); Phases 2–5 pending. Key pattern: new
`cctv_cameras`/`cctv_events` tables + owner-verified `upsert_cctv_camera` RPC + anon
`cctv_cameras_public` view + deep-link reuse of `mint_handoff_token`. Full recipe, SQL,
and component contract in `references/rover-kit-cctv-integration.md`.

## Reference files
- `references/supabase-remote-migration.md` — copy-paste recipe + verified
  Phase 1.5 apply transcript (tables, RPC, r2-presign redeploy).
- `references/rover-kit-cctv-integration.md` — ROVER-KIT CCTV camera registry: shared-backend
  SQL (cctv_cameras/cctv_events + owner-verified upsert RPC + anon read view), LunaV "Vision"
  tab integration, R-Tessera deep-link reuse, plus the unbuilt Phases 2–5.
- `references/architecture.md` — table/RPC map + Documents / Spatial-Proxy
  feature shape, and how read-only share forwards them.
- `references/migration-db-push.md` — `supabase db push --linked` vs
  `supabase db query --linked --file` for applying schema/RPC to the live project.
- `references/feature-node-photos.md` — per-node evidence photos: max 3 @ 200KB
  (`photos_json` column, `attachPhotos`, client-side enforcement pitfalls) + the
  LunaV rebrand footnote.
- `references/auth-reset.md` — password-reset implementation recipe, redirectTo allow-list
  rule, `email rate limit exceeded` pitfall, and the `.cjs` programmatic-trigger pattern.
- `references/known-gaps.md` — executive-summary linkify gap + recommended fix.
- `references/viewer3d-model-transform.md` — persistent model MOVE+ROTATE recipe
  (re-center then offset, live re-apply via modelBasePosRef, click-to-pick, schema).
- `references/live-migration-gate.md` — apply + COMMIT pending migration SQL in the same
  session as the frontend that depends on it (untracked-SQL detection, apply checklist).
- `references/analytics-design.md` — dashboard/analytics visual design rules: SVG line
  graphs, slim 4px pill bars, severity strips, inset commentary. Encodes user's "modern,
  slim, exclusive" preference established after the chunky bar-chart redesign was rejected.
- `references/theme-adding.md` — add a new client theme (Appearance → Theme): CSS
  `data-theme` block + type-union ×N files + Appearance selector + DB CHECK-constraint
  migration. The "Glass" (iOS frosted-glassmorphism) theme is the worked example.
- `references/ar-pose-stabilization.md` — MindAR+A-Frame jitter/vanish fix: decoupled display
  root, `enableStabilizer` (smoothing + hold-on-lost + motion-consistency gate; factor 1.0
  exact-tracking mode for setup.html), `enableManipulator` multi-touch alignment (drag/pinch/
  twist), slider-toggle touch-first pattern.
