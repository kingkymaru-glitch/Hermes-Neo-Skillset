# Oxlint Project Scoping for Vite+React+TS Scaffolds

## The problem
Fresh Vite + React + TypeTS scaffolds often have zero project-source lint errors, but `oxlint` still shows noise from `node_modules` and exits non-zero. That breaks the “clean pass” acceptance criterion before visual polish is even checked.

## Verified working shape
1. `.oxlintrc.json` at project root:
```json
{
  "plugins": ["oxlint/plugin-react"],
  "ignorePatterns": ["**/node_modules/**"],
  "settings": { "react": { "version": "19" } },
  "rules": { "react/react-in-jsx-scope": "off" }
}
```
2. `package.json` lint script:
```json
"lint": "oxlint --no-error-on-unmatched-pattern src"
```
3. Project-local fixes that often show up together:
- `src/vite-env.d.ts` must be exactly `/// <reference types="vite/client" />`, not a malformed XML-ish tag.
- Remove dead imports / unused variables from hooks/components; this is where oxlint catches real issues after scoping.

## Why this matters
If you only change the script without the `.oxlintrc.json`, you get noisier output. If you only add `.oxlintrc.json` without scoping the script, external paths can still poison the run. Do both.

## Workspace evidence
In the RIINA prototype (`~/riina`), the path to clean zero-error lint was:
- add `.oxlintrc.json` with react plugin + ignorePatterns
- rewrite `src/vite-env.d.ts`
- patch `package.json` lint script to `oxlint --no-error-on-unmatched-pattern src`
- remove dead `storage` import in `src/hooks/app.tsx`

After that, `npm run lint` passed cleanly in ~18-25ms on project sources only.
