# TSX Iterative-Edit Hygiene

## Recovery Patterns

### Reusable UI extraction
- Create one shared component when the same JSX pattern appears in 2+ views.
- Example: `src/components/BackButton.tsx` with `onClick` and optional `label`.
- Replace inline copies across sibling components, then rerun build/lint.

### Duplicate-import repair
- Symptom: file has two `import BackButton from './BackButton'` lines, or `react(jsx-no-undef)` fires for a component already present elsewhere.
- Do not keep patching the same region: if two targeted edits already misaligned the import block, read the whole file and rewrite the top import block instead.
- Keep imports grouped: React, third-party libs, local components.

### Unused-import lint cleanup
- When adding a shared component, remove now-dead inline imports or unused type imports.
- Common leftover artifacts after `BackButton` extraction: `ReactNode`, `View`, duplicate `type` imports.
- oxlint mode in this scaffold can surface these as warnings quickly; clean them up before the next build claim.

## Verification Cadence
During iterative UI fixes, run `npm run build && npm run lint` after every 2-3 small UI patches. Catch import/lint drift early rather than replaying a long batch at the end.
