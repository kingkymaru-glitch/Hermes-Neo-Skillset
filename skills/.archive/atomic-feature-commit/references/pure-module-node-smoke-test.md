# Smoke-test a Vite/ESM pure module under Node (no browser)

When a module is framework-free (no React / Cesium / DOM) but uses extensionless
relative imports (`./foo`, not `./foo.js`), **raw `node x.mjs` FAILS**:

```
ERR_MODULE_NOT_FOUND: Cannot find module './foo' imported from ...
```

Vite/webpack resolve extensionless imports; raw Node ESM does not.
`--experimental-specifier-resolution=node` is deprecated/ignored on modern Node,
so don't rely on it.

## Reliable method — bundle with esbuild, then run

esbuild ships with Vite, so `npx esbuild` works without a separate install.

```bash
cat > /tmp/smoke.mjs <<'EOF'
import { createGovernance } from '/abs/path/src/feature/service.js'
import { POLICY } from '/abs/path/src/feature/registry.js'

# Shim any browser globals the module touches (localStorage, etc.)
globalThis.localStorage = {
  _m: {},
  getItem(k) { return this._m[k] ?? null },
  setItem(k, v) { this._m[k] = v },
}

const g = createGovernance(POLICY)
console.log('NORMAL cap (expect 80):', g.status('openweather').cap)

# Exercise the gate: burn calls, then assert it blocks at the limit.
for (let i = 0; i < 80; i++) { g.ask('openweather'); g.record('openweather') }
console.log('after 80, ask (expect allow:false):', JSON.stringify(g.ask('openweather')))
console.log('pill color (expect tripped):', g.status('openweather').color)

# Mode / kill-switch / disabled / fail-open assertions...
g.setMode('off')
console.log('OFF ask (expect allow:false):', JSON.stringify(g.ask('openweather')))
EOF

npx esbuild /tmp/smoke.mjs --bundle --platform=node --format=esm \
  --outfile=/tmp/smoke.bundle.mjs --log-level=error
node /tmp/smoke.bundle.mjs
```

## Why this matters
lint + build only prove the code *compiles*. A real execution catches logic bugs
that a green build would ship — e.g. an OFF mode that returns `allow:true` instead
of blocking egress, or a circuit-breaker threshold computed wrong. Always
smoke-test pure gate / registry / circuit-breaker logic before committing.

## Gotchas
- Use **absolute** import paths in the temp test so esbuild resolves cleanly.
- If the module reads `import.meta.env`, that won't exist under Node — stub it or
  test the pure function in isolation.
- Clean up `/tmp` artifacts; they are not part of the repo.
- Keep the smoke test OUT of the committed tree unless the user wants a formal
  test suite (for creative-UI phases they may prefer to eyeball first).
