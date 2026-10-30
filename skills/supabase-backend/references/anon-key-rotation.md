# Anon Key Rotation Diagnostic

When Supabase returns `{"message":"Invalid API key"}` on every call, but the key
looks correct (right length, not truncated), the key may have been **rotated** in the
Supabase dashboard since it was last copied to `.env.local`.

## Diagnostic: decode the JWT payload

The Supabase anon key is a JWT. Its payload (base64) contains a `ref` field that
identifies the project. Decode it to confirm the key belongs to the right project:

```python
import base64, json
key = "eyJhbG..."  # the suspect anon key
parts = key.split('.')
payload = json.loads(base64.urlsafe_b64decode(parts[1] + '=='))
print(f"ref: {payload['ref']}")  # must match the Supabase URL ref
print(f"role: {payload['role']}")  # must be 'anon'
print(f"iss: {payload['iss']}")   # must be 'supabase'
```

If `ref` doesn't match the project ref in your URL (`https://<ref>.supabase.co`),
the key is for a DIFFERENT project. If `ref` matches but the API still rejects it,
the key was **rotated** — the Supabase dashboard issued a new key and the old one
is invalid.

## Fix: get the current key from the Supabase dashboard

1. Supabase dashboard → your project → **Settings → API**.
2. Copy the **`anon` `public`** key (may be labeled "Publishable key" in newer
   dashboards, prefixed `sb_publishable_`).
3. Paste into `.env.local` (`NEXT_PUBLIC_SUPABASE_ANON_KEY=...`) or directly into
   the hardcoded `createClient()` call if using P43 bypass.
4. Redeploy (Vercel env vars or git push).

## Trap: Vercel has the NEW key, .env.local has the OLD one

A common failure mode: the live Vercel deployment has the correct (current) key
set in the Vercel dashboard env vars, so the deployed app works fine. But
`.env.local` on disk still has the OLD (rotated) key. Probing from the agent's
terminal or hardcoding from `.env.local` will fail with "Invalid API key" while
the live app still works.

**Diagnostic**: compare the working Vercel env key (from the Vercel dashboard)
with the `.env.local` key. If they differ, `.env.local` is stale. Update it.

## Verification after fix

```python
import hashlib
# Compare old vs new
old_key = "<from .env.local before fix>"
new_key = "<from Supabase dashboard>"
print(hashlib.md5(old_key.encode()).hexdigest())
print(hashlib.md5(new_key.encode()).hexdigest())
# They MUST differ if rotation occurred; if identical, the key was never rotated
```