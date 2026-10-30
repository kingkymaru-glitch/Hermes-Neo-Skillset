# Legacy localStorage purge — exact RINA diff recipe

Context: RINA (`~/riina`, Vite + React + recharts, localStorage-only, no backend) seeded 27 demo users + 50 tasks into `localStorage` via a `seed:v1` flag. User asked to "remove all mock data" for real testing. After bumping the flag to `v2` and stopping the seeder, browsers that had already loaded the v1 build STILL showed the mock users (Priya, Ahmad) because the seeded data was never deleted — only the "seed again" decision changed.

## The fix that worked (storage.ts)

Before the read path, purge any data written by the old build:

```ts
const SEED_FLAG = 'seed:v2';
const LEGACY_FLAG = 'seed:v1';

healLegacySeed(): void {
  if (typeof localStorage === 'undefined') return;
  if (storage.load<boolean>(LEGACY_FLAG, false) && !storage.load<boolean>(SEED_FLAG, false)) {
    ['rina:users', 'rina:tasks', 'rina:notifications', 'rina:auditLogs', `rina:${LEGACY_FLAG}`]
      .forEach((k) => localStorage.removeItem(k));
  }
}

init() {
  storage.healLegacySeed();
  const seeded = storage.load<boolean>(SEED_FLAG, false);
  if (!seeded) {
    storage.save(SEED_FLAG, true);
    storage.save('users', []);
    storage.save('tasks', []);
    storage.save('notifications', []);
    storage.save('auditLogs', []);
  }
  return {
    users: storage.load<User[]>('users', []),
    tasks: storage.load<Task[]>('tasks', []),
    notifications: storage.load<Notification[]>('notifications', []),
    auditLogs: storage.load<AuditLog[]>('auditLogs', []),
  };
}
```

## Why this is the right shape
- `healLegacySeed` only fires once (guard: legacy flag set AND new flag not yet set). After it runs, the new flag gets set on first `init()`, so it never re-triggers.
- It deletes the legacy flag key itself so a v1 build can't "re-seed" on a user who toggled back.
- New browsers (no legacy flag) skip the purge and simply start empty.

## Three mock surfaces that also had to change (RINA)
1. `useUsers()` — was `return base.length ? base : mockData().users;` → `return base;`
2. `useAuth.login()` — removed `|| mockData().users.find(...)` fallback.
3. Hardcoded UI:
   - `OrgChart.tsx`: "Built from mock data. Click Edit to change a role." → live/empty-state copy.
   - `AdminPanel.tsx`: a block REPLACED the user-management UI with "User list and role controls are hidden in demo mode." → replaced with a real user table (list, role `<select>`, + Add user, Remove).
   - `Login.tsx`: "Demo only / seeded account" dropdown → real "Create first administrator" form (empty state) or email sign-in.

## Verification that proved it
- `npm run build` green.
- `grep -rniE "mock|demo|example\.com" src/` → only `departmentColorMap` import from `mock.ts` remained (kept; it's a color map, not data).
- After `git push` (Vercel auto-build), fetched the LIVE bundle and grepped:
  - `"people in this workspace"` present (>=1), `"+ Add user"` present, `"Help"` present → NEW build live.
  - `"Built from mock data"` → 0 matches, `"hidden in demo mode"` → 0 matches → OLD demo strings gone.
- User action: hard-reload once (Cmd+Shift+R) so `healLegacySeed()` fires; falls back to "clear site data" if anything stuck.

## Lesson
For localStorage-only apps, a seed-flag bump is NOT sufficient to clear data already written under the old flag. Add an explicit legacy purge. And grep the DEPLOYED bundle to confirm the deploy actually rebuilt (a green push can still serve a stale bundle — see `vercel-prod-deploy-verification`).
