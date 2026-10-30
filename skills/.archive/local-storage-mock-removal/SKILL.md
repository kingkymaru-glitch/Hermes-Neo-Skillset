---
name: local-storage-mock-removal
description: Convert a localStorage-only (no-backend) prototype that auto-seeds demo/mock users & tasks into a clean app that starts empty and runs on real data. Covers the full class of failure — seed flag in storage.init(), hook-level mock fallbacks (useUsers/useAuth), a seeded-account login picker, hardcoded "demo mode" labels and feature gates, and the silent trap where a flag bump does NOT clear data already written under the old flag. Trigger when the user says "remove all mock data", "strip the demo data", "make it ready for real data", "the app still shows seeded/fake users", or when prepping a localStorage prototype for real use/testing.
---

# Removing mock data from a localStorage-only prototype

A very common prototype pattern: on first load, `storage.init()` checks a seed flag (e.g. `seed:v1`); if unset, it calls `mockData()` and writes demo users/tasks into `localStorage`, then sets the flag. This "works" for demos but becomes a trap the moment you want real data. Removing mock data is NOT just deleting the seed line — you must close every place the demo leaks back in, AND purge data already written under the old flag.

## The full checklist (do all of these)

1. **Stop seeding in `storage.init()`.** Return empty arrays instead of `mockData()`. Bump the seed flag (`seed:v1` → `seed:v2`) so a fresh browser starts empty.
2. **Kill hook-level fallbacks.** Search every hook that reads storage for `|| mockData()...` fallbacks. `useUsers` often does `base.length ? base : mockData().users`; `useAuth.login` often falls back to `mockData().users` for "demo convenience". Delete those fallbacks — otherwise an empty store silently repopulates from mock, or the demo login still matches fake accounts. Remove the now-unused `import { mockData }`.
3. **Replace the seeded-account login.** A typical login screen renders a `<select>` of `mockData().users` ("sign in as Priya…"). Replace it with a REAL flow: if zero users exist, show a "Create first administrator" form (name/email/position/department) that creates a SuperAdmin via the real `addUser`; otherwise email-based sign-in against stored users. Remove any "Demo only" disclaimer.
4. **Hunt hardcoded demo artifacts** — these are easy to miss and look identical to real UI:
   - Labels like "Built from mock data. Click Edit to change a role."
   - Feature GATES that replace real UI with a placeholder: e.g. AdminPanel showing "User list and role controls are hidden in demo mode" instead of the actual user table. Remove the gate, render the real UI.
   - Footer/brand copy with customer-specific strings (e.g. "TNB's strategic goals") — genericize per the copy config.
5. **Add an explicit legacy-purge (the silent trap).** A flag bump only helps browsers that have NOT yet seeded. Any browser that loaded the OLD build already wrote `seed:v1` + the mock arrays, and will KEEP showing them forever because the new `seed:v2` check sees v1 already set and skips init. Fix:
   ```ts
   const LEGACY_FLAG = 'seed:v1';
   healLegacySeed() {
     if (localStorage.getItem(`rina:${LEGACY_FLAG}`) && !localStorage.getItem(`rina:${SEED_FLAG}`)) {
       ['rina:users','rina:tasks','rina:notifications','rina:auditLogs',`rina:${LEGACY_FLAG}`]
         .forEach(k => localStorage.removeItem(k));
     }
   }
   // call storage.healLegacySeed() at the top of init()
   ```
   This makes the next load of the NEW build wipe the old mock data, regardless of when the browser first visited.

## Multi-company isolation (the next step after removing mock data)
Once a single-tenant localStorage app runs on real data, the user often needs MULTIPLE real companies, each with its own admin, fully separate from each other. The trap: the app keys everything off `rina:users` (global), so after Company A registers there is NO path for Company B to register a fresh company, and the two would bleed into each other. Fix = per-company localStorage partition + an org picker on login.

### Data model
- Registry: `rina:orgs` = JSON array `[{ key, name, createdAt }]`.
- Active org: `rina:activeOrg` = current `key`.
- **Scoped keys**: every datum is stored under `rina:org:<key>:<datum>` (e.g. `rina:org:org-123:users`). A `scoped(key)` helper reads `rina:activeOrg` and prefixes; `load/save` auto-scope.
- Each org's `init()` seeds empty + sets its own `seed:v2` flag so data never crosses partitions.

