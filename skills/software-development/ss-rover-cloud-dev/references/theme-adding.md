# Adding a new client theme to LunaV (Appearance -> Theme)

LunaV themes are driven by a `data-theme="<name>"` attribute on `<html>` plus a
CSS block `html[data-theme="<name>"] { --var: ... }` in `src/app/globals.css`.
The selected theme is stored in `projects.brand_theme` (text + CHECK constraint).

## Steps (all required)

1. **CSS** — add a block in `src/app/globals.css` after the existing theme blocks:
   ```css
   html[data-theme="glass"] {
     --dash-void: #0b1020;
     --dash-panel: rgba(28, 36, 58, 0.55);
     --dash-panel-raised: rgba(44, 54, 82, 0.62);
     --dash-inset: rgba(10, 14, 26, 0.55);
     --hairline: rgba(180, 200, 255, 0.18);
     --hairline-strong: rgba(180, 200, 255, 0.32);
     --glass: rgba(30, 38, 64, 0.55);
     --mb-turquoise: #0a84ff;
     --mb-turquoise-dim: rgba(10, 132, 255, 0.18);
     --mb-ice: #5ac8fa;
     --mb-amber: #ff9f0a;
     --mb-amber-dim: rgba(255, 159, 10, 0.16);
     --mb-red: #ff453a;
     --mb-red-dim: rgba(255, 69, 58, 0.16);
     --txt-primary: #f2f5ff;
     --txt-secondary: #aeb9d6;
     --txt-tertiary: #6c789b;
     --glow-turquoise: 0 0 22px rgba(10, 132, 255, 0.45);
     --glow-amber: 0 0 18px rgba(255, 159, 10, 0.4);
     --glow-red: 0 0 18px rgba(255, 69, 58, 0.4);
   }
   ```
   (The "Glass" theme above was the iOS-style frosted-glassmorphism example —
   highly translucent `rgba` surfaces so content shows through.)

2. **Type union** — add the new name to the `"dark" | "light" | "midnight"` union in
   EVERY place it appears:
   - `src/lib/types.ts`: `Project.brand_theme` and `ClientBranding.theme`
   - `src/components/ProjectWorkspace.tsx`: the three `theme:` type annotations
     (branding prop, useState, saveBranding param)
   - `src/app/share/[token]/page.tsx`: the `as "dark" | "light" | "midnight"` cast
   - `src/app/project/[id]/page.tsx`: same cast

3. **Appearance selector** — add the name to the button list in
   `ProjectWorkspace.tsx` (Theme row):
   ```tsx
   {(["dark", "light", "midnight", "glass"] as const).map((t) => ( ... ))}
   ```

4. **DB CHECK constraint** — `brand_theme` has `CHECK (brand_theme IN (...))`.
   A new value is REJECTED on save unless you extend it (see
   `supabase-js-column-pitfalls/references/working-migrations.md` §5). Ship a
   migration file under `supabase/migrations/` and have the user run it in the
   Supabase SQL Editor (no CLI/service-key access from this environment):
   ```sql
   ALTER TABLE projects
     DROP CONSTRAINT IF EXISTS projects_brand_theme_check;
   ALTER TABLE projects
     ADD CONSTRAINT projects_brand_theme_check
     CHECK (brand_theme IN ('dark', 'light', 'midnight', 'glass'));
   NOTIFY pgrst, 'reload schema';
   ```

## Pitfall
Missing ANY of steps 2–4 breaks the build (step 2) or silently rejects the save
(step 4). The DB CHECK-constraint step is the one most easily forgotten because
the frontend builds green without it.
