# Glass theme — making it the universal default (worked DDL)

Context: LunaV client themes live in `projects.brand_theme text not null
default 'dark' check (brand_theme in ('dark','light','midnight'))`. A new
"glass" theme was added. Three things had to change together:

## 1. Extend the CHECK + set default + backfill existing rows
```sql
ALTER TABLE projects
  DROP CONSTRAINT IF EXISTS projects_brand_theme_check;
ALTER TABLE projects
  ADD CONSTRAINT projects_brand_theme_check
  CHECK (brand_theme IN ('dark','light','midnight','glass'));
ALTER TABLE projects
  ALTER COLUMN brand_theme SET DEFAULT 'glass';
UPDATE projects
  SET brand_theme = 'glass'
  WHERE brand_theme IS NULL OR brand_theme = 'dark';
NOTIFY pgrst, 'reload schema';
```

## 2. CSS default cascade (so global pages like /dashboard, /login also go Glass)
The base `:root` block holds the DEFAULT theme variables. The other themes are
applied via `html[data-theme="X"]`. To make Glass universal:
- Move the OLD `:root` (dark) values into a NEW `html[data-theme="dark"] { ... }` block.
- Replace `:root { ... }` with the Glass palette variables.
- Keep `html[data-theme="light"]` / `html[data-theme="midnight"]` as-is.
Now `:root` = Glass (inherited by every page that doesn't set data-theme), and
"Dark" is still selectable via the explicit override.

## 3. Frontend fallbacks `?? "dark"` → `?? "glass"`
In the server components that read branding:
`theme: (project.brand_theme as ...) ?? "glass"` (project + share pages).
And the workspace's initial branding-state default `theme: "glass"`.

## Pitfall
Forgetting step 2 means project pages go Glass but the dashboard/login stay
dark — exactly the "theme not standard across pages" complaint that triggered
this. All three layers must move together.
