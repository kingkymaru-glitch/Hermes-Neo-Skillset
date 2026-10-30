-- Supabase "creator must have the app" gate (SkyPin pattern).
-- Anon (browser) clients can SELECT rooms/participants (view-only) but CANNOT
-- create or join a room. App-authenticated users can. Enforced in the RPC, not
-- just the UI, so a crafted browser call still fails.

-- RLS: allow anon + authenticated to READ live state (view-only tier needs it)
create policy "rooms readable by all" on rooms
  for select using (true);
create policy "participants readable by all" on participants
  for select using (true);

-- But writes require a logged-in user (app only; email magic-link)
create policy "rooms writable by app users" on rooms
  for all using (auth.uid() is not null) with check (auth.uid() is not null);
create policy "participants writable by app users" on participants
  for all using (auth.uid() is not null) with check (auth.uid() is not null);

-- RPC guard: raise auth_required for anon (the browser can't call this)
create or replace function create_room(p_room_skin text, p_all_app boolean)
returns json language plpgsql security definer as $$
declare
  v_id uuid;
begin
  if auth.uid() is null then
    raise exception 'auth_required';   -- browser/anon caller is rejected
  end if;
  insert into rooms (creator_id, room_skin, all_app)
  values (auth.uid(), p_room_skin, p_all_app)
  returning id into v_id;
  -- ... build share token, TTL, etc.
  return json_build_object('id', v_id);
end; $$;

-- Same guard on join_room, upload_skin, report, ban.
-- Browser viewer uses the anon client: it CAN fetch the roster + positions but
-- can never create_room/join_room, so it stays view-only by construction.
