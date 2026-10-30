# ROVER-KIT CCTV camera registry — shared LunaV/R-Tessera backend

Scope: extend the SINGLE shared Supabase project (the one both LunaV Solutions AND
R-Tessera use) with a CCTV camera registry, so an edge device (Pi5 / Luna EDGE YOLO)
can write detection events and R-Tessera can render camera nodes — with NO second
backend and NO second auth. This is the confirmed, built recipe (Phase 0 SQL + Phase 1
LunaV UI). Phases 2–5 are not built yet.

Code lives in `~/lunavsolution-code` (the active LunaV Solutions checkout).

## Architecture (who acts where)
- **LunaV Solutions (Next.js)** = camera registry UI. "Vision" tab on the Dashboard.
- **R-Tessera (CesiumJS)** = reads the shared `cctv_cameras` via an anon-granted
  SECURITY DEFINER view and renders camera nodes; gets a deep-link token from
  `mint_handoff_token`.
- **Pi5 / Luna EDGE** = writes person-detection events to `cctv_events` (Phase 3).
- **Shared Supabase** = the ONLY backend. Reuse the existing
  `mint_handoff_token(p_project_id)` RPC (no pgcrypto) for the LunaV → R-Tessera link.

## Phase 0 — SQL migration (apply in Supabase SQL Editor)
File: `supabase/migrations/20260825_cctv_cameras.sql`. Untracked `.sql` = pending live
DB work → must be applied AND committed in the same session as the frontend that calls it.
(`git status --porcelain -- 'supabase/*.sql'` to detect.)

Tables:
```sql
create table if not exists public.cctv_cameras (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references public.projects(id) on delete cascade,
  name text not null,
  communication_channel text,
  lat double precision,
  lng double precision,
  status text default 'active',
  created_by uuid,
  created_at timestamptz default now()
);
create table if not exists public.cctv_events (
  id uuid primary key default gen_random_uuid(),
  camera_id uuid references public.cctv_cameras(id) on delete cascade,
  frame_url text,
  detected_at timestamptz default now(),
  person_count int default 0
);
```
Policies (owner = creator; mirror the existing geo-linking migration). `CREATE POLICY IF
NOT EXISTS` is INVALID Postgres — use `drop policy if exists …; create policy …;`.
- `cctv_cameras_owner_all` FOR ALL USING (auth.uid() = created_by) WITH CHECK (auth.uid() = created_by).
- anon/authenticated SELECT on the table is DENIED (so R-Tessera can't read raw rows).
  Expose via a SECURITY DEFINER view instead:
```sql
create or replace view public.cctv_cameras_public as
  select id, project_id, name, lat, lng, status from public.cctv_cameras;
grant select on public.cctv_cameras_public to anon, authenticated;
```
RPCs (SECURITY DEFINER, `set search_path = public`):
```sql
-- owner-verified upsert (same auth.uid() owner check as mint_handoff_token)
create or replace function public.upsert_cctv_camera(
  p_id uuid, p_project_id uuid, p_name text, p_channel text,
  p_lat double precision, p_lng double precision)
returns uuid language plpgsql security definer set search_path = public as $$
declare v_owner uuid; v_id uuid := p_id;
begin
  select owner_id into v_owner from public.projects where id = p_project_id;
  if v_owner is null or v_owner <> auth.uid() then raise exception 'Not project owner'; end if;
  if v_id is null then v_id := gen_random_uuid(); end if;
  insert into public.cctv_cameras (id, project_id, name, communication_channel, lat, lng, created_by)
  values (v_id, p_project_id, p_name, p_channel, p_lat, p_lng, auth.uid())
  on conflict (id) do update set name = excluded.name, communication_channel = excluded.communication_channel,
    lat = excluded.lat, lng = excluded.lng where cctv_cameras.created_by = auth.uid();
  return v_id;
end; $$;
grant execute on function public.upsert_cctv_camera(uuid,uuid,text,text,double precision,double precision) to authenticated;

-- edge device writes an event (Phase 3 hardening: gate by device auth if needed)
create or replace function public.log_cctv_event(
  p_camera_id uuid, p_frame_url text, p_person_count int)
returns uuid language plpgsql security definer set search_path = public as $$
declare v_id uuid := gen_random_uuid();
begin
  insert into public.cctv_events (id, camera_id, frame_url, person_count)
  values (v_id, p_camera_id, p_frame_url, coalesce(p_person_count,0));
  return v_id;
end; $$;
grant execute on function public.log_cctv_event(uuid,text,int) to authenticated, anon;
```

## Phase 1 — LunaV app integration (built; `npm run build` green)
- `src/lib/types.ts`: added `CctvCamera`, `CctvEvent` interfaces + a `CCTV_STATUS_COLOR` map.
- `src/components/CctvVisionPage.tsx`: self-contained Vision registry —
  Leaflet map (click to drop pin → lat/lng), project `<select>` fed by the passed
  `projects: ProjectCard[]`, calls `supabase.rpc("upsert_cctv_camera", {...})`, then shows a
  "View on R-Tessera" deep link reusing `mint_handoff_token`:
  ```ts
  const popup = window.open("", "_blank");          // synchronous, BEFORE await
  const { data: token } = await supabase.rpc("mint_handoff_token", { p_project_id });
  popup.location.href = `https://r-tessera.vercel.app/?link=1&project=${projectId}&token=${token}`;
  ```
- `src/app/dashboard/page.tsx`: added `tab: "projects" | "vision"` state + a text-only
  top-level tab switcher (no emoji — LunaV nav convention). Pass the already-loaded
  `cards: ProjectCard[]` straight into `<CctvVisionPage supabase={supabase} projects={cards} />`.

## Pitfalls confirmed this session
- **JSX branch with two siblings needs a fragment.** Wrapping the existing project panel
  AND the project-list `{...}` expression in a `tab === "vision" ? <A/> : ( … )` branch
  without a `<>…</>` parent is a hard parse error. Wrap both in `<>…</>`.
- **Popup-blocker:** open `window.open("", "_blank")` synchronously in the click handler
  BEFORE `await mint_handoff_token`, else the browser silently blocks the popup.
- **Untracked `.sql` = pending live DB.** Apply in Supabase SQL Editor AND commit in the
  same session as the frontend that depends on it.
- **Anon can't read a table with no anon policy** — use a SECURITY DEFINER view, not a
  table grant, to share rows with R-Tessera.

## NOT built (future phases — see ROVER-KIT Action Plan in Obsidian vault)
- Phase 2: R-Tessera CCTV layer consuming `cctv_cameras_public` + `mint_handoff_token` landing.
- Phase 3: Pi5 / Luna EDGE YOLO → `log_cctv_event` on person detection (Supabase Realtime blink).
- Phase 4: WhatsApp image push. Phase 5: field GUI.
