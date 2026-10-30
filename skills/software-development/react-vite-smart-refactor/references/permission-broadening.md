# Permission Broadening Pattern

Pattern for changing a role-scoped view to global visibility in a dashboard app.

## Context
Changing Analytics.tsx from "SuperAdmin sees all; others see only own department" to "all members see overall department load."

## Steps
1. Find the accessible scope derivation; it usually looks like:
   ```ts
   const base = Array.from(new Set(tasks.map(t => t.department)));
   const accessible = role === 'SuperAdmin' ? base : [department];
   ```
2. Replace second line with `const accessible = base;`.
3. ALSO find any exclusion filters chained to the same list, e.g.:
   ```ts
   .filter((d) => d !== 'Digital Transformation')
   ```
   Remove them; otherwise departments disappear from the global view.
4. Verify that visible-task filtering uses `accessible.includes(...)`.

## Pitfall
A role check AND a domain-level exclusion can both constrain output. Changing one without the other leaves the UI broken or silently incomplete.

## Evidence this worked (2026-07-22)
Before:
```ts
const baseDepartments = Array.from(new Set(tasks.map((t) => t.department))).filter((d) => d !== 'Digital Transformation');
const accessibleDepts = role === 'SuperAdmin' ? baseDepartments : [department].filter((d) => d !== 'Digital Transformation');
```
After:
```ts
const baseDepartments = Array.from(new Set(tasks.map((t) => t.department)));
const accessibleDepts = baseDepartments;
```
