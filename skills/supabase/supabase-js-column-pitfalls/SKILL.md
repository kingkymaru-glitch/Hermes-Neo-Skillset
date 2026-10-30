---
name: supabase-js-column-pitfalls
description: Supabase schema traps when writing from the JS client.
---

# Supabase JS column-typing pitfalls

When a client write to Supabase fails for no obvious RLS reason, suspect a column
TYPE mismatch between what PostgREST expects and what the JS client sends.

## 1. THE BIG ONE — `jsonb[]` cannot receive a JS array
If a column is `jsonb[]` (a Postgres *native* array of jsonb), the JS client
sends a **JSON array** `[{...},{...}]`. PostgREST cannot coerce a JSON array
into a Postgres native array, so the upsert fails — often with a vague
"site save failed" / "could not find the column" or a 400 with no detail.

**Rule:** for any column that holds "a list of objects" the app reads/writes
from the client, declare it as plain **`jsonb`** (a JSON array), NOT `jsonb[]`.
Examples that work because they are `jsonb`: `remarks`, `extra_fields`.
`jsonb` stores `[{...}]` natively and round-trips perfectly through supabase-js.

```sql
-- RIGHT (JSON array, writes cleanly from JS):
area_polygons jsonb not null default '[]'::jsonb,
annotations   jsonb not null default '[]'::jsonb,

-- WRONG (Postgres native array — JS client cannot write it):
area_polygons jsonb[] not null default '{}'::jsonb[],
```

Client code then just does `area_polygons: [...(site.area_polygons ?? []), newItem]`
(no special encoding). `.map` / `.filter` / `.push` all work because it's a JS array.

## 2. Migration literal trap — `[]` vs `{}` for empty array
When converting a column type in SQL you may hit:
`ERROR: 22P02: malformed array literal: "[]"`.
Postgres's empty-array literal is **`{}`**, not `[]`. Use `'{}'::jsonb[]` (or
`'[]'::jsonb` for the JSON form). Also drop redundant `::jsonb[]` casts on
`ARRAY[col]` constructors — `ARRAY[col]` already yields `jsonb[]`.

## 2b. `jsonb[]` → `jsonb` conversion: DROP DEFAULT first (ERROR 42804)
If the column already has a default `'{}'::jsonb[]` and you `ALTER ... TYPE jsonb`,
Postgres cannot auto-cast the array-literal default →
`ERROR: 42804: default for column "X" cannot be cast automatically to type jsonb`.
Fix: drop the default, convert, then set the new `jsonb` default:
```sql
ALTER TABLE project_sites ALTER COLUMN area_polygons DROP DEFAULT;
ALTER TABLE project_sites ALTER COLUMN annotations DROP DEFAULT;
ALTER TABLE project_sites
  ALTER COLUMN area_polygons TYPE jsonb
    USING (CASE WHEN area_polygons IS NULL THEN '[]'::jsonb ELSE to_jsonb(area_polygons) END);
ALTER TABLE project_sites
  ALTER COLUMN annotations TYPE jsonb
    USING (CASE WHEN annotations IS NULL THEN '[]'::jsonb ELSE to_jsonb(annotations) END);
ALTER TABLE project_sites ALTER COLUMN area_polygons SET DEFAULT '[]'::jsonb;
ALTER TABLE project_sites ALTER COLUMN annotations SET DEFAULT '[]'::jsonb;
NOTIFY pgrst, 'reload schema';
```
`to_jsonb(jsonb[])` collapses the Postgres native array into a JSON array.

## 3. Stale PostgREST schema cache — verify, don't assume
After `ALTER TABLE ... ADD COLUMN` / `RENAME COLUMN` / type change, run
`NOTIFY pgrst, 'reload schema';`. But this sometimes does NOT take effect
(especially if run mid-transaction or the API gateway cached the schema).
**Verify through the real client**, not the SQL editor:
query the new column with the *anon* client used by the app. If you get
`code: '42703', message: 'column X does not exist'`, the cache is still stale
OR the migration didn't actually apply — re-run it and re-NOTIFY.
A successful read (even returning `[]`) proves the cache is fresh.

## 3b. THE app-blocker: a multi-column `.select()` dies if ONE column isn't migrated
The most damaging variant of the missing-column trap: **one `.select('a, b')`
query errors the ENTIRE query (42703) when a single column doesn't exist yet** —
and if your code `catch`es that and falls back to a *blocking* default, the whole
app goes down for every user. Real case (RINA, 2026-08-17): a company-status check
did `.select('approved, paused')`; `paused` didn't exist yet (migration never run),
so the query errored and the catch returned `approved=false` → EVERY user saw
"Company registration pending" even for fully-approved companies.

**Rules:**
- Split the always-present column from the optional/not-yet-migrated one into
  **two separate error-swallowing queries**. The one that gates access must not
  fail closed:
  ```ts
  let approved = false;
  try { const {data} = await sb.from('orgs').select('approved').eq('id',id).maybeSingle(); if (data) approved=!!data.approved; }
  catch { approved = true; }   // never block the user on a read error
  let paused = false;
  try { const {data} = await sb.from('orgs').select('paused').eq('id',id).maybeSingle(); if (data) paused=!!data.paused; }
  catch { paused = false; }    // optional column missing = just not paused
  ```
