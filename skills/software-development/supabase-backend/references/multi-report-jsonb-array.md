# 1..N relationship as a plain `jsonb` array column (e.g. "reports to 1..N bosses")

When a row must reference MULTIPLE related rows (a member reports to several
managers, a task has several assignees, a node maps to many documents), store the
foreign ids as a **plain `jsonb` array column** — NOT `jsonb[]`, NOT a junction
table at small scale. Real case: RINA `user_profiles.reports_to_ids` (2026-08-17).

## Schema
```sql
alter table public.user_profiles
  add column if not exists reports_to_ids jsonb;
```
- **Use `jsonb`, not `jsonb[]`.** The Supabase JS client writes a JS array
  `[{...}, {...}]` (JSON) which PostgREST cannot coerce into a native `jsonb[]`
  array literal (see supabase-backend P47). `jsonb` accepts a JSON array natively.
- **Keep the legacy single column** (`reports_to` still exists) for back-compat.
  New writes go to the array; readers fall back to the single field when the array
  is empty.

## Client model (TypeScript)
```ts
reportsTo?: string | null;        // legacy single boss (kept)
reportsToIds?: string[];          // 0..N bosses — preferred when set
```

## Read path — resolve with legacy fallback every time
```ts
const reportsToId = (u: User) =>
  (u.reportsToIds && u.reportsToIds.length ? u.reportsToIds : u.reportsTo ? [u.reportsTo] : []);
// root = members with no boss; reports = members whose id-set includes parent.id
const root = users.filter((u) => u.active && reportsToId(u).length === 0);
const getReports = (parentId) => users.filter((u) => u.active && reportsToId(u).includes(parentId));
```
This is the key trick: ONE helper returns the id-set (array if set, else the single
field wrapped), and BOTH the root computation and the per-parent children lookup go
through it. A member then renders under EVERY boss in its set — that's the
"appears under multiple parents" behavior for free.

## Write path (API layer)
```ts
reports_to:  user.reportsTo ?? null,
reports_to_ids: user.reportsToIds && user.reportsToIds.length ? user.reportsToIds : null,
```
Keep writing the legacy `reports_to` (first id) so single-boss rows stay readable by
older code, AND the array for multi-boss.

## UI (multi-select in an inline edit row)
In edit mode, render a checkbox list of the OTHER members; the row's single Save
commits the whole object (name/email/position/department/role/jobDescription/
reportsToIds) through the existing upsert path. Toggle helper:
```ts
const toggleReportsTo = (id, bossId) => {
  const d = draft[id];
  const has = d.reportsToIds.includes(bossId);
  setDraft(id, { reportsToIds: has ? d.reportsToIds.filter(x => x !== bossId)
                                   : [...d.reportsToIds, bossId] });
};
```

## Pitfalls
- **A missing `jsonb` column breaks the read** if the status/fetch query selects it
  in the same call as a required column (see P39 extension 3 — fail OPEN, split
  required vs optional columns). The row edit UI will show "—" until the migration
  is applied AND a selection is saved.
- **Multi-select UI alone is a trap without the DB column** — the button renders
  before the migration is applied. Ship the `.sql` and the code together; confirm
  the founder ran it.
- If you MUST have a junction table (true many-to-many with per-link metadata), that
  is Option B; at single-digit-company scale the `jsonb` array is simpler and faster.
