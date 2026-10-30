# Relative Import Drift After Adding Components

Observed in: `~/riina` scaffold while adding `src/components/*.tsx`.

Failure:
- `npm run build` fails with `[UNRESOLVED_IMPORT] Could not resolve '../data/mock' in src/App.tsx`.

Cause:
- `src/App.tsx` is at the `src` root. Once sibling components are referenced as `./components/...`, sibling data imports should use `./data/...`, not `../data/mock`.

Fix:
- Change `import { mockData } from '../data/mock'` to `import { mockData } from './data/mock'`.

Verification:
- `npm run build` passes after correction.
- Lint shows no project-local errors; warnings remain confined to `node_modules`.

Lesson:
- When importing from root-level `src` files, use `./...` relative paths from `App.tsx`, not `../...`.
