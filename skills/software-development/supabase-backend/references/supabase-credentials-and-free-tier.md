# Supabase credentials + free-tier project cap

## Access token vs. anon/service keys
- CLI auth/token: `sbp_...` from Dashboard → Account → Access Tokens.
- App anon key: `sb_publishable_...` or `eyJ...` — stored in `VITE_SUPABASE_ANON_KEY`.
- Management API (`/v1/projects/.../api-keys`) returns both kinds; the
  `sbp_...` token is the only one that authorizes `supabase projects create`.

## Free-tier project-cap trap
Each free-tier account org is capped at 2 active projects. When cap is hit,
`supabase projects create` returns:
`The following organization members have reached their maximum limits for the
number of active projects...`
Do not keep poking `projects create`; choose one of:
1. Use an existing project and add a new table.
2. Pause/delete an unused project in the Dashboard.
3. Use a different account that still has a slot.

## Credential lookup order
Before pasting/or requesting tokens, search:
1. Existing `.env.local` in the app root.
2. The app's `supabaseClient.js` / Supabase service wrapper for env var names.
3. Obsidian vault notes (`HermesProgress.md`, `Projects/*.md`) for project ref,
   URL, and known-good anon keys tied to a live account.
4. Keychain search: `security find-generic-password -s "supabase" -w`.
5. Filesystem: `cat ~/.supabase/creds*`, `cat ~/.netrc`.
6. If the user says a token exists and was generated on this Macbook, check vault
   notes for the live project ref and anon key before asking them to manually
   generate a new CLI token.

## Token secrecy
- NEVER echo/print/paste `sbp_...` tokens in tool output after the deploy step.
- `.env.local`/`.env` go in `.gitignore`; never commit them.
- If accidentally committed, remove from history with `git rm --cached` and
  amend the commit before pushing.

## .env.local in a repo that commits `dist/`
Some projects intentionally commit `dist/` while still ignoring `.env.local`.
Verify `.gitignore` has `.env.local` so build artifacts do not bake secrets
into the shipped bundle. Production env vars should come from Vercel project
settings, not local files.

## App-side Supabase client shape
```js
import { createClient } from '@supabase/supabase-js'
const url = import.meta.env.VITE_SUPABASE_URL
const key = import.meta.env.VITE_SUPABASE_ANON_KEY
export const isSupabaseConfigured = Boolean(url && key)
export const supabase = isSupabaseConfigured ? createClient(url, key) : null
```
Update `EdgeDataContext` to import `supabase` for persistence hooks; derive all
cloud status via a dedicated pair of state values rather than sprinkling
network flags through the store.
