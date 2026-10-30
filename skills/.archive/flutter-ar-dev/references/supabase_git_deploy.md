# Supabase via GitHub — deploy runbook (Flutter/AR app)

Pattern used for SkyPin (Flutter + Supabase, pushed to private GitHub repo).

## Repo layout for Git-driven Supabase
```
skypin/
  app/                     # Flutter project (lib/, android/, ios/, assets/)
  supabase/
    config.toml            # read by `supabase` CLI / Supabase Git deploy
    migrations/
      0001_init.sql        # schema: tables, RLS, RPCs, buckets SQL
  supabase_schema.sql      # also kept at root for easy SQL-Editor paste
  DESIGN.md
  NARRATIVE.md
```
- `.gitignore` at root must exclude Flutter build output (`app/build/`, `.dart_tool/`,
  etc.) so the ~80 MB release APK is NOT committed. Also ignore `.env`.
- Scan before first push: `grep -rniE "eyJ|ghp_|supabase.co|api[_-]?key|secret|password|BEGIN .*PRIVATE KEY"` — must come back empty except placeholder `[REDACTED]` values.

## Option A — Supabase dashboard Integrations (true "through GitHub")
1. Supabase dashboard → your project → Integrations → GitHub → connect `<owner>/<repo>`.
2. On each push to the linked branch, Supabase applies `supabase/migrations/*.sql`.
3. STILL MANUAL (Git deploy does NOT do these):
   - Create Storage buckets `skypins`, `skins` (public).
   - Upload storage files (e.g. 4 procedural `.glb` skins; arrow.glb is generated locally at `app/assets/skins/`).
   - Set skin asset URLs in app config (`SkyPinConfig.skinUrls`).
   - Auth → URL config: Site URL / redirect to `skypin://login` (Android + iOS scheme).

## Option B — `supabase` CLI from a logged-in machine
```
supabase login                       # needs access token (browser)
supabase link --project-ref <REF>    # REF from project URL / settings
supabase db push                     # applies migrations/ to live DB
```
Works only when the CLI has a session. On a fresh agent machine without a token, skip and use Option A.

## App-side config (always manual)
- `app/lib/config.dart`: `supabaseUrl`, `supabaseAnonKey` → paste real values, or
  pass via `flutter build apk --dart-define=SUPABASE_URL=... --dart-define=SUPABASE_ANON=...`
  and read with `String.fromEnvironment`. The anon key is client-safe (RLS enforces access).

## What to tell the user honestly
"GitHub push = code is safe + schema migrations are wired. Fully runnable app = schema via
GitHub + (1) paste URL/anon key, (2) create 2 buckets + upload skins, (3) set Auth redirect
URL. Git deploy covers the DB, not storage or app config."
