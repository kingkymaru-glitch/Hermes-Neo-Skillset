# Removing mock/seeded data from a localStorage-only Vite/React SPA

Pattern distilled from the RINA task (Vite + React + recharts, no backend — all state in `localStorage`). The user said "remove all mock data so I can test with real data." A seed-flag bump is NOT sufficient. Do ALL of the following.

## The four places mock data hides (miss any one → user still sees demo data)
1. **Storage seeder** (`hooks/storage.ts` `init()`): likely does `if (!seeded) { save users/tasks from mockData(); save SEED_FLAG }`. Change it to save EMPTY arrays. Bump `SEED_FLAG` (e.g. `v1`→`v2`) so a fresh browser won't reuse old data — but see #4.
2. **Hook fallbacks**: `useUsers` often does `return base.length ? base : mockData().users`. `useAuth.login` often falls back to `mockData().users.find(...)`. Delete every `mockData()` reference in the hooks. Import of `mockData` becomes unused → remove it.
3. **Hardcoded demo UI**: search the whole `src` for `mock`, `demo`, `Built from mock`, `hidden in demo mode`, `seeded account`, `Demo only`. These are STRING LITERALS and component gates that DON'T disappear when you cut the data. RINA had two that were missed on the first pass:
   - `OrgChart.tsx`: `<div>Build from mock data. Click Edit…</div>` label.
   - `AdminPanel.tsx`: a "User list and role controls are hidden in demo mode" block that REPLACED the real user-management UI with a placeholder — so even after data was gone, the admin couldn't manage users.
   Grep `src` for `demo|mock|seeded` after the data cut and kill every hit that renders to the user.
4. **Legacy purge (the critical one)**: a seed-flag bump ONLY helps browsers that have NEVER loaded the app. Any browser that already loaded the OLD build has `rina:users` etc. written under `seed:v1` and will keep showing mock users forever, because the new `v2` init sees `seeded=true` and skips re-seeding (so it just reads the old mock data back). Fix: add a one-time self-heal that detects the OLD flag and deletes the legacy keys:
   ```ts
   const LEGACY_FLAG = 'seed:v1';
   healLegacySeed() {
     if (localStorage.getItem(`rina:${LEGACY_FLAG}`) && !localStorage.getItem(`rina:${SEED_FLAG}`)) {
       ['rina:users','rina:tasks','rina:notifications','rina:auditLogs',`rina:${LEGACY_FLAG}`]
         .forEach(k => localStorage.removeItem(k));
     }
   }
   // call healLegacySeed() at the top of init()
   ```

## Onboarding when there's no seeded admin (localStorage-only means login needs a real user)
With no users, the old "pick a seeded account" login breaks. Replace it with a first-run flow:
- `Login.tsx`: if `users.length === 0`, show a "Create first administrator" form (name/email/position/department) that calls `addUser` with `role: 'SuperAdmin'`. Otherwise email sign-in against real stored users. Remove the "Demo only" disclaimer.
- This makes the app genuinely start empty and populate from real input. Tell the user to HARD-RELOAD (Cmd+Shift+R) once after deploy so the legacy purge (#4) runs.

## Verify the removal actually took
- `npm run build` green (2160 modules etc.).
- Grep the DEPLOYED bundle (not just local) for demo markers — see `vercel-prod-deploy-verification` bundle-grep recipe. Expect NEW-code strings present, OLD demo strings (`Built from mock data`, `hidden in demo mode`) GONE.
- The user's screenshot is ground truth: if they still see seeded names (Priya, Ahmad…), the legacy purge hasn't run in their browser yet (they need the hard-reload) OR a hardcoded demo artifact was missed.

## Lesson
For localStorage-only apps, "remove the seed call" is maybe 40% of the job. The other 60% is: kill hook fallbacks, kill hardcoded demo strings/gates, and add a legacy-purge for browsers that already seeded. Anything less and the user reloads to find the demo still there.
