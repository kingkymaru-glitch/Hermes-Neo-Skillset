# Hardcoded Supabase anon key — bypass Vercel env-var setup

## When to use
- A Supabase-backed app (Vite, Next, etc.) that deploys to **Vercel** (git-push auto-deploy).
- The anon Supabase client returns `null` (→ "Supabase not configured" in the UI) on the
  **live** deploy, even though `.env.local` has valid `VITE_SUPABASE_URL` +
  `VITE_SUPABASE_ANON_KEY` (or `NEXT_PUBLIC_` equivalents).
- You confirmed the keys work locally; the failure is Vercel-only.

## Root cause
Vercel does NOT read `.env.local` (it's gitignored). It only injects environment
variables set in the **Vercel dashboard → Settings → Environment Variables**. A
`.env.example` with empty/placeholder values (the default in many repos) means the
build sees empty strings → the anon client init returns null → the app breaks
silently on the live site.

## Solutions (ordered by preference)

### 1. Set Vercel environment variables (dashboard, ~30 seconds)
Go to https://vercel.com → your project → Settings → Environment Variables.
Add `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` scoped to Production +
Preview + Development. Redeploy. This is the "correct" path — but it requires
manually copying values or being logged into Vercel (which the agent typically
isn't).

### 2. Hardcode in the client (code change, instant, zero Vercel config)
**This is safe for the ANON key only** — it is a PUBLIC key by design
(read-only + gated RPCs). The service-role key MUST NEVER be hardcoded.
```js
// Before (reads env vars — Vercel sees empty strings):
const url = import.meta.env.VITE_SUPABASE_URL;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
export function createSupabase() {
  if (!url || !anonKey) return null;
  return createClient(url, anonKey, { auth: { persistSession: false } });
}

// After (hardcoded anon key — works everywhere, no Vercel settings):
export function createSupabase() {
  return createClient(
    'https://<project>.supabase.co',
    'eyJhbG...<full-anon-jwt>',
    { auth: { persistSession: false, autoRefreshToken: false } },
  );
}
```
**Pitfall:** the anon key is a long JWT (208+ chars). Copying from truncated
terminal output (e.g. `grep` with `...` ellipsis) produces an invalid key →
"Invalid API key" error. Always verify the key length and md5 against the
source `.env.local` before pushing:
```bash
# Extract from LunaV env and compare
python3 -c "
import hashlib
with open('.env.local') as f:
    for line in f:
        if 'ANON_KEY=' in line:
            real = line.split('=',1)[1].strip()
with open('src/lib/supabaseClient.js') as f:
    import re
    match = re.search(r\"'eyJ[A-Za-z0-9._-]*'\", f.read())
    hard = match.group().strip(\"'\")
print(f'real={len(real)}chars md5={hashlib.md5(real.encode()).hexdigest()}')
print(f'hard={len(hard)}chars md5={hashlib.md5(hard.encode()).hexdigest()}')
print('MATCH:', real == hard)
"
```

## When NOT to hardcode
- The **service_role** key (never ship it).
- Any key you don't already ship in a browser bundle. The anon key is already
  in every LunaV client — hardcoding it adds zero exposure beyond what the
  browser already has.
