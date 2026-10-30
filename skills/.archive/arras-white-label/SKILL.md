---
name: arras-white-label
description: White-label LunaV as ARRAS without forking.
---

# ARRAS White-Label Pattern

## Goal
Deploy ARRAS as a branded instance of the existing LunaV codebase, with its own DB/storage/deploy, while keeping LunaV production untouched.

## Core pattern
- One repo, one codebase.
- `src/lib/branding.ts` returns config from `NEXT_PUBLIC_APP_MODE=lunav|arras`.
- Feature flags in brand config control ARRAS-only UI.
- All ARRAS-specific writes stay local/feature-flagged until ARRAS gets its own Supabase project.

## Setup
1. Create new Supabase project for ARRAS.
2. Add ARRAS-specific migration files under `supabase/`.
3. Create new Vercel project pointing at same repo.
4. Set ARRAS env vars in Vercel: `NEXT_PUBLIC_APP_MODE=arras`, Supabase URL/anon key, R2 config if separate bucket/prefix.
5. **Deploy Edge Functions** — ARRAS Supabase starts with ZERO functions deployed. Every feature that uploads files (GLB, photos, docs) needs the `r2-presign` Edge Function. Porting features from LunaV/CDM is not enough — the function code exists in `supabase/functions/` but is never deployed until you do it.
   ```bash
   cd ~/ARRAS
   supabase link --project-ref lxmmxpxjercmhmiuqegq
   supabase functions deploy r2-presign
   supabase functions deploy r2-list
   supabase functions deploy notify-admin
   ```
   Then set R2 secrets via Dashboard → Edge Functions → r2-presign → Secrets: `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, `R2_PUBLIC_BASE`.
6. In the 3D tab model sidebar, add a dropdown to select the spatial model; keep selection local-only for demos.
7. **Vercel env var visibility:** `NEXT_PUBLIC_*` variables must use `visibility: config`, not `secret`. If Vercel complains, look for the Visibility field in the env var form and switch it.

### PITFALL — porting features that reference missing API routes
When porting a feature from LunaV or CDM to ARRAS, verify every `fetch('/api/...')` in the ported code has a matching `src/app/api/<name>/route.ts`. A context or component that calls `/api/dem-data`, `/api/presets`, `/api/terrain`, etc. will 404 on ARRAS if those routes were not included in the port. After any port, grep the new components for `fetch(` and confirm each endpoint exists in `src/app/api/`. This check catches gaps that TypeScript compilation does not — the code compiles against types, not runtime routes.

### PITFALL — porting features that need new DB tables
Ported code that reads/writes DB tables (e.g. `simulation_runs`, `simulation_presets`) will 500 until the migration is applied to the ARRAS Supabase project. After creating migration files under `supabase/migrations/`, apply them to the target project's SQL Editor. A feature is not live until both the code is deployed AND the migration is run.

### PITFALL — sharing R2 across projects (LunaV → ARRAS)
When ARRAS should reuse LunaV's R2 bucket instead of creating a new one, you need LunaV's R2 credentials: `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, `R2_PUBLIC_BASE`. These are stored as Supabase secrets on the LunaV project, not in `.env.local` or Vercel. If you cannot access them, the user must provide them from the Cloudflare R2 dashboard. Do not block on this — ask for the 5 values directly.

### PITFALL — Vercel env inspection requires project link
To inspect or modify Vercel env vars, the local repo must be linked: `vercel link --project <name> --yes`. Without this, `vercel env list` fails with "codebase isn't linked to a project".

## Feature gating rules
- Spatial tab, layer toggle, device palette, and spatial model selector must all be gated by `appFeatures.*`.
- LunaV mode must never show ARRAS UI.
- Do not hardcode one client's brand copy in shared components unless it comes from project branding/config.

## DB isolation
- Never apply ARRAS migrations to LunaV's live Supabase.
- Keep ARRAS spatial selection local-only until ARRAS DB is live.
- When ARRAS DB is ready, re-enable persistence in `saveProjectSpatialModel` and apply migrations to the ARRAS project only.

## Fresh Supabase project schema apply order
When applying schema to a brand-new Supabase project:
1. Create all tables **without** inline `references public.other_table(id)` FK clauses.
2. Add FK constraints afterward via `ALTER TABLE ... ADD CONSTRAINT ... FOREIGN KEY (...) REFERENCES ...`.
3. Enable RLS after FK constraints.
4. Create policies.
5. Create `SECURITY DEFINER` RPCs last.

This avoids `42P01: relation does not exist` errors when tables reference each other during creation.

## Clean SQL script format for copy-paste deploy
When the user wants a single file to paste into Supabase SQL Editor:
- Strip all `--` comment lines from the combined script.
- Keep only pure SQL statements, one per line.
- Preserve statement order: tables first, then FKs, then RLS, then policies, then RPCs.
- Deliver as `.sql` in a known path, e.g. `/Users/kamarulhk/ARRAS/supabase/apply_all_migrations_clean.sql`.

## Repo duplication / fork-to-new-repo pattern
If Vercel cannot point the existing project at the correct branch, or the user wants full isolation, duplicate the repo into a new ARRAS repo under the same GitHub account:
1. `git clone --mirror https://github.com/kingkymaru-glitch/lunavsolution.git /tmp/lunavsolution-mirror.git`
2. `cd /tmp/lunavsolution-mirror.git && git push --mirror https://github.com/kingkymaru-glitch/ARRAS.git`
3. Clone the new repo: `rm -rf ~/ARRAS && git clone https://github.com/kingkymaru-glitch/ARRAS.git ~/ARRAS`
4. Checkout the ARRAS branch: `cd ~/ARRAS && git checkout arras/reservoir-tab`
5. Merge into `main` if the new repo is otherwise empty: `git checkout main && git merge arras/reservoir-tab --no-edit`
6. Rebrand: `package.json` `name` → `arras`, `.env.example` defaults to `NEXT_PUBLIC_APP_MODE=arras`, replace hardcoded LunaV brand strings in pages/layout/login/viewer/R2 CORS.
7. Commit and push: `git add -A && git commit -m "chore: ARRAS identity defaults" && git push origin main`

## Admin bootstrap
To make users admin in ARRAS:
1. Create users in Supabase Dashboard → Authentication → Users (check **Email confirmed**).
2. Run `/Users/kamarulhk/ARRAS/supabase/admin_setup.sql` in SQL Editor: expands allowed roles to `admin` and updates matching emails.
3. For pre-creation without passwords, insert into `auth.users` with `email_confirmed_at=now()` and `role='authenticated'`.

## Deployment
- ARRAS gets its own Vercel project; LunaV Vercel project stays untouched.
- Connect Vercel to the new `kingkymaru-glitch/ARRAS` repo, not the old `lunavsolution` repo.
- Env vars: `NEXT_PUBLIC_APP_MODE=arras`, ARRAS Supabase URL/anon key, visibility `config`.
- After changing the Git repo, delete the old Vercel project if needed, then create fresh from the ARRAS repo.

## References
- `references/arras_spatial_pattern.md`
