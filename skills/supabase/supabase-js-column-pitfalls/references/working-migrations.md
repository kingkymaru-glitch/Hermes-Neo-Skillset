# Proven Supabase migrations (paste-ready, bare SQL)

## 1. Declare a "list of objects" column correctly — plain jsonb
For any column the JS client reads/writes as a JS array of objects, declare it
as `jsonb` (JSON array), NOT `jsonb[]`. Fresh-table form:

```sql
area_polygons jsonb not null default '[]'::jsonb,
annotations   jsonb not null default '[]'::jsonb,
```

## 2. Convert an EXISTING jsonb[] column -> jsonb (runs clean)
Re-running ALTER ... TYPE jsonb on a jsonb[] column that has a '{}'::jsonb[]
default fails with 42804 unless you DROP DEFAULT first. to_jsonb(jsonb[])
collapses the Postgres native array into a JSON array. This exact block was
applied successfully to live project_sites (area_polygons + annotations):

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

## 3. Rename a single column -> array (preserve data) — alt path
If you started with one area_polygon jsonb row and want area_polygons jsonb[]
(before learning jsonb is better), rename then convert. But PREFER #1/#2 (keep
it jsonb). Shown for reference — this was the intermediate step that led to #2:

```sql
ALTER TABLE project_sites RENAME COLUMN area_polygon TO area_polygons;
ALTER TABLE project_sites ALTER COLUMN area_polygons TYPE jsonb[]
  USING (CASE WHEN area_polygons IS NULL THEN '{}'::jsonb[] ELSE ARRAY[area_polygons] END);
ALTER TABLE project_sites ALTER COLUMN area_polygons SET DEFAULT '{}'::jsonb[];
NOTIFY pgrst, 'reload schema';
```

## 4. Empty-array literal trap
Postgres empty-array literal is {}, not []. [] -> ERROR: 22P02: malformed
array literal. Use '{}'::jsonb[] (native array) or '[]'::jsonb (JSON form).
Drop redundant ::jsonb[] casts on ARRAY[col] (ARRAY[col] already yields jsonb[]).

## 5. Extend a CHECK-constraint enum (e.g. add a theme value)
Text columns with CHECK (col IN (...)) reject new values. Drop + re-add:

```sql
ALTER TABLE projects
  DROP CONSTRAINT IF EXISTS projects_brand_theme_check;
ALTER TABLE projects
  ADD CONSTRAINT projects_brand_theme_check
  CHECK (brand_theme IN ('dark', 'light', 'midnight', 'glass'));
NOTIFY pgrst, 'reload schema';
```

## Verify after any schema change
1. NOTIFY pgrst, 'reload schema';
2. From the app's anon/supabase client: select('new_col') — must NOT return
   42703 (column does not exist). A successful read (even []) proves the
   PostgREST cache is fresh.
3. Attempt the actual client write that was failing — confirm it persists.
