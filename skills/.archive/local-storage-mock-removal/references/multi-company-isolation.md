# Multi-company isolation — concrete RINA diff map

RINA (`~/riina`, Vite+React+recharts, localStorage-only, Vercel auto-deploy) went from single-tenant to multi-company in commit `7caa4f2`. This is the file-by-file map of the technique described in the parent SKILL.md.

## storage.ts (org-aware core)
- Add constants `ORGS_KEY='rina:orgs'`, `ACTIVE_KEY='rina:activeOrg'`, `MIGRATED_KEY='rina:orgMigrated'`.
- `scoped(key)`: `const org = getActiveOrg(); return org ? 'rina:org:'+org+':'+key : 'rina:'+key;`. Both `load`/`save` use it.
- `listOrgs()`: read `rina:orgs` JSON array.
- `setActiveOrg(key|null)`: set/remove `rina:activeOrg`.
- `createOrg(name)`: push `{key,name,createdAt}` to `rina:orgs`, `setActiveOrg(key)`, then **call `storage.init()` immediately** so the new partition is seeded empty + flagged (prevents Workspace's init from wiping the admin we write next).
- `removeOrg(key)`: drop from `rina:orgs`, delete all `rina:org:<key>:*` keys, clear activeOrg if it was that one.
- `migrateLegacyGlobal()`: if `!rina:orgMigrated` and `rina:users` exists → `createOrg('My Company')` (sets activeOrg), copy `rina:users/tasks/notifications/auditLogs/seed/branding:*` into the new org scope, remove the old global keys. Guarded so it runs once.
- `healLegacySeed()` + `init()` unchanged in spirit, but now operate on the scoped keys.

## App.tsx (thin shell + Workspace)
- `App` calls `storage.migrateLegacyGlobal()` ONCE at top (eager, so the picker sees migrated orgs before render).
- `App` holds `user` + `activeOrg` state. `if (!user) return <Login onLogin=.../>`.
- Authed app extracted into `<Workspace key={activeOrg ?? 'none'} .../>` — the `key` remounts all data hooks on company switch.
- `Workspace` owns `useTasks/useUsers/useAudit`, all handlers, `renderContent()`, and the `AppShell`. Branding now routed through `storage.load/save('branding:header'|'branding:footer')` (org-scoped).
- `onUserChange` prop replaces the old `setUser` (Workspace can't call App's setter directly).

## Login.tsx (org picker)
- `orgs = storage.listOrgs()`; `mode = orgs.length===0 ? 'create' : 'picker'`.
- **picker**: list orgs as sign-in buttons + "+ Start a new company".
- **signin**: `selectOrg(key)` does `storage.setActiveOrg(key)` then reads `storage.load('users',[])` for the email match; `onLogin(user)`.
- **create**: `storage.createOrg(name)` → `storage.save('users',[admin, ...storage.load('users',[])])` (direct storage write, NOT a hook). `onLogin(admin)`.

## AppShell.tsx
- `logOut()` now also `localStorage.removeItem('rina:activeOrg')` before reload, so logout returns to the picker.

## PITFALLS hit and fixed
1. Wrote new admin via `useUsers().addUser` first → injected Company A's users into Company B's partition (stale closure). Switched to direct `storage.save`.
2. Ran migration only inside `init()` → picker rendered empty on first load. Moved `migrateLegacyGlobal()` to `App` top.
3. `createOrg` didn't seed → Workspace's `init()` overwrote the new admin with empty arrays. Added `storage.init()` call inside `createOrg`.

## Verify
- `npm run build` green.
- Bundle-grep live: "Start a new company", "Register a new company", "rina:orgs" all present.
- Manual: hard-reload → "My Company" (migrated) + "Start a new company" → create "Company B" → fresh empty workspace → logout → "My Company" intact.
