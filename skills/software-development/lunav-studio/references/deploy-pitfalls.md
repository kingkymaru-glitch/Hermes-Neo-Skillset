# Supabase Edge Function Deploy Pitfalls

## Pitfall 1: "Via AI Assistant" auto-names functions

When deploying an edge function via the Supabase dashboard:

1. Navigate to Edge Functions → "Deploy a new function"
2. Three deployment options appear:
   - **Via Editor** (code icon) — You type the function name yourself ✅
   - **Via CLI** (terminal icon) — Local deploy via `supabase functions deploy`
   - **Via AI Assistant** (diamond icon) — ⚠️ **DANGER**: This auto-names your function with a random adjective-noun pair (e.g., "bright-action", "purple-forest")

If you accidentally deploy via AI Assistant, the function gets a random name that doesn't match what your codebase expects (e.g., `r2-list`). You'll need to delete and redeploy.

**Always use "Via Editor" and type the name manually.**

## Pitfall 2: CLI logged into wrong Supabase account

The `supabase` CLI may be authenticated to a different account than the project you need:

```bash
supabase projects list    # Check: if you see AnglerGO/r-tessera, you're on inventedmaru@gmail.com
```

To switch to kingkymaru (for LunaV/LUNASCAN):
```bash
supabase logout
supabase login    # opens browser → log in as kingkymaru
```

## Pitfall 3: Running migration before schema.sql

The migration file `20260805_lunascan_import.sql` adds a `source` column to the `models` table. It will fail with `relation "public.models" does not exist` if `schema.sql` hasn't been run first.

**Run order:** `schema.sql` FIRST, then individual migrations. The migration is redundant if `schema.sql` already includes the column — but harmless (idempotent).