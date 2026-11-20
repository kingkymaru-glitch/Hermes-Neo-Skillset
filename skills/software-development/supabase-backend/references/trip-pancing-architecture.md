# Trip.Pancing — multi-page Next.js + Cesium + Three.js app architecture

A reference for the class of app that has: a hero landing page with a swappable 3D center model (Three.js) and a rotating navigation wheel, a Cesium geo-map page, Supabase-backed content/RSVPs, and admin-only content editing. Built 2026-09-22, revised 2026-09-22 to simplify roles.

## Roles (simplified 2026-09-22)

Only TWO roles:
- `user` (default) — can create events AND shops, can RSVP, can manage own content. Both "seller" and "organizer" concepts merged into `user`.
- `admin` (you) — can edit landing page content, upload center 3D model, manage any content.

There is NO `organizer` role. Any authenticated user is both a potential seller (if they create a shop listing) and a potential organizer (if they create an event). No self-promotion step required.

## Page structure

| Route | What | Stack |
|-------|------|-------|
| `/` | Hero landing — Three.js center stage (lure or admin GLB), auto-rotating nav wheel, title from `landing_content` | Three.js (CDN) + Supabase |
| `/globe` | Full Cesium map with all shops + active events as billboard pins | Cesium + Supabase |
| `/events` | Event directory with type filter, RSVP buttons, date display | Next.js + Supabase |
| `/shops` | Shop directory with type filter, address, phone | Next.js + Supabase |
| `/about` | About page (content from landing_content hero) | Next.js |
| `/admin` | Admin CMS — edit hero text, stats, upload GLB center model | Next.js + Supabase Storage |
| `/dashboard` | User dashboard — create/manage events, shops, view RSVPs, stats | Next.js + Supabase |
| `/login` `/signup` | Auth (email/password + Google OAuth) | Supabase Auth |

## Key patterns

1. **Three.js in Next.js** — dynamic `import('three')` + `import('three/addons/...')` inside `useEffect`, never at module top level. `'use client'` required.
2. **Cesium in Next.js** — load via `<Script src="...cesium.com/.../Cesium.js" strategy="beforeInteractive">` from CDN, then read `(window as any).Cesium` inside `useEffect` after onReady.
3. **Swappable center model** — read `landing_content` where section='center_model'; if `url` is null → render procedural Three.js Rapala lure; if set → fetch GLB from Supabase Storage and auto-fit (Box3 → scale to 3.5 → recenter).
4. **Rotating nav wheel** — HTML/CSS 3D transforms (not WebGL), auto-rotating cylinder of menu buttons. Each button scales/fades based on its angle. Front button is highlighted. Click navigates.
5. **Admin gating** — `profiles.role === 'admin'` checked via `is_admin()` SECURITY DEFINER function; hide all upload/edit UI from non-admins.
6. **Event lifecycle** — `pg_cron` inside Supabase: active→ended (event_date passed), ended→archived (7 days later). Cron runs in UTC — convert MYT by subtracting 8h.
7. **RSVPs** — `event_registrations` table with triggers: auto-increment `events.current_count` on insert, decrement on cancel. RLS: users see own, event creators see their events' RSVPs.
8. **Landing content** — `landing_content(section, data jsonb)` table, public read via RLS, admin write only. Sections: 'hero', 'stats', 'highlights', 'center_model'.
9. **Auth redirect** — single `/login` route, role-based redirect after signin: admin → /admin, user → /dashboard.

## Data model (v1)

- `profiles` — `(user | admin)`, extends `auth.users`, auto-created by `on_auth_user_created` trigger
- `shops` — permanent listings (tackle/lure/boat/charter/guide), geo-tagged, `owner_user_id` FK
- `events` — time-bound (tournament/workshop/charter_trip/community/public), lifecycle status, RSVP capacity (`max_participants`, `current_count`), `created_by` FK
- `event_registrations` — event RSVPs, triggers manage `current_count`, unique(event_id, user_id)
- `landing_content` — admin-editable: `{section, data jsonb}`

## RLS rules (no recursion)

ALL admin checks go through `public.is_admin()` — a `SECURITY DEFINER` function that runs as postgres and bypasses RLS. NEVER inline a subquery on `profiles` inside a policy on `profiles` (causes 42P17 infinite recursion).

```sql
create or replace function public.is_admin()
returns boolean as $$
  select exists(select 1 from public.profiles where id = auth.uid() and role = 'admin');
$$ language sql security definer set search_path = public;
```

## Stack

- Next.js 14 App Router (all client components for 3D/Cesium pages)
- Three.js 0.158 (dynamic import inside useEffect)
- CesiumJS 1.125 (CDN via next/script beforeInteractive)
- Supabase (Auth + Postgres + Storage + pg_cron + Realtime + RLS)
- Vercel deploy (auto on push to main)
