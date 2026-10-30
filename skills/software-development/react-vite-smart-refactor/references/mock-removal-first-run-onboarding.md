# Strip mock/seeded data + real first-run onboarding (localStorage-only Vite SPA)

Recurring task: a prototype ships with seeded demo users/tasks (e.g. `mockData()`
auto-loaded into localStorage on first run). The user wants it testable with
REAL data. This is a cross-cutting Vite+React refactor: the seed must be cut at
EVERY layer that pulls it, or the app silently repopulates.

## The trap: one seed switch is not enough
A seeded SPA usually re-injects mock data in 2–3 places. Audit all of:

1. **Storage init** (`storage.ts` / `init()`): the place that writes mock data
   into localStorage on first run. Replace the seed block with empty arrays.
2. **Hook fallbacks**: `useUsers()` / `useAuth().login()` often do
   `base.length ? base : mockData().users` or `|| mockData().users`. Remove the
   `mockData()` fallback entirely — otherwise an empty store gets repopulated.
3. **Login UI**: a "pick a seeded account" `<select>` + "Demo only" disclaimer.
   Replace with a REAL first-run flow (below).

## Fresh-empty flag bump
If the app guards seeding with a `seed:v1` localStorage flag, BUMP it to `v2`
and still write empty arrays. Otherwise a browser that already ran the old seed
keeps the demo data and the change looks like it "didn't take." Clearing storage
resets to empty, but the flag bump makes the new empty start apply to returning
users too.