### Login flow (the entry point that makes Company B possible)
- `orgs = storage.listOrgs()`. If empty → show "Create company" form; else → **company picker** (list existing orgs as sign-in buttons + a "+ Start a new company" button).
- Select org → `storage.setActiveOrg(key)` → sign-in form reads THAT org's `users`.
- Create company → `storage.createOrg(name)` (sets activeOrg + seeds the new partition immediately) → write the Super Admin via `storage.save('users', [admin])` (NOT via a `useUsers` hook, which captured the old org's array at mount — see pitfall).
- **PITFALL — migration must run EAGERLY at startup, not lazily inside `init()`.** `init()` is only called by data hooks, but `Login` reads `listOrgs()` on first render. If migration (global → "My Company" workspace) runs only inside `init()`, the picker renders BEFORE migration and shows an empty company list. Call `storage.migrateLegacyGlobal()` once at the top of `App` so the picker reflects migrated data immediately. Guard with a `rina:orgMigrated` flag so it runs once.
- **PITFALL — do NOT write the new admin through a `useUsers()`-style hook captured at mount.** `addUser`/`upsert` close over the `users` array from the hook's `useState` initializer, which was the PREVIOUS active org (or empty). After `createOrg` flips `activeOrg`, that closure still holds stale data and would inject it into the new partition. Write the admin directly: `storage.save('users', [admin, ...storage.load('users',[])])` AFTER `createOrg` set the active org, so `load/save` target the new scope.

### Re-mount the data hooks per company (the React trap)
`useState(() => storage.init().users)` captures the active org at mount. If the user switches companies without a full reload, the hooks keep Company A's data. Fix: extract the authed app into a `<Workspace>` subcomponent and render it with `key={activeOrg}` so a company switch remounts the subtree and re-runs every `useState` initializer against the new partition. App stays a thin shell: `if (!user) return <Login/>; return <Workspace key={activeOrg} .../>`. Logout clears `rina:activeOrg` (so the next login shows the picker, not the old company).

### Limitation (by design, no-backend apps)
Data is per-browser/device. Company B on a different laptop starts empty until people are added (e.g. via .xlsx batch upload). True cross-device sync for one company needs backend tenancy (Supabase orgs + RLS) — flag as "Approach B" if the user wants it. **This was implemented for RINA (2026-07-26): real Supabase Auth (email+password) + per-`organization_id` RLS + an `on_auth_user_created` trigger that creates the org on first-admin signup and claims invited members on join. See `supabase-auth-gate` → "Multi-tenant / multi-company" section + `references/multitenant-vite-supabase.md` for the concrete schema + React hook patterns (incl. the `orgId`-as-prop child-before-parent effect fix and the import-safe Supabase client).** Don't pretend per-device isolation is multi-device.

See `references/multi-company-isolation.md` for the concrete RINA diff map (storage.ts / App.tsx / Login.tsx).

## Verify (do NOT skip)
- `npm run build` green (or `vite build`).
- **Confirm the deploy actually serves new code** via the bundle-grep in `vercel-prod-deploy-verification` (a green push does NOT mean Vercel rebuilt — stale builds are silent). For RINA: grep the live bundle for a NEW string (e.g. "people in this workspace") and confirm OLD strings ("Built from mock data", "hidden in demo mode") are GONE.
- **Tell the user to hard-reload once** (Cmd+Shift+R). The legacy-purge only runs on a load of the NEW build. If they still see old data after a normal reload, it's browser cache + old localStorage — hard-reload fixes it; clearing site data is the nuclear option.

## RINA case study (real, 2026-07-26)
Vite + React + recharts task app, localStorage-only, repo `~/riina`, GitHub `kingkymaru-glitch/riina`, Vercel auto-deploy.
- First "remove mock data" pass (commit a0b98cf) did steps 1–3 + bumped flag, but STILL failed in production: live Org Chart showed seeded users + "Built from mock data" + no Help button (proved the deploy was stale AND old localStorage wasn't cleared). Root causes: (a) Vercel hadn't rebuilt the prior push; (b) flag bump didn't clear v1-seeded data; (c) two hardcoded demo artifacts missed (OrgChart label, AdminPanel "hidden in demo mode" gate that replaced the real user table).
- Fix pass (commit 299eb68): added `healLegacySeed()` + removed both hardcoded artifacts + built a REAL AdminPanel user-management table (list all, role `<select>`, + Add user, Remove). Verified live via bundle grep. User hard-reloaded → clean first-admin setup screen.
- Lesson captured in `vercel-prod-deploy-verification`: bundle-grep the deployed JS; a flag bump is insufficient for already-seeded browsers.
See `references/rina-mock-removal.md` for the exact file-by-file diff map.

## Gotchas
- Leaving `src/data/mock.ts` in place is fine (harmless dead code / color maps), but ensure NOTHING imports `mockData()` anymore (grep to be sure).
- The "Plan vs Actual" recharts graph was ALREADY functional in RINA (planned = `estimatedHours`, actual = `actualHours`); "make it function" meant add a graceful empty state, not rebuild. Don't assume a missing feature is broken — read the component first.

## Backend/edge dashboard variant (synthetic telemetry, not a localStorage prototype)
When the target is a CesiumJS/React dashboard like R-Tessera (repo `~/my-digital-twin`, also branded MARU) rather than a localStorage CRUD app, "remove all mock data" means something broader than the seed-flag pattern above. There is no `storage.init()` mock seed — instead the app synthesizes a believable telemetry stream so the board is never empty when no real edge hardware is connected. Removing ALL of it (the user's usual intent) makes the dashboard show NOTHING until a real `VITE_EDGE_API_URL` edge computer or android node is wired up.

**SCOPE-CLARIFY FIRST (non-negotiable).** A single `clarify()` with the mechanism + trade-off before any edit, because the two scopes produce opposite outcomes:
- Scope A — remove ONLY the Demo Sensors authoring feature (the `MOCK_SENSOR_TYPES` registry + placement mode). Keep `seedSensors()`/`tickSensors()` so the board still shows live channels when no hardware is present.
- Scope B — remove ALL synthetic telemetry (Demo Sensors + `seedSensors()`/`tickSensors()` + `EDGE_MODE==='mock'`). Dashboard empty unless real hardware connects. **(user chose this 2026-08-01)**
- Scope C — also strip the `nodesService` localStorage fallback so user-authored nodes require Supabase configured (true zero-mock).

**What to excise (Scope B) — see `references/rtessera-synthetic-telemetry-removal.md` for the exact symbol/file map:**
- `src/context/EdgeDataContext.jsx`: `MOCK_SENSOR_TYPES`, `MOCK_TYPE_MAP`, `MAX_SLOTS`, `seedSensors()`, `tickSensors()`, the `mockSensors` state + `addMockSensor`/`removeMockSensor`/`clearMockSensors`, `getMockSeries()`, `placement`/`setPlacement`, the mock-jitter `useEffect`, `allSensors = [...sensorPayloads, ...mockSensors]`, the `EDGE_MODE==='mock'` branch, and the exported `MOCK_MAX_SLOTS`.
- `src/App.jsx`: the `demo` SETTING_ITEM, `DemoSensorsPanel` + its `{view==='demo' && ...}` mount, the placement banner + crosshair-cursor effect, the `useEdgeData()` destructure pulling mock symbols, `SensorDetail`'s `getMockSeries`/`sensor.mock` sparkline, `MOCK_CHAT` seed, and `DEMO_ASSETS` + every `setAssets(DEMO_ASSETS)` fallback (replace with empty array or real fetch).
- `src/App.css`: the `.demo-*` class family + `.dt-edge.edge-mock`.
- `src/supabaseClient.js`: the comment claiming a 'seeded demo data' fallback.

**KEEP (NOT mock):** `sensorPayloads` driven by a real `VITE_EDGE_API_URL`/`android` node; the `nodesService` localStorage fallback for *user-authored* nodes (Scope A/B) — that is durable offline storage, not demo data.

**Verify:** `npm run build` green; grep for `mockSensors|MOCK_SENSOR_TYPES|DemoSensorsPanel|seedSensors|tickSensors|getMockSeries|MOCK_CHAT|DEMO_ASSETS` returns zero; confirm the dashboard is empty (no channels) when no edge device is configured.
