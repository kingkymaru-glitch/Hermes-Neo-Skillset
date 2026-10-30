# Verify a live Supabase schema is ACTUALLY applied — anon-key Node probe

When you cannot `supabase db push` (CLI unlinked, no access token, no service
role, no local Postgres), you can still PROVE the live DB has your tables/RPCs
using ONLY the public anon (Publishable) key — the same key the browser bundle
already ships. This is the verification pattern used when R-Tessera (Vite/Cesium)
was wired to read LunaV's shared Supabase project (okzmblyboudjffaifixa) and the
migration had been run in the Dashboard SQL Editor but never confirmed.

## Why this is needed
`git push` -> Vercel builds the app but NEVER runs migrations (see P35 /
vercel-deploy-does-not-run-migrations). A migration file existing in the repo is
NOT proof it reached prod. The only way to know is to hit the live DB. The anon
key is enough for read/existence checks.

## The probe (run from a dir with @supabase/supabase-js installed)
Copy the project's anon key + URL out of the consuming app's `.env.local` (or a
sibling repo) — do NOT paste the key through chat (P8: it truncates). Read it
from disk:

```js
const fs = require('fs');
const env = fs.readFileSync('/path/to/.env.local', 'utf8');
const url = env.match(/VITE_SUPABASE_URL=(.*)/i)[1].trim();
const anon = env.match(/VITE_SUPABASE_ANON_KEY=(.*)/i)[1].trim();
const { createClient } = require('@supabase/supabase-js');
(async () => {
  const sb = createClient(url, anon, { auth: { persistSession: false } });
  const dummy = '00000000-0000-0000-0000-000000000000';
  // 1) table exists?  anon SELECT is granted on the table
  const r1 = await sb.from('project_nodes').select('id').limit(1);
  console.log('project_nodes ->', r1.error ? 'ERR: ' + r1.error.message : 'OK rows=' + (r1.data?.length ?? 0));
  // 2) RPC exists AND ran?  dummy args -> a DOMAIN error means it executed
  const r4 = await sb.rpc('upsert_project_node', {
    p_lunav_project_id: dummy, p_handoff_token: 'x', p_name: 't',
    p_description: '', p_lon: 0, p_lat: 0, p_visibility: 'public', p_share_token: null,
  });
  console.log('upsert_project_node ->', r4.error ? 'ERR: ' + r4.error.message : 'OK (unexpected)');
})().catch(e => { console.error('FATAL', e); process.exit(1); });
```

## Reading the result (the key insight)
The ERROR MESSAGE tells you whether the object exists and ran:

| Probe result | Meaning |
|---|---|
| `select` -> no error, `data=[]` | table EXISTS (just empty) |
| `select` -> `error: relation "x" does not exist` | table MISSING |
| `rpc` -> `error: Unknown project` / `Not project owner` | function EXISTS and RAN (dummy arg hit your RAISE) — this is SUCCESS for existence |
| `rpc` -> `error: Could not find the function public.fn(p_token) in the schema cache` | function MISSING OR wrong parameter name (param-name trap below) |
| `rpc` -> `error: function public.fn() does not exist` | function MISSING |

So a domain error from an RPC (`Unknown project`) is a PASS for "the function is
live and executes" — it proves the migration applied. Never treat it as failure.

## TRAP: rpc() matches by PARAMETER NAME, not position
Supabase's JS `rpc(name, params)` matches the keys of `params` to the function's
PARAMETER NAMES — not order, not types. If the live function is declared
`get_shared_project(share_token uuid)` and you call
`rpc('get_shared_project', { p_token: dummy })`, Supabase looks for a param named
`p_token`, finds none, and reports `Could not find the function ...(p_token) in
the schema cache` — which looks identical to "function missing" but is really a
NAME mismatch. ALWAYS call with the exact declared param name (`share_token`).
Grep the function definition (`create or replace function ... (param_name type)`)
in the repo to get the right name before probing.

## Pattern: two apps intentionally share ONE Supabase project
R-Tessera (Vite + Cesium globe) and LunaV (Next + Three.js inspection) are
separate repos/deploys but share ONE backend (okzmblyboudjffaifixa). The link
architecture: LunaV = owner/writer (authenticated, RLS-enforced writes);
R-Tessera = anon reader (reads the public `project_nodes` index + calls owner-
validated RPCs with a handoff token minted by LunaV). This is a valid
"link, don't merge" design — no dual WebGL, no codebase merge.

To give the reader app the keys without pasting them: copy from the writer
repo's `.env.local` into the reader's `.env.local` as `VITE_SUPABASE_URL` /
`VITE_SUPABASE_ANON_KEY` via a throwaway Node script (read source file -> write
target file; never echo the key into terminal history). Anon key is safe to
expose (same exposure as the browser bundle) but must be COMPLETE (P8).

RLS for this shape:
- Writer tables: owner-all via RLS (`organization_id = my_org_id()` etc.).
- Reader index table (`project_nodes`): `anon + authenticated` SELECT all (the
  globe marker is meant to be visible to everyone); INSERT/UPDATE/DELETE guarded
  by an owner-validated RPC (`upsert_project_node` checks a handoff token minted
  by the writer via `mint_handoff_token`). The reader app never holds a service
  role and never writes directly.
- Never ship a service-role key to the reader. Anon key + RPCs only.

## Cleanup
Delete the probe scripts after running (`rm -f verify_schema*.cjs`) — they are
throwaway, not feature code. Confirm with `git status --porcelain` that nothing
stray was left in the repo.
