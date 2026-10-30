# RIINA — Admin & Org Chart tab function map (for process-QA)

Verified 2026-08-18 by reading `src/components/AdminPanel.tsx`,
`src/components/OrgChart.tsx`, `src/components/OrgChartCanvas.tsx`, `src/lib/api.ts`.

## ADMIN TAB — User Management (SuperAdmin/MasterAdmin only)
| Button / action | Code path | Status |
|---|---|---|
| `+ Add user` | `upsertProfile()` → `upsert_user_profile` RPC | ❌ BROKEN (avatar column, see live_bugs §3) |
| `Upload .xlsx` (bulk) | loop `upsertProfile` (active=true) + `setUserHierarchy` | ❌ BROKEN (same RPC) |
| Row `Edit → Save` | `setUserHierarchy` + `upsertProfile` | ❌ BROKEN (same RPC) |
| `Remove` (row) | `removeProfile()` → `delete_user_profile` RPC (soft) | UNTESTED |
| `Undo` (restore) | `restoreProfile()` → `restore_user_profile` RPC | UNTESTED |
| `Import from chart (AI)` | `api/import-org-chart` (Gemini proxy) | UNTESTED (needs GEMINI_API_KEY in Vercel) |
| `Download sample` | builds `.xlsx` client-side | UNTESTED |
| Branding Edit/Save | `saveOrgSetting` (localStorage) + displayed via `loadOrgSetting` | UNTESTED |
| Company settings (autoStartHours) | `saveCompanySettings` → `company_settings` upsert | UNTESTED |
| Audit log view | reads `audit_logs` (org-scoped) | UNTESTED |

## ORG CHART TAB
| Action | Code path | Status |
|---|---|---|
| Auto layout (read-only) | `fetchUsers` + `fetchReportingLines`, merges `reports_to_ids` | UNTESTED (pending) |
| `Canvas` toggle | switches to `OrgChartCanvas` (admin-gated, `canEdit = role==='SuperAdmin'`) | UNTESTED |
| Canvas draw modes / move box / draw line | `addReportingLine` / `removeReportingLine` / `upsertOrgChartPosition` | UNTESTED |
| `Add role` (in chart) | `onAddOrUpdateUser` → `upsertProfile` | ❌ shares broken RPC |
| `Re-seed from Admin` | reloads positions from `fetchOrgChartPositions` | UNTESTED |
| Wheel zoom / Fit / Back-to-Auto | `OrgChartCanvas` (patched earlier this session, commit 0f55b57/d907e6a) | BUILT (verify live) |

## How to drive a button from Node (example)
```js
const sb = createClient(URL, KEY); // anon client
await sb.auth.signInWithPassword({ email:'neo.superadmin@rina-test.dev', password:'RinaTest!2026' });
// then call the SAME rpc the button uses:
await sb.rpc('upsert_user_profile', { org, payload:{...} }); // exercises the Add-user path
```
This is equivalent to clicking the button (no skipped steps in the data layer).
Note: headless Chrome is disabled on MARU's Mac, so UI clicks are driven via this
Node-as-anon-client approach rather than a browser session.
