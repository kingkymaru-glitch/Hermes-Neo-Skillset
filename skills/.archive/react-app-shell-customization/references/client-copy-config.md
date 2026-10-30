# Client copy config pattern (`src/config/copy.ts`)

Used when re-injecting a client's branded taglines into an app that was previously
genericized. Keeps the codebase generic — the next customer is a one-file swap.

## Shape
```ts
// src/config/copy.ts
export const copy = {
  brandHeader: 'Organizational Clarity',
  brandFooter: 'RINA — Roles. Initiative. Network & Achievement',
  tagline: 'Organizational Clarity: Ensuring no strategic initiative falls through the cracks.',
  subtext: "Visibly map every team member's contributions, workload, and achievements to TNB's strategic goals.",
  dashboardTitle: 'Organizational Clarity',
  dashboardSubtitle: "Visibly map every team member's contributions, workload, and achievements to TNB's strategic goals.",
  loginTagline: 'Organizational Clarity: Ensuring no strategic initiative falls through the cracks.',
  loginSubtext: "Visibly map every team member's contributions, workload, and achievements to TNB's strategic goals.",
  emptyTasksTitle: 'No active initiatives yet',
  emptyTasksBody: 'Create the first strategic initiative to make progress visible across the organization.',
} as const;
```

## Usage
- Import in each surface: `import { copy } from '../config/copy';`
- Render `{copy.loginTagline}` etc. — components never contain the literal sentence.
- Surfaces touched in the RIINA TNB case: `components/Login.tsx` (hero), `App.tsx`
  dashboard case (header block), `components/MyTasks.tsx` (empty state).

## Why a config module (not props/localStorage)
This is static per-deployment copy, not user-editable branding. localStorage persistence
(see phase1-localstorage-branding.md) is for Phase-1 admin-editable identity; client
taglines are deployment-time constants. One file = one edit to rebrand for the next
customer. If the user wants admin-editable copy too, combine: default from `copy`,
override via localStorage in AppShell.

## Pitfall
If the user previously demanded full genericization, re-adding client strings reverses
that — flag it. The config-file approach means the reversal is isolated and reversible
(the genericization is NOT destroyed; only `copy.ts` is client-specific.
