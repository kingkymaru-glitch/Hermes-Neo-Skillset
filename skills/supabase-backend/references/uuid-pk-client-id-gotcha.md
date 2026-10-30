# P36 / P36b — uuid PK + client-generated string ids + fire-and-forget async

## Symptom (RINA, 2026-08-07)
User mass-uploaded a `.xlsx` of new users via AdminPanel "Upload .xlsx".
The success toast said "N added / Org chart updated" but the org chart
never reflected the uploaded people. No console error was surfaced to the user.

## Root cause
1. `user_profiles.id` is `uuid primary key default gen_random_uuid()`
   (schema.sql). The batch handler minted fake ids `user-${Date.now()}-${n}`
   (a string) and passed them to `upsertProfile` →
   `supabase.from('user_profiles').upsert({ id, … })`.
   Postgres: `invalid input syntax for type uuid`. Insert rejected.
2. The insert was fire-and-forget: `onAddOrUpdateUser?.(…)` (no `await`),
   and App.tsx's `upsertUser` did NOT `return` the promise, so the
   rejection was swallowed. The false success toast was set in the same
   `try` block after the calls, so it always fired.

## Repro (minimal)
```js
// table: id uuid primary key, organization_id uuid not null
await supabase.from('user_profiles').upsert({
  id: `user-${Date.now()}-0`,   // NOT a valid uuid
  organization_id: orgId, name: 'X', email: 'x@y.z', …
});
// -> PostgresError: invalid input syntax for type uuid: "user-1754…-0"
```

## Fix (two parts)
A. Generate a real UUID on the client, or let the DB assign one:
   - client: `const id = crypto.randomUUID();`  (valid uuid, passes the type check)
   - or omit `id` entirely and rely on `default gen_random_uuid()`
B. Await every write and return the promise so errors surface:
   - AdminPanel: `await onAddOrUpdateUser?.(row);`
   - App.tsx: `const upsertUser = (p) => usersApi.upsert(p);`  // NOTE return
   - catch block shows the real error: `setBatchMsg('Upload failed: ' + e.message)`

## P36b — FK key-type must match on both ends
The upload stored `reportsTo` as a UUID (resolved from the "Reports To"
column by name→id map). But OrgChart rendered the tree by
`child.reportsTo === parent.name` (a NAME), and the manual Edit dropdown
stored `value={u.name}`. So even once rows persisted, uploaded people
appeared as disconnected root cards (no reporting lines).

Fix: use the UUID id consistently:
- insert: `reportsTo: refId` (refId = looked-up uuid)
- OrgChart lookup: `users.filter(u => u.reportsTo === u.id)` is wrong;
  the parent lookup is `getReports(reportsTo) => users.filter(u => u.reportsTo === reportsTo)`
  called with `member.id` (not `member.name`)
- OrgChart Edit dropdown: `<option value={u.id}>{u.name}</option>`
  and Save writes `{ ...member, reportsTo: reportsTo || null }` (reportsTo is the id)

## Verification (what actually ran)
- `npm run build` → green (Vite/esbuild ignores the pre-existing `tsc` errors).
- Node harness with the installed `xlsx` lib, using the app's exact template
  columns (Name, Email, Position, Office, Reports To, Role):
  - 3 rows parsed, 0 skipped
  - `crypto.randomUUID()` ids all matched
    `/^[0-9a-f]{8}-…-…-[0-9a-f]{12}$/i`
  - reportsTo wiring correct: Siti→Ahmad, Rajesh→Siti
  - proved the OLD fake id `user-1754…-0` is NOT a valid uuid → would fail insert

## Broader rule
Any client-side row creation that writes a synthetic string id into a
`uuid` PK (or any typed PK) will fail the same way. Audit: grep for
`` `user-` `` / `` `id-${Date.now()` `` / template-literal ids feeding an
`upsert`/`insert`. And grep the relationship column's usage on BOTH the
write side and the read/join side — a type mismatch there is silent until
the dependent view (org chart, tree, parent/child list) renders wrong.
