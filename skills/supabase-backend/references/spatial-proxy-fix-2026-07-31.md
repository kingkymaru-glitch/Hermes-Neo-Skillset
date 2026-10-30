# Spatial Proxy Fix - 2026-07-31

## Problem
After deploying the proxy model isolation feature, markers and their evidence photos disappeared from the client share portal (`/share/[token]`), while the owner view showed them correctly.

## Root Cause Analysis

### 1. Migration Applied to Wrong Version
The migration file `20260731_proxies_model_id.sql` was applied to the live database, but it contained an **OLD version** of the `get_shared_project` RPC that was missing critical marker fields.

### 2. Missing Fields in RPC
The RPC was missing:
- `model_id` for markers (needed for filtering)
- `kind` (needed for rendering)
- `geometry_json` (needed for rendering)
- `photos_json` (needed for evidence photos)

### 3. Correct Fix Already Existed
The file `supabase/phase3_share_nodes_fix.sql` contained the correct SQL with all fields, but it was never applied to the live database.

## Fix Applied
1. Updated `20260731_proxies_model_id.sql` to include all marker fields
2. Applied the corrected RPC to live database via `supabase db push --linked`

## Key Lesson
**Always verify that migration files contain the CURRENT version of RPCs, not stale versions from months ago.** A migration file can be updated after initial application, and `supabase db push` will re-apply it (since it uses `create or replace`).

## Verification Steps
1. Test owner view - markers should appear
2. Generate share link - markers should appear
3. Check RPC output directly:
   ```sql
   select get_shared_project('<token>') as bundle;
   ```
4. Verify `models[0].markers[].kind` is present
5. Verify `models[0].markers[].photos_json` is populated