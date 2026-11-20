# Supabase <-> GitHub link (safety + auto-deploy layout)

## Linking is safe across projects
- The Supabase<->GitHub connection is **PER SUPABASE PROJECT** (an OAuth grant +
  repo connection). Linking a 2nd/3rd project to the SAME GitHub account/org does
  **NOT** merge databases — each project stays isolated by its own ref. No conflict
  even if other projects (e.g. MARU/RINA) already link the same GitHub.
- **Cross-account note:** Supabase accounts are independent of GitHub. A project
  under `inventedmaru@gmail.com` can authorize the same GitHub as one under
  `kingkymaru`. Just be logged into the correct Supabase account when you click Link.
- **Benefit:** enables `supabase` CLI migration tracking + optional CI auto-deploy
  of migrations / edge functions from the repo.

## Auto-deploy needs `supabase/migrations/` layout
- Auto-deploy expects files at `supabase/migrations/<YYYYMMDD>_<name>.sql`
  (see P14/P15). SQL kept in a non-standard folder (e.g. `Supabase/catches.sql`)
  will NOT auto-apply until you restructure into `supabase/migrations/`.
- **Linking alone gives CLI access; it does NOT silently run your existing SQL.**
  You still apply DDL via `supabase db push --linked` (P14).
- Verify applied state with `select count(*) from <table>` after a push.

## Founder concern pattern (recurring)
Question: "If I link this project to my GitHub, will it conflict with the 2 other
projects already linked?" -> Answer: no DB merge, isolated by ref, safe to link.
The only real trap is the auto-deploy folder layout above.
