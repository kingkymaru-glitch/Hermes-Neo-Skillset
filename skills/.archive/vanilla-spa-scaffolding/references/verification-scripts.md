# Node verification patterns for vanilla SPA projects

Use `tests/test.js` with synchronous filesystem assertions rather than a test runner framework.

## Test setup
Place in `/tests/test.js` with ESM imports:
`import fs from 'fs'; import path from 'path'; import { fileURLToPath } from 'url';`

## Common checks
- `index.html` contains shell markers:
  - `<main id="mainContent">`
  - `<nav class="tabs"`
  - `<footer`
- `main.js` contains:
  - `import` or `from` references to `./utils`
  - bootstrap functions: `renderPanels`, `renderTabs`, `restoreDraft`
- `src/api/client.js` contains:
  - `export const api`
  - `/parse`
- `src/styles/main.css` contains:
  - CSS variables such as `--primary`
  - `@media`
- `package.json` parses to object with:
  - `name`
  - `scripts.start`
  - `scripts.test`

## Framework exclusion
Scan source files and fail if `react`, `vue`, or `@angular/` appear in source.

## ESM/package.json hygiene
- Add `"type": "module"` to package.json when tests use ESM syntax.
- Run `node --check` for JS syntax if possible; then `npm test`.
- Always fix test failures before claiming completion.

## Tar packaging note
For archive step where status code is `126` on a naked directory, use:
`tar -czf out.tar.gz -C /path/to/parent dirname`