- **Verification habit:** if a user is blocked at a gate but their DB row looks
  correct, CHECK whether the app queries a column that may not exist in the live
  DB yet. An anon REST probe (`curl .../rest/v1/<table>?select=a,b`) returning
  `42703 column X does not exist`, or the diagnostic SQL erroring on it, confirms
  an un-applied migration is silently degrading to the blocking default.
- This is distinct from the stale-cache case (3): here the column is genuinely
  absent, not cached-away — the fix is to RUN the migration (add the column) AND
  make the code not fail closed. Do both.

## 4. Anon read path — `project_sites` has NO anon SELECT
The app's logged-out viewers must read the Project Homepage site row, but
`project_sites` has RLS `sites_owner_all` (owner-only) and **no anon SELECT
policy**. A direct `supabase.from('project_sites').select('*')` returns null
(or errors) for anon → the page falls back to empty and saved areas/notes vanish.

**Fix:** load the site via the SECURITY DEFINER RPC that already returns it:
```ts
const { data } = await supabase.rpc('get_shared_project', { share_token });
const site = (data as { site?: ProjectSite | null })?.site ?? null;
```
The LunaV homepage calls this when a `?share=<token>` param is present (R-Tessera's
"View Homepage" appends `?share=<lunav_share_token>` for public nodes). Owner
(authed) still uses the direct table read + autosave.
**Symptom pattern:** "I can see the page but my saved box/notes aren't there
when logged out" ⇒ anon read path is using the direct table select, not the RPC.

## 5. Adding an enum-like value to a `text` column with a CHECK constraint
Client themes / statuses stored as `text` with `check (col in ('a','b','c'))`.
Adding a new value (e.g. a "glass" theme) requires extending the CHECK,
otherwise the insert is rejected:
```sql
ALTER TABLE projects
  DROP CONSTRAINT IF EXISTS projects_brand_theme_check;
ALTER TABLE projects
  ADD CONSTRAINT projects_brand_theme_check
  CHECK (brand_theme IN ('dark','light','midnight','glass'));
NOTIFY pgrst, 'reload schema';
```
To make a value the universal default: also `ALTER COLUMN col SET DEFAULT 'new'`
and `UPDATE projects SET col='new' WHERE col IS NULL OR col='old';`.
This user set Glass as the universal default this way (see references/glass-theme.md).

### 5b. THE TRAP — a column-only migration will NOT fix a CHECK-gated 400
If a value is rejected by a CHECK (not by a missing column), adding the
columns the insert also needs does **nothing**: the `INSERT` still dies at the
CHECK before any column logic runs, and PostgREST returns a bare `400 ()` with
no body — no `42703`, no "column does not exist", nothing pointing at the
constraint. **Real case (Lunav Solutions, 2026-08-20):** a new `proxies` row
with `shape='dimension'` (and later `shape='annotation'`) 400'd in production.
An earlier hand-off SQL had added the dimension columns — but the live
`proxies` CHECK still read `check (shape in ('box','plane'))`, so every
dimension/annotation insert was rejected. The user re-ran the column-only
script, still 400'd, and the symptom looked identical to "migration not
applied."

**Rules for any new enum value behind a CHECK:**
- The migration that ENABLES the insert MUST extend the CHECK to include the
  new value. Columns the row also carries are separate — add them too, but the
  constraint change is the load-bearing fix.
- Prefer an **idempotent** drop+re-add of the constraint (safe to re-run if the
  user ran a half-fix first):
```sql
alter table public.proxies
  drop constraint if exists proxies_shape_check;
alter table public.proxies
  add constraint proxies_shape_check
  check (shape in ('box','plane','dimension','annotation'));
```
- If the new value has its own columns, add them with `add column if not exists`
  in the SAME script so one paste fixes everything.
- Make any "recorded value" column `NULL`able when the feature is a free-text
  record, not a computed field — e.g. `alter column dimension_value drop not
  null;` so an inspector can describe instead of entering a number.

### 5c. Code-deploy ≠ DB-deploy (both halves required)
A feature that touches the DB needs TWO independent deploys: (1) merge code to
the default branch so Vercel/CI builds it, AND (2) apply the SQL migration to
the **live** Supabase project. Forgetting (2) leaves the app 400'ing in
production even though the code is perfect. When you hand the user SQL, say so
explicitly and give a verification step — don't assume "pushed to main" means
"works." You generally CANNOT run the live SQL yourself (no Supabase CLI link /
no credentials in the agent env, and never put secrets in code), so ship a
idempotent paste-ready script to `~/Desktop` and tell the user to run it.

