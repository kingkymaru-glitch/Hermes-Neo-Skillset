# JSX Extension Pitfalls in Vite + React + TS Projects

Observed failure mode:
- `.jsx` files containing TS syntax like `import type { User } from '../types';` under Vite/Rolldown parser rules during `npm run build`.
- `App.tsx` self-import or sibling import with wrong relative path like `./Login` when file is `./components/Login.tsx`.

Fix:
- Use `.tsx` everywhere for JSX in TS projects.
- Use exact relative paths in imports.

This note is intentionally short because the SKILL.md captures the exact rule set; this file just records the raw failure signatures found in the first RIINA scaffold build.
