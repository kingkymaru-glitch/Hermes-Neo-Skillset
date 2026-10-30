# Post-Rename Verification

Exact steps that produced a clean rename in this session (`RIINA` -> `RINA`).

## Search pattern
Use case-insensitive exact match across the whole `src/` tree before and after edits.

```bash
# ideal: zero exact matches after rename
```

## Edit locations (in order of frequency)
1. Component display text and branding defaults (`AppShell.tsx`, `Login.tsx`, `AdminPanel.tsx`, mock notifications).
2. App footer/header default strings in the root component (`App.tsx`).
3. localStorage key prefixes in storage helpers and session cleanup code.

## Verification procedure
1. `npm run lint`
2. `npm run build`
3. Manual search for zero matches

## Pitfalls caught this session
- An unnecessary `useState` import was added to `Analytics.tsx` while making a separate permission change, then surfaced as a lint warning. Fix: re-read the import line and remove any import not actually referenced below it.

## Evidence this worked (2026-07-22)
- Codebase search: 0 exact `RIINA` matches after rename.
- `npm run lint`: 0 warnings, 0 errors.
- `npm run build`: exit 0.
