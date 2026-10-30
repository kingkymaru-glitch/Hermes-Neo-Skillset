# Two apps, ONE Supabase — owner-RPC writes, anon-view reads

Reusable pattern for splitting a system into a WRITER app and a READ-ONLY viewer app
that share a single Supabase project (no second backend, no second auth provider).

## The shape

- **Writer app (app A)** — e.g. LunaV Solutions. Authenticated users create/update rows.
- **Viewer app (app B)** — e.g. R-Tessera globe. Reads rows to render markers/nodes.
  Gets the **anon key only**; never the service-role key.

Both use the SAME project URL + anon key (key-copy hygiene: the anon key is public by
design; never paste the service-role key into a client bundle).

## RLS model

Table owner = the authenticated writer. Enforce ownership INSIDE a `security definer` RPC,
not via the client's `supabase.from(...).insert(...)` (which would need row-level INSERT
policies and exposes the table to the client). The RPC runs as the definer, validates
`auth.uid()`, then writes.

```sql
-- table owned by the writer app's auth users
create table public.cctv_cameras (
  id uuid primary key default gen_random_uuid(),
  project_id uuid,                 -- nullable: camera may be standalone (no parent project)
  owner uuid not null default auth.uid() references auth.users(id),
  name text not null,
  lon double precision not null,
  lat double precision not null,
  status text not null default 'active',
  created_at timestamptz not null default now()
);

-- optional linkage: deleting the parent must NOT delete cameras (use SET NULL, not CASCADE)
alter table public.cctv_cameras
  add constraint fk_project foreign key (project_id)
  references public.projects(id) on delete set null;

-- ownership policy: only the owner sees/edits their rows
create policy "owner rw" on public.cctv_cameras
  for all using (owner = auth.uid()) with check (owner = auth.uid());

-- writer RPC (security definer): client calls this instead of .insert/.update
create or replace function public.upsert_cctv_camera(
  p_project_id uuid,            -- required params FIRST
  p_name text,
  p_lon double precision,
  p_lat double precision,
  p_id uuid default null,       -- optional upsert key, LAST (42P13 ordering rule)
  p_comment text default null,
  p_status text default 'active'
) returns uuid language plpgsql security definer set search_path = public as $$
declare v_id uuid := p_id;
begin
  if v_id is null then
    insert into public.cctv_cameras (project_id, name, lon, lat, status, owner)
    values (p_project_id, p_name, p_lon, p_lat, p_status, auth.uid())
    returning id into v_id;
  else
    update public.cctv_cameras set project_id = p_project_id, name = p_name,
      lon = p_lon, lat = p_lat, status = coalesce(p_status, status)
    where id = v_id and owner = auth.uid();   -- can only edit own rows
  end if;
  return v_id;
end; $$;
grant execute on function public.upsert_cctv_camera(uuid, text, double precision, double precision, uuid, text, text)
  to authenticated;

-- read-only view for app B: anon-visible, owner column hidden
create or replace view public.cctv_cameras_public as
  select id, project_id, name, lon, lat, status, created_at
  from public.cctv_cameras;
grant select on public.cctv_cameras_public to anon;
```

## Client call (named args — order-independent after a param reorder)

```ts
const { data, error } = await supabase.rpc("upsert_cctv_camera", {
  p_project_id, p_name, p_lon, p_lat,        // required
  p_id: editingId ?? null,                   // optional
  p_status: "active",
});
```
Because the call uses NAMED arguments, reordering the function's params (e.g. to fix a
42P13) is transparent to the client — no front-end change needed.

## Viewer app reads via the anon view

```ts
const { data } = await supabase.from("cctv_cameras_public").select("*");
```
App B only ever touches `_public` views → no write path, no RLS bypass, no service key.

## Deep-link handoff (writer → viewer)

When app A needs to send the user to app B with a pre-selected record, mint a token and
embed it in the URL instead of passing raw IDs:

```sql
create or replace function public.mint_handoff_token(p_project_id uuid)
returns text language plpgsql security definer set search_path = public as $$
declare v text;
begin
  v := encode(gen_random_bytes(18), 'hex');
  insert into public.handoff_tokens (token, project_id, owner, expires_at)
  values (v, p_project_id, auth.uid(), now() + interval '15 minutes');
  return v;
end; $$;
grant execute on function public.mint_handoff_token(uuid) to authenticated;
```

App A: `window.open(\`https://rtessera.app/?link=1&project=${id}&token=${await mint()}\`)`.
App B: validate the token via an anon-readable RPC, then upsert the node / focus the camera.

## Pitfalls (from ROVER-KIT / LunaV 2026-08)
- **42P13 param ordering**: once a param has a DEFAULT, every later param needs one too.
  Put required params first (see `sql-returns-table-column-order.md` Cause C).
- **Don't CASCADE on the parent FK** — a deleted Studio project would wipe cameras. Use
  `on delete set null` so a camera can become standalone.
- **`project_id` NULLABLE** when a record may legitimately live outside any parent
  project; surface an "Unassigned / standalone" filter in the UI.
- **Grant signature must match the param order** after a reorder, or the grant silently
  no-ops → "permission denied" for authenticated callers.
- **Never give app B the service role.** Anon-only views + the anon key keep the read
  side unprivileged even if the viewer is fully public.
- **Show write errors INSIDE the modal**, not in the page behind it — an error rendered
  behind an overlay reads as "the button did nothing" (caught in the field, 2026-08-25).
