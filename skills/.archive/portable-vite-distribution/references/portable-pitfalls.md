# Portable Vite distribution — pitfalls & gotchas

## 1. oxlint config: `ignorePatterns`, NOT `ignore`
This burned a verification cycle. The supported key is `ignorePatterns`.
Using `ignore` fails to parse:
```
x Failed to parse config with error Error("unknown field `ignore`,
  expected one of `$schema`, `plugins`, `jsPlugins`, `categories`, `rules`,
  `settings`, `env`, `globals`, `overrides`, `options`, `ignorePatterns`,
  `extends`", line: 0, column: 0)
```
Correct `.oxlintrc.json`:
```json
{
  "plugins": ["react", "oxc"],
  "ignorePatterns": ["dist", "node_modules"],
  "rules": { "react/rules-of-hooks": "error" }
}
```

## 2. Never lint-scan `dist/`
`dist/` contains the minified Cesium bundle (`dist/cesium/Cesium.js`). Scanning it
produces ~18,610 warnings + 2 false "errors" from minified code. Always ignore
`dist` in oxlint (and don't `cat`/`grep` it by hand).

## 3. Dev `/api` proxy is dead unless the app calls through it
Adding `proxy: { '/api': { target: 'http://localhost:4173' } }` to `vite.config.js`
does NOTHING unless (a) Vite is actually running AND (b) the app fetches a path
starting with `/api`. In dev, run `server/local-server.mjs` (4173) in the
background, then `npm run dev` (Vite) — Vite proxies `/api` → 4173. Verify with
`curl http://localhost:<vite-port>/api/nodes` → proxied response.

## 4. The static server MUST serve `dist/cesium/*`
Cesium resolves its workers/assets via `CESIUM_BASE_URL` = `/cesium`. If your
static server doesn't serve `dist/cesium/Cesium.js` etc., the globe silently
never renders. Verify: `curl -s -o /dev/null -w "%{http_code}" http://localhost:4173/cesium/Cesium.js` → `200`.
A Vite `base` path change can break this — keep `base: './'` or serve from root.

## 5. `&` backgrounding is rejected by `terminal()`
One `terminal()` call with `node server &` fails:
"Foreground command uses '&' backgrounding. Use terminal(background=true)..."
Always start long-lived servers via `terminal(background=true, watch_patterns=[...])`
and then poll/wait, then run curl checks in a separate foreground call.

## 6. Kill stray servers before testing
Earlier sessions leave servers on 5174/5175/5176 (Vite) and 8799 (old bridge).
If you test against the wrong instance you'll see stale/ghost data. Before a
verification run: `lsof -iTCP:4173 -sTCP:LISTEN` etc., and `kill` the PIDs.

## 7. Commit `dist/` for the USB build
The whole point is the client runs with no build step. So `dist/` must be
committed/zip-shipped, not git-ignored. Keep `data/` tracked too (records travel).
Use `data/nodes/.gitkeep` so the empty folder ships.

## 8. Relative API path is the core portability fix
Hardcoded `http://localhost:8799/api/nodes` ties the app to one machine/port.
Switch to `const NODES_API = '/api/nodes'` so the app is same-origin everywhere.
