---
name: mock-data-removal
description: Remove demo/seeded/mock data from a localStorage-backed SPA so it runs on real data — without leaving stale seed data in users' browsers or invisible demo artifacts in the UI. Trigger "remove all mock data", "strip demo users", "clear seeded accounts", "make it use real data". Covers the seed-flag-bump trap, legacy localStorage purge, hardcoded demo-mode gates/labels, and first-run real onboarding.
---

# Removing Mock Data from a localStorage-backed SPA

Bumping a seed flag is NOT enough to clear mock data. Do all surfaces.

## The seed-flag-bump trap
`storage.init()` seeds `mockData()` only when flag `seed:v1` is absent, then sets it. Bumping to `seed:v2` + stop seeding only helps FRESH browsers. A browser that already loaded v1 keeps the old seeded `rina:users`/`rina:tasks` forever.

Fix — explicit legacy purge at the top of `init()`:
```ts
healLegacySeed(): void {
  if (!localStorage) return;
  if (load('seed:v1', false) && !load('seed:v2', false)) {
    ['rina:users','rina:tasks','rina:notifications','rina:auditLogs','seed:v1']
      .forEach(k => localStorage.removeItem(k));
  }
}
```
New browsers start empty; old browsers self-heal on first visit to the new build.

## Audit ALL mock surfaces
1. Seeder (`storage.init()` calling `mockData()`) — stop, start empty.
2. Read fallbacks: `useUsers()` `return base.length ? base : mockData().users` and `useAuth.login()` fallback to `mockData().users` re-inject mock on first real login. Delete every `mockData()` call.
3. Hardcoded demo UI: labels ("Built from mock data"), "hidden in demo mode" gates that REPLACE real UI with a placeholder, login "Demo only" picker. Replace with real UI.
4. **Every surface that NAMES the demo entities — the surface that survives a "successful" purge.**
   Delete the seeded ROWS and the UI still advertises them. A backend-backed purge is not done when
   the table is empty: sweep the map legend / keyed colour strip, HUD chips carrying hardcoded
   coordinates, demo or sales scripts, PDF and report templates, and any panel rendering a FIXED
   legend. Grep the demo entity names themselves (their IDs, brands, and the demo client name)
   across the WHOLE repo, not just the data layer — those strings are what pin a deleted dataset
   into the shipped UI.

Grep: `grep -rniE "mock|demo|seeded|example\.com|hidden in demo" src/ | grep -v "\.test\."`

## Real first-run onboarding
If `users.length === 0` → "Create first administrator" form (creates SuperAdmin). Else email sign-in. First opener becomes admin; others added via Admin/Org Chart.

## Verify
1. `npm run build` green. 2. grep src for mock/demo → only color-map import allowed. 3. After deploy, grep the DEPLOYED bundle for OLD demo string (expect 0) and NEW real string (expect >=1) — see `vercel-prod-deploy-verification`. 4. Tell user to hard-reload once (legacy purge fires); fallback = clear site data.

## Pitfall — stale deploy shows old mock data
Build green + push success ≠ live is new. Confirm via live-bundle grep before claiming fixed.
