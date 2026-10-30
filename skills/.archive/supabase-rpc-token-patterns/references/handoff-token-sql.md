# Corrective migration: handoff token without pgcrypto

Apply this in the Supabase SQL Editor when `mint_handoff_token` 404s with
`function hmac does not exist`. The functions reference `public.projects` and
`public.project_nodes` — adjust table/column names to your schema.

```sql
-- 1) Store the minted token on the project row (binds token <-> project).
alter table public.projects add column if not exists handoff_token uuid;

-- 2) Mint: owner-verified random UUID, persisted on the row.
create or replace function public.mint_handoff_token(p_project_id uuid)
returns text language plpgsql security definer set search_path = public as $$
declare
  v_owner uuid;
  v_token uuid := gen_random_uuid();
begin
  select owner_id into v_owner from public.projects where id = p_project_id;
  if v_owner is null then raise exception 'Unknown project'; end if;
  if v_owner <> auth.uid() then raise exception 'Not project owner'; end if;
  update public.projects set handoff_token = v_token where id = p_project_id;
  return v_token::text;
end; $$;
grant execute on function public.mint_handoff_token(uuid) to authenticated;

-- 3) Verify: token must match the one minted for THIS project.
create or replace function public.upsert_project_node(
  p_lunav_project_id uuid,
  p_handoff_token text,
  p_name text, p_description text,
  p_lon double precision, p_lat double precision,
  p_visibility text, p_share_token uuid default null
)
returns public.project_nodes language plpgsql security definer set search_path = public as $$
declare
  v_owner uuid; v_stored text; v_row public.project_nodes;
begin
  select owner_id, handoff_token::text into v_owner, v_stored
  from public.projects where id = p_lunav_project_id;
  if v_owner is null then raise exception 'Unknown project'; end if;
  if v_stored is null or v_stored <> p_handoff_token then
    raise exception 'Invalid handoff token';
  end if;
  insert into public.project_nodes (
    lunav_project_id, lunav_share_token, name, description,
    lon, lat, visibility, handoff_token
  ) values (
    p_lunav_project_id, p_share_token, p_name, p_description,
    p_lon, p_lat, p_visibility, p_handoff_token
  )
  on conflict (lunav_project_id) do update set
    lunav_share_token = excluded.lunav_share_token,
    name = excluded.name, description = excluded.description,
    lon = excluded.lon, lat = excluded.lat, visibility = excluded.visibility,
    handoff_token = excluded.handoff_token, created_at = now()
  returning * into v_row;
  return v_row;
end; $$;
grant execute on function public.upsert_project_node(
  uuid, text, text, text, double precision, double precision, text, uuid
) to anon, authenticated;
```

## Verification probe (run from the agent, needs only the anon key)
```js
const { createClient } = require('@supabase/supabase-js');
const sb = createClient(URL, ANON);
// column present?
await sb.from('projects').select('handoff_token').limit(1);
// function runs (anon can't own -> expect 'Unknown project', NOT 'function does not exist')
const r = await sb.rpc('mint_handoff_token', { p_project_id: '00000000-0000-0000-0000-000000000000' });
console.log(r.error?.message); // 'Unknown project' == fixed
```
Expect `'Unknown project'` (proves the function runs). `'function ... does not
exist'` means the migration did not apply or the body still uses hmac.

## Note on the consumer carrying the token
The producer app should pass `name` + `client_share_token` via the handoff URL
query string so the consumer can pre-fill and auto-bind the public deep-link —
no manual token paste. The consumer reads `p_share_token` into
`project_nodes.lunav_share_token` for public pins (→ `/share/<token>`); private
pins store NULL (→ `/login?project=<id>`).