## 6b. Postgres EXTENSION columns (PostGIS geometry, pgvector) can't be written from JS — pass TEXT, convert server-side
PostgREST cannot coerce a JSON value into a Postgres extension type like
`geometry(Polygon,4326)` or `vector(1536)`. `.insert({ geom: {...} })` with a
GeoJSON-ish object, or `.insert({ embedding: [0.1,...] })` with a JS array,
fails. **Rule:** write those columns ONLY through a SQL function/RPC that takes
the value as TEXT and casts server-side, then returns the row with the column
serialized for JSON:
- geometry: pass WKT, `ST_GeomFromText(p_wkt, 4326)` inside the function.
- pgvector: pass the literal text `'[0.1,0.2,...]'`, `query_embedding_text::vector`.
- read path: return `ST_AsGeoJSON(geom)::jsonb` so the client gets plain JSON;
  a raw `vector` column comes back as a string from PostgREST.
- A `GENERATED ALWAYS AS (a*b) STORED` column is maintained server-side — never
  send it, and it returns already-computed.

### Writing a `LANGUAGE sql` set-returning function with an INSERT
A bare scalar-subquery form (`SELECT ... FROM t WHERE id = (INSERT ... RETURNING id)`)
fails to compile (`syntax error at or near "INTO"`) in `LANGUAGE sql`. Wrap the
INSERT in a data-modifying CTE instead:
```sql
CREATE FUNCTION ... RETURNS jsonb LANGUAGE sql AS $$
  WITH ins AS (INSERT INTO ... VALUES (...) RETURNING *)
  SELECT jsonb_build_object(...) FROM ins r;
$$;
```

## 7. Storage object keys are BUCKET-RELATIVE — double-prefixing silently misroutes
Supabase Storage's REST paths already contain the bucket:
`/storage/v1/object/<bucket>/<key>`. Passing a key that itself starts with
`<bucket>/` produces `<bucket>/<bucket>/...` — the upload returns **HTTP 200**,
the job records the key, and the object is unreachable at that path. Fetching it
later gives `NoSuchKey` / a 400 with `"Object not found"`.

**Rule:** the key stored in your DB should be bucket-relative. Normalise on BOTH
write and read so a caller that passes either form works:
```python
def bucket_relative(key: str, bucket: str) -> str:
    prefix = f"{bucket}/"
    while key.startswith(prefix):
        key = key[len(prefix):]
    return key
```
**Verify by LISTING, not by trusting a success code:**
```bash
curl -s -X POST "$URL/storage/v1/object/list/<bucket>" \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"prefix":"","limit":50}'
```
If the listing shows a folder literally named after the bucket, you have the bug.

## 7b. A private result needs a PUBLIC copy for any unauthenticated viewer
A 3D viewer / image tag / share link loads by plain URL with no auth header. A
private bucket object therefore 404s there even though your service_role client
can read it. Do not "fix" this by making the work bucket public — that exposes
every intermediate artifact. Use two buckets:
- private work bucket (service_role only) — job outputs
- public read bucket — only what someone explicitly published

Publishing = sign the private object → fetch → re-upload into the public bucket →
insert the app row pointing at the public URL. Verify the public URL with a bare
`curl` that sends NO auth header; HTTP 200 there is the only proof the viewer will
be able to load it.

Public-read policy for the bucket (storage.objects):
```sql
create policy "models_bucket_public_read" on storage.objects
  for select using (bucket_id = 'models');
```

## 8. Verify a stored artifact by fetching it back — a DONE status is not proof
Three separate bugs in one session (empty-queue row, bucket double-prefix, a
space in the filename) each reported success. The only reason they were caught
was fetching the artifact back and validating the bytes:
- download it, `shasum -a 256` against the source, and parse the header
  (e.g. a `.glb` must start `glTF`, declared length == actual length)
- a filename containing a SPACE breaks the signed-URL round trip (sign → fetch →
  re-upload) and fails quietly; use underscores in generated artifact names

## 6. Delivery preference (this user)
When handing the user copy-paste SQL for the Supabase SQL Editor, ALSO give a
**clean, comment-free block** they can paste directly. The user explicitly
asked for "clean code not with ur comment etc that i could copied and paste."
Keep the explanatory/commented version in chat context, but the paste-ready
block must be bare SQL.

## Verification checklist after any schema change
1. `NOTIFY pgrst, 'reload schema';` (modern Supabase auto-reloads; harmless).
2. From the app's anon/supabase client: `select('new_col')` — must NOT 42703.
3. Attempt the actual client write that was failing — confirm it persists.
4. If the write is a NEW enum value behind a CHECK and still 400s with no body,
   suspect the CHECK constraint (not columns): re-run the constraint-extending
   part of the migration and re-test the real write. Column-only SQL won't fix it.

## Reference
`references/working-migrations.md` — copy-paste SQL that actually worked for the
area_polygon→area_polygons + annotations conversion (jsonb, not jsonb[]).
`references/glass-theme.md` — worked DDL + CSS + frontend changes to make a new
client theme (Glass) the universal default across ALL pages (CHECK extend +
`:root` cascade + `??` fallback).
`references/check-constraint-400-migration.md` — worked idempotent migration
that fixed a bare `400 ()` on `proxies` INSERT: the blocker was the CHECK
constraint gating `shape`, not missing columns. Includes code-side shape wiring
and the code-deploy ≠ DB-deploy reminder.
