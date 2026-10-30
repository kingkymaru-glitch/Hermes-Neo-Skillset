---
name: supabase-migration
description: "Migrate an app onto (or between) Supabase — backend unification, Firebase→Supabase swaps, multi-app/multi-environment deployment topology, RLS as the rules layer. Use when the user wants to unify backends on Supabase, move an app off Firebase/Firestore, or asks 'can Supabase handle multiple deployments / multiple apps'. Trigger on 'migrate to supabase', 'unify backend', 'firebase expired/replaced', 'supabase multiple deployments'."
---

# Supabase Migration & Multi-Deployment

When moving an app onto Supabase, or unifying several apps on one backend, the questions are
topology + the swap surface — not just "install the SDK".

## Multi-deployment: what Supabase actually allows
(See `references/supabase-multi-deployment.md` for the full answer — bake it into your reply;
don't re-derive it each time.)
- **Multiple apps, one project:** YES. One Supabase project can back RINA + LUNAV + AnglerGO.
  Isolate each app by **schema** (namespace) or table prefix (`catches`, `shops`, `models`).
  One project, one bill, one auth. Free tier covers dev/launch.
- **One app, multiple environments:** Supabase recommends **one project per environment**
  (dev / staging / prod). Don't fold environments into one project. Switch URL+anon key per
  build config.
- **Multiple regions:** supported (Sydney `ap-southeast-2`, Singapore, etc.). Pick the region
  nearest the app's users.
- **Free-tier limits (decisive — seen this session):** 2 projects PER AUTH ACCOUNT max on free.
  When an account (e.g. `kingkymaru`) already holds 2 projects (RINA + MARU/SSR), a THIRD app
  (AnglerGO) CANNOT be created there — you must **create a NEW Supabase account** (new email,
  e.g. `inventedmaru@gmail.com`) or upgrade the account to Pro (~$25/mo). Do NOT try to fold a
  3rd app into a 2-project account; it will be rejected by the dashboard. The "2 projects/org"
  number is the hard cap that forces a new-account decision, not just a new project.
- One project = 500MB DB, limited compute. Split busy apps into their own project when scaling.

## "Unify onto Supabase" — recommended topology
The Founder's phrase "unify into Supabase" usually means **same backend tech + same conventions
+ one team skillset** — NOT necessarily one shared database. Recommended:
- Give each app its **OWN Supabase project** (clean prod/dev separation; a spike in one app
  doesn't starve others) but use the **same region** and the **same patterns** (RLS, Storage-URL,
  email/password auth) as the existing apps. This is the pragmatic reading of "unify".

## Firebase → Supabase swap surface (iOS/Swift example)
When porting an existing Firebase app (Auth + Firestore + Storage):
- `AppState` / `ShopsService`: swap FirebaseAuth + Firestore for the `supabase-swift` client;
  collections → Postgres tables; snapshot listeners → realtime channels / `.select()` polling.
- Binary assets: keep the **Storage-URL pattern** — upload to Supabase Storage, persist the
  public/path URL string; NEVER store blobs in the DB row (same 1MB-ish discipline as
  Firestore; Postgres rows aren't meant for large binaries either).
- Auth: Supabase Auth (email/password or OAuth) replaces FirebaseAuth; inject the session.
- **RLS = the rules layer.** Firebase security rules map to Supabase Row Level Security policies.
  This is cleaner and IS the "shop-owner edits only their shop" gate — design RLS early (it
  pairs with the data-model work, don't defer it).
- App init (`AnglerGoApp`): replace Firebase `configure()` with Supabase client init
  (`SupabaseClient(url:anonKey)`), reading URL+key from a config the user provides.

## SQL ↔ Swift Codable decode contract (the #1 silent runtime break)
`swiftc -parse` cannot catch these — they only fail at runtime when `execute().value` /
`doc.data(as:)` throws on every row. Get the DDL types right against the model:
- `String`-backed `Codable` enum (raw values are emoji/arbitrary strings, e.g. `"🎣 Tackle"`)
  → column MUST be `text`, NEVER a Postgres `ENUM`. A Postgres enum makes PostgREST return
  `{name:"tackleShop"}` and Swift `Codable` throws.
- Nested dict/array model field (`[String:[TimeSlot]]`, `[String:[Model]]`) → column MUST be
  `jsonb` (not `text`/`json`), or the decode into a Swift Dictionary fails.
- Nullable Swift property (`String?`) ↔ nullable column (no `NOT NULL`) unless every insert
  path guarantees a value. `NOT NULL` rejects nil-owner inserts (the dashboard seeds empty owners).
- Prefer `ON DELETE SET NULL` over `ON DELETE CASCADE` for marketplace/child rows so deleting an
  owner account doesn't nuke child data.
- Static-check the DDL before running: assert paren/quote balance, `availability jsonb`,
  `shop_type text`, and that declared columns == the model's `CodingKeys` set. (See `swift-cli-ios-dev`.)
- **Idempotent SQL**: use `create table if not exists`, `drop policy if exists` + `create policy`,
  `create index if not exists` so re-running is safe.

## PostgreSQL function deploy gotcha: CREATE OR REPLACE fails across signature changes

`create or replace function` ONLY works if the new signature (name + arg TYPES + return)
is identical to the existing one. If you change arg names/types/defaults, or the function
was created with different args, Postgres raises (and on live, the Supabase SQL Editor run
can leave the OLD/broken function in place or error) — PostgREST then returns **400**
"could not find the function ... matching the given name and argument types" when the
client calls it. A `supabase.rpc()` 400 is therefore usually an UNDEPLOYED/STALE function,
not client code.

Fix — make the deploy idempotent with an explicit drop first:
  drop function if exists public.<fn>(<argtypes>);
  create or replace function public.<fn>(<args>) returns ... language plpgsql security definer ...
  grant execute on function public.<fn>(<argtypes>) to authenticated;
The `drop function if exists ... (<argtypes>)` MUST list the EXACT arg types so it drops
the right overload.

Also match the LIVE column state: a later migration can change a column's default/CHECK
(e.g. a "glass" theme migration added `'glass'` to a `brand_theme` CHECK and set default
`'glass'`). The deploy SQL must use `coalesce(p_theme, 'glass')` (not the old `'dark'`) or
the function writes a value the constraint now rejects. Always grep the migrations dir for
the column before writing the deploy SQL.

(Probe the live function per the § "When supabase db push is NOT available" recipe — a 400
on the call with correct args = stale/missing function = re-run the idempotent deploy SQL.)

## PostGIS geometry + CLI gotchas (spatial backends)
- PostgREST cannot accept a PostGIS `geometry(Polygon, 4326)` column value via a normal JSON insert — it has no JSON representation for geometry. Write an `insert_*` RPC that takes **WKT text** and does `ST_GeomFromText($1, 4326)` server-side, returning the row with `ST_AsGeoJSON(geom)::jsonb`.
- PostgREST returns PostGIS geometry columns as an **already-parsed GeoJSON geometry object** in the row — drop it straight into a feature's `geometry` for Cesium/Leaflet; do not re-serialize or stringify.
- A bare `INSERT ... RETURNING id` cannot be a scalar subquery inside a SQL-language function (`... WHERE id = (INSERT ...)`). Postgres throws `syntax error at or near "INTO"`. Wrap it in a data-modifying CTE: `WITH ins AS (INSERT ... RETURNING *) SELECT jsonb_build_object(...) FROM ins`.
- `supabase db push` applies `supabase/migrations/*.sql` to the linked live project **without psql** and runs as the login role, so `create extension` / `create table` / `create function` all work through it. Prefer it over hand-applying when psql isn't on the host.
- `supabase projects api-keys` AND the management API (`api.supabase.com/v1/projects/<ref>/api-keys`) MASK the legacy anon/service keys in output with a middle-ellipsis even though the stored string is full length — the printed value lies. Capture the raw response to a file and read it with `node -e "require('<file>')"`, which returns the FULL key.
- `dotenv`'s bare `import "dotenv/config"` reads `.env`, NOT `.env.local`. In a Next repo whose secrets live in `.env.local`, call `config({ path: ".env.local" })` explicitly or every script that guards on `process.env.X` reports the var missing.
- macOS: the supabase CLI access token lives in the login keychain as service `Supabase CLI`, account `supabase` — `security find-generic-password -a supabase -s "Supabase CLI" -w` retrieves it for the management API (`curl -H "Authorization: Bearer $TOKEN" ...`).

## Dashboard run-order checklist (Founder executes in browser; agent cannot)
1. SQL Editor → New query → paste `catches.sql` (profiles.sql, shops.sql) → Run → "Success. No rows returned".
2. Storage → New bucket → name (`catch-images`, `shop-logos`) → tick **Public** → Create. (Public
   so the app reads `getPublicURL` directly; table RLS is separate from Storage.)
3. Settings → API → copy the **anon public** key (long `eyJ…`/`sb_publishable_…` JWT). Paste to the
   agent. NEVER the `service_role` key (bypasses RLS, must stay server-side).
4. Agent patches the `SupabaseService` URL + anon key placeholders, then the Founder's ⌘B is the
   real verification (supabase-swift resolves only in Xcode). Any API-name mismatch from ⌘B → paste
   exact error, agent patches surgically.

## Co-founder loop
Migrations are high-blast-radius. Run the review loop from `ai-coding-collaboration`: read the
real source, challenge wrong calls (e.g. an agent storing blobs inline), apply + static-verify,
update stale docs, commit/push, hand back one task at a time.

## Verification
No Xcode on the CLI host for iOS → use `swift-cli-ios-dev` (`swiftc -parse`). For the backend,
the real check is: deploy SQL migrations + RLS to the Supabase project, then exercise from the
app/supabase CLI. Static-check SQL with `supabase db push --dry-run` where possible.

### When `supabase db push` is NOT available (no CLI link / access token / service key)
You cannot push from the agent host, but you CAN verify the SQL actually applied to the live
project — without fabricating success. The user pastes it into the Supabase SQL Editor; you then
PROBE the live DB with the anon key (same key the client uses; lives in the sibling app's
`.env.local` as `VITE_SUPABASE_ANON_KEY` / `NEXT_PUBLIC_SUPABASE_ANON_KEY`).
- Write a tiny Node probe (`createClient(url, anonKey)`) that:
  - `select('id').limit(1)` on each new table → OK means it exists (rows=0 is fine).
  - calls each new RPC with a dummy UUID. Distinguish the two failure modes:
    - **"function ... does not exist" / schema-cache miss** → RPC was NOT applied.
    - **a domain error** (e.g. "Unknown project", "Not project owner") → function EXISTS and
      RAN (it just rejected the dummy input). This is the PASS signal.
  - For an `auth`-only RPC, call it as anon on purpose: a domain error proves it's live;
    "does not exist" proves it's missing.
- A browser 404 on an RPC call is a RED HERRING: it can mean a stale Vercel deploy (the frontend
  shipped the call before the DB function existed) — NOT necessarily a missing function. Always
  confirm against the live DB with the probe before "fixing" client code.
- Place the probe inside the sibling app's dir (so `node_modules/@supabase/supabase-js` resolves),
  use CommonJS `require`, `rm` it after. Never leave temp `.cjs` in the repo.
- See `references/verify-migration-live.md` for a copy-paste probe template + the exact
  error-signature table.

### Pitfall: orphaned route (compile-green, unreachable in UI)
A new route (`app/project/[id]/home`) can build + typecheck perfectly and still be undiscoverable
because NOTHING links to it. The silent failure: the feature "exists" but the user reports
"can't find it." Fix: every route you add must get an entry point — link the dashboard card to it,
AND add a nav button from the sibling view back/forth. After building, grep the repo for `href={` to
confirm at least one navigation target points at the new route. The LunaV Project Homepage shipped
green then was unreachable until dashboard cards + a workspace "Project Home" button were wired.

## Support files
- `references/supabase-multi-deployment.md` — the exact multi-app / multi-env / multi-region
  answer, with the free-tier numbers, so you stop re-deriving it.
- `templates/migration-plan.md` — starter plan doc (topology decision, swap-surface table,
  RLS list, verification steps) to copy into the repo as `MIGRATION.md`.
