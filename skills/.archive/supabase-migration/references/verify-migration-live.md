# Verify a Supabase migration is LIVE without `supabase db push`

## When to use
The SQL was pasted into the Supabase SQL Editor by the user (or applied another way), but the
agent host has no `supabase` CLI link, no access token, and no `service_role` key. You must
CONFIRM the tables/RPCs/functions actually exist in the live project — not assume the
"Success. No rows returned" toast means the whole file applied (it often does NOT; one bad
statement aborts the rest mid-file).

## What you need
- The project URL + **anon** key. These are already in the sibling app's `.env.local`
  (e.g. R-Tessera reads LunaV's anon key from `ss-rover-cloud/.env.local`). Copy them into the
  target app's `.env.local` as `VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY` — never hand-type
  the 208-char JWT (shell mangles it). Use a Node script, not `node -e`, to copy.
- `@supabase/supabase-js` resolvable → run the probe from inside a dir that has it
  (e.g. the R-Tessera repo root). CommonJS `require`, not ESM `import`, to avoid resolution pain.

## Probe template (copy, fill URL/key, run, then delete)
```js
const fs = require('fs');
const env = fs.readFileSync('/path/to/app/.env.local','utf8');
const url = env.match(/VITE_SUPABASE_URL=(.*)/i)[1].trim();
const anon = env.match(/VITE_SUPABASE_ANON_KEY=(.*)/i)[1].trim();
const { createClient } = require('@supabase/supabase-js');
(async () => {
  const sb = createClient(url, anon, { auth: { persistSession: false } });
  const dummy = '00000000-0000-0000-0000-000000000000';
  const t = await sb.from('project_nodes').select('id').limit(1);
  console.log('project_nodes ->', t.error ? 'ERR '+t.error.message : 'OK');
  const r = await sb.rpc('upsert_project_node', { p_lunav_project_id: dummy, p_handoff_token:'x',
    p_name:'t', p_description:'', p_lon:0, p_lat:0, p_visibility:'public', p_share_token:null });
  console.log('upsert_project_node ->', r.error ? 'ERR '+r.error.message : 'unexpected OK');
  const m = await sb.rpc('mint_handoff_token', { p_project_id: dummy });
  console.log('mint_handoff_token ->', m.error ? 'ERR '+m.error.message : 'unexpected');
})().catch(e => { console.error('FATAL', e); process.exit(1); });
```

## Error-signature table (the part that matters)
| Symptom | Meaning | Action |
|---|---|---|
| `select` -> OK (even rows=0) | table exists | pass |
| RPC -> `PGRST202` / `function ... does not exist` / schema cache miss | RPC NOT applied | re-run that function's DDL |
| RPC -> `Unknown project` / `Not project owner` | function EXISTS + RAN (rejected dummy) | **PASS** -- live |
| browser console 404 on RPC | often a STALE deploy, not a missing fn | probe live DB before touching client code |
| `create or replace function ... returns TABLE` over existing `returns jsonb` | Postgres REJECTS return-type change -> fn stays old | keep same return type; extend jsonb |

## Gotchas
- Calling `rpc('get_shared_project', { p_token })` when live param is `share_token` yields a
  "does not exist" FALSE NEGATIVE. Match the live param name (check schema.sql).
- Delete the probe `.cjs` after running (`rm`); it is NOT feature code.
- A green build + HTTP 200 from the live URL only proves the app deployed -- NOT that the DB
  schema is applied. The probe is the separate, required check.
