# Spatial Proxy Model Isolation Fix (2026-07-29)

## Problem
- Proxy shapes disappeared from 3D view
- Console error: "Failed to load resources: the server responded with a status of 400"
- Spatial Proxy toolbox non-functional

## Root Cause
Migration `20260731_proxies_model_id.sql` added `model_id` column to `proxies` table,
but migration was NOT applied to live Supabase database. RLS policy for proxies
checks `proxies.model_id` which didn't exist → policy evaluation failed → 400 error.

## Three-Part Fix

### 1. Apply Migration to Live Database
```bash
cd ~/Documents/ss-rover-cloud
supabase db push --linked
```

### 2. Update Proxy Filtering Logic
File: `src/components/ProjectWorkspace.tsx`

Before (broken):
```typescript
const proxiesForActiveModel = useMemo(
  () => activeModelId ? proxies.filter((p) => p.model_id === activeModelId) : [],
  [proxies, activeModelId],
);
```

After (fixed):
```typescript
const proxiesForActiveModel = useMemo(() => {
  // If no active model, show all proxies (backward compatibility)
  if (!activeModelId) return proxies;
  // Filter to proxies belonging to the active model
  return proxies.filter((p) => p.model_id === activeModelId || !p.model_id);
}, [proxies, activeModelId]);
```

### 3. Redeploy
```bash
npm run build
npx vercel --prod --yes
```

## Key Lesson
**ALWAYS apply migrations BEFORE deploying code that uses new columns.**
The 400 error was misleading - it looked like a client-side issue but was
actually a server-side RLS policy failure due to missing column.

## Verification
- Build: ✅ PASSED
- Deployment: ✅ SUCCESS  
- Live site: ✅ HTTP 200 (age: 0)
- Proxies: ✅ Rendering correctly