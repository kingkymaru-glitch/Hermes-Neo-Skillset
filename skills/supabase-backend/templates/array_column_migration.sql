-- TEMPLATE: convert a single jsonb column to a JSON-array column (jsonb, NOT
-- jsonb[]) and add a sibling JSON-array column, idempotently. Copy-paste ready
-- (no comments). Used when a frontend writes a JS array: plain jsonb is
-- required (jsonb[] rejects JS-array payloads via PostgREST). Drop DEFAULT
-- first to avoid 42804. Rename-style keeps data; the USING collapses jsonb[]
-- to jsonb. Adjust table/column names per case. End with NOTIFY to reload cache.

ALTER TABLE project_sites RENAME COLUMN area_polygon TO area_polygons;
ALTER TABLE project_sites ALTER COLUMN area_polygons TYPE jsonb[] USING (CASE WHEN area_polygons IS NULL THEN '{}'::jsonb[] ELSE ARRAY[area_polygons] END);
ALTER TABLE project_sites ALTER COLUMN area_polygons SET DEFAULT '{}'::jsonb[];
ALTER TABLE project_sites ADD COLUMN IF NOT EXISTS annotations jsonb[] NOT NULL DEFAULT '{}'::jsonb[];

ALTER TABLE project_sites ALTER COLUMN area_polygons DROP DEFAULT;
ALTER TABLE project_sites ALTER COLUMN annotations DROP DEFAULT;
ALTER TABLE project_sites ALTER COLUMN area_polygons TYPE jsonb USING (CASE WHEN area_polygons IS NULL THEN '[]'::jsonb ELSE to_jsonb(area_polygons) END);
ALTER TABLE project_sites ALTER COLUMN annotations TYPE jsonb USING (CASE WHEN annotations IS NULL THEN '[]'::jsonb ELSE to_jsonb(annotations) END);
ALTER TABLE project_sites ALTER COLUMN area_polygons SET DEFAULT '[]'::jsonb;
ALTER TABLE project_sites ALTER COLUMN annotations SET DEFAULT '[]'::jsonb;

NOTIFY pgrst, 'reload schema';
