# RINA mock-data removal — file-by-file diff map (2026-07-26)

Repo: ~/riina (Vite+React+recharts, localStorage-only, no backend). GitHub kingkymaru-glitch/riina, Vercel auto-deploy on push to main.

## Files changed
- src/hooks/storage.ts
  - Removed `import { mockData }`.
  - `init()` no longer calls mockData(); writes empty arrays; flag `seed:v1`→`seed:v2`.
  - Added `healLegacySeed()`: if old `seed:v1` present and new `seed:v2` absent, remove `rina:users/tasks/notifications/auditLogs` + `seed:v1`. Called at top of `init()`.
- src/hooks/app.tsx
  - `useAuth.login`: deleted `|| mockData().users.find(...)` fallback; removed the `import { mockData }`.
  - `useUsers`: `return base.length ? base : mockData().users` → `return base`.
  - Added `useUsers.removeUser` (filter + persist) so AdminPanel can delete users.
- src/components/Login.tsx (rewritten)
  - Old: `<select>` of seeded mock users + "Demo only" disclaimer.
  - New: `isFirstRun = users.length===0`; first-run shows "Create first administrator" form (name/email/position/department) → creates SuperAdmin via `addUser`; else email sign-in. Uses `useUsers()`.
- src/components/OrgChart.tsx
  - Removed hardcoded "Built from mock data. Click Edit to change a role." → live-structure or empty-state copy.
- src/components/AdminPanel.tsx
  - Removed "User list and role controls are hidden in demo mode" gate that replaced the real UI with a placeholder.
  - New: real User Management table for SuperAdmin/DepartmentHead — list all users (name/email/dept/role), role `<select>` (Member/DeptHead/SuperAdmin), "+ Add user" form, Remove (not self). Props `onAddOrUpdateUser`, `onRemoveUser`.
- src/App.tsx
  - Added `removeUser = (id)=>usersApi.removeUser(id)`.
  - Passed `onAddOrUpdateUser={upsertUser}` + `onRemoveUser={removeUser}` into `<AdminPanel>`.
- src/components/AppShell.tsx + src/components/HelpModal.tsx
  - Added Help button (HelpCircle) to top bar; modal with step-by-step guides for all 9 feature areas.

## Verification
- `npm run build` green (2160 modules).
- Bundle grep on live riina-eight.vercel.app/assets/index-*.js: NEW strings present ("people in this workspace", "+ Add user", "Help"); OLD strings GONE ("Built from mock data", "hidden in demo mode").
- User hard-reloaded → clean first-admin screen (legacy-purge fired).

## Copy changes
- src/config/copy.ts: "TNB's strategic goals" → "Company's strategic goals" (subtext, dashboardSubtitle, loginSubtext). Login page sentences (tagline/subtext) removed from Login.tsx render; "RIINA Console"→"RINA Console".
