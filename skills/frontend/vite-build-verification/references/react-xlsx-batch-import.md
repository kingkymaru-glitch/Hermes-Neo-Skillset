# Client-side .xlsx batch import in a React/Vite SPA (SheetJS)

Reusable pattern from the RINA "batch upload users" feature. Useful whenever a user wants to bulk-create records (users, inventory, tasks) from a spreadsheet with NO backend.

## Dependency
`npm install xlsx@0.18.5`. NOTE: npm flags 2 OSV advisories on xlsx@0.18.5 (prototype pollution / ReDoS). Acceptable for CLIENT-SIDE, admin-supplied-file-only parsing (no server trust boundary). If you ever parse server-side or accept untrusted uploads, swap to `exceljs` instead. Don't let the advisory block the dep in a pure-browser flow.

## Template download (so users fill the right columns)
```ts
import * as XLSX from 'xlsx';
const rows = [
  { Name: 'Ahmad', Email: 'ahmad@co.com', Position: 'VP', Office: 'VP Office', 'Reports To': '', Role: 'SuperAdmin' },
  { Name: 'Siti',  Email: 'siti@co.com',  Position: 'Head', Office: 'Strategy', 'Reports To': 'Ahmad', Role: 'DepartmentHead' },
];
const ws = XLSX.utils.json_to_sheet(rows);
const wb = XLSX.utils.book_new();
XLSX.utils.book_append_sheet(wb, ws, 'Users');
XLSX.writeFile(wb, 'RINA-users-template.xlsx');   // triggers browser download
```

## Parse + map (two-pass so hierarchy resolves)
The trap: "Reports To" references another row by name/email, but that person may not exist yet when you create the current row. Resolve in two passes.
```ts
const buf = await file.arrayBuffer();
const wb = XLSX.read(buf, { type: 'array' });
const raw = XLSX.utils.sheet_to_json<Record<string, unknown>>(wb.Sheets[wb.SheetNames[0]], { defval: '' });
const norm = (s: unknown) => String(s ?? '').trim();

const idByEmail = new Map<string,string>();
const idByName  = new Map<string,string>();
const created: { email: string; reportsToRef: string }[] = [];
let added = 0, skipped = 0;

// Pass 1: create every valid row (reportsTo left null)
for (const r of raw) {
  const name = norm(r['Name']), email = norm(r['Email']);
  if (!name || !email) { skipped++; continue; }
  if (existing.some(u => u.email.toLowerCase() === email.toLowerCase())) { skipped++; continue; }
  const role = (['SuperAdmin','DepartmentHead','Member'] as const).includes(norm(r['Role']) as never) ? norm(r['Role']) as User['role'] : 'Member';
  const id = `user-${Date.now()}-${added}`;
  idByEmail.set(email.toLowerCase(), id); idByName.set(name.toLowerCase(), id);
  onAddOrUpdateUser?.({ id, name, email, position: norm(r['Position']) || 'Member',
    grade: '', department: norm(r['Office']) || 'General', reportsTo: null, role,
    phone: '', bio: '', joinDate: new Date().toISOString().slice(0,10), active: true });
  created.push({ email: email.toLowerCase(), reportsToRef: norm(r['Reports To']) });
  added++;
}
// Pass 2: wire reportsTo by looking up the ref in the created set (or existing users)
for (const c of created) {
  const ref = c.reportsToRef; if (!ref) continue;
  const refId = idByEmail.get(ref.toLowerCase()) || idByName.get(ref.toLowerCase())
    || existing.find(u => u.email.toLowerCase() === ref.toLowerCase() || u.name.toLowerCase() === ref.toLowerCase())?.id;
  if (refId) onAddOrUpdateUser?.({ ...existingUserByEmail(c.email), reportsTo: refId });
}
```
- Header names are the contract — keep them stable and match the template exactly (Name, Email, Position, Office, Reports To, Role).
- Map "Office" → your `department` field, "Reports To" → `reportsTo` (id, resolved in pass 2).
- Gate the buttons to the privileged role (SuperAdmin) so DeptHead/ Member can't bulk-import.
- Surface a toast: `${added} added, ${skipped} skipped (missing name/email or duplicate)`.
- After import the org-chart/hierarchy view renders automatically because it reads `reportsTo` from the same store.

## Verify
Build green; grep the deployed bundle for a marker only the new code contains (e.g. `RINA-users-template`). See `vercel-prod-deploy-verification` bundle-grep recipe.
