# Static Vite/React SPA → Vercel + localStorage persistence

## Deploy (Phase A)
- `npm run build` → static `dist/`. `npx vercel deploy --prod --yes`.
- Vercel auto-detects Vite preset (build `npm run build`, out `dist`). No env vars needed for a pure SPA.
- Live URL returns 200 — curl it to verify before declaring done.

## PITFALL — Vercel CLI hangs on alias promotion (macOS, this environment)
`npx vercel deploy --prod --yes` has TWICE hung at the alias-promotion step (timed out at 600s, exit 124) even though the build itself succeeded. The CLI buffers output and never reports completion, so you can't tell it's done from the process.
SIGNALS a deploy actually finished despite the hung CLI:
- `npx vercel ls` shows a NEW random build URL (e.g. `ss-rover-cloud-gmw6c80ct-rover-r-3d.vercel.app`) — one is minted per build.
- The new code is present in the built client bundle: `grep -rl "your-new-string" .next/static 2>/dev/null` (Next) or `dist/assets` (Vite).
WORKAROUND (do NOT keep waiting on the stuck CLI):
1. Kill the stuck process (`process action=kill`).
2. Promote the new build to the prod alias yourself: `npx vercel alias set <new-build-url> <prod-domain>` (e.g. `ss-rover-cloud.vercel.app`). Run it in BACKGROUND with `notify_on_complete=true` — this step also hangs in foreground but completes.
3. Verify: `curl -s -o /dev/null -w "%{http_code}\n" <prod-domain>`.
Note: `npx vercel deploy --prod --prebuilt` fails here ("no prebuilt output in .vercel/output") unless you ran `vercel build` first — not a useful shortcut. Just run the normal deploy and promote separately.

## Phase B: wire a localStorage hook layer (no backend)
Pattern that shipped cleanly:
- `hooks/storage.ts` — thin `load(key, fallback)` / `save(key, value)` wrapping `localStorage` with a `rina:` prefix; SSR-safe (`typeof localStorage !== 'undefined'`).
- `hooks/app.tsx` — `useAuth` (persist `session`), `useTasks`, `useUsers`, `useAudit` — each seeds from a `useState` initializer that reads storage, and persists on every mutation.
- `App.tsx` consumes the hooks instead of raw `useState`. Restore session on mount so login survives refresh: `useState(() => auth.session?.user ?? null)` and default view `'dashboard'` when a session exists.

## PITFALL — empty-state seed bug (cost a silent data wipe)
A naive `storage.init()` like:
```
const initialized = storage.load('initialized', false);
if (!initialized) { storage.save('initialized', true); return { users:[], tasks:[], ... }; }
```
returns EMPTY users/tasks on every load AFTER the first. On first open the demo looks fine; on refresh the seeded 40+ tasks and 25 people vanish because `mockData()` is never written to storage.

FIX: on first init, WRITE the mock seed into storage, then return it:
```
if (!seeded) {
  const s = mockData();
  storage.save('seed:v1', true);
  storage.save('users', s.users);
  storage.save('tasks', s.tasks);
  storage.save('notifications', s.notifications);
  storage.save('auditLogs', []);
  return { users: s.users, tasks: s.tasks, notifications: s.notifications, auditLogs: [] };
}
```
Use a *versioned* flag (`seed:v1`) so a later schema change can re-seed by bumping the key.

## Pitfalls — functional vs object updater
- When porting `setTasks(prev => ...)` callbacks to a hook, the hook's `update(id, patch)` likely takes an object patch, not a function. Either (a) change the hook to accept `Partial<T> | ((prev: T) => T)` and apply the function inside, or (b) compute the next value in the caller. The shipped fix did (a).
- Audit log accumulator: if the hook exposes `items`, call `api.add(log)` then read `api.items` for the in-memory mirror — don't double-accumulate via `setState(prev => [...prev, log])` AND the hook, or entries duplicate.

## Verify
- Build green, lint 0/0, live 200. Then in a browser: create a task, refresh, confirm it persists; log in, refresh, confirm session restored.
