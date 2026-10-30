# Env-gated DCE: the false "stale build" trap

## Symptom
After editing `src/context/EdgeDataContext.jsx` (added S22 Ultra endpoints behind an
`EDGE_MODE === 'android'` branch) and adding a `/s22-api` dev proxy, repeated
`npm run build` runs produced an identical bundle hash and the bundle did NOT
contain the new strings (`/s22-api`, `192.168.0.84`, `/sensors.json`). The
build-verification gate repeatedly flagged the result as "stale".

## Wrong hypotheses chased (and rejected)
- **Stale Vite transform cache** (`node_modules/.vite`): clearing it changed
  nothing — because the cache was never the cause.
- **Corrupt module graph**: no — the source file was confirmed correct via grep.

## Root cause
`vite build` statically replaces `import.meta.env.VITE_EDGE_MODE` with the literal
value. Unset → `undefined`. So `EDGE_MODE = import.meta.env.VITE_EDGE_MODE || 'mock'`
collapses to `'mock'`, and `EDGE_MODE === 'android'` folds to `false`. esbuild's
minifier **dead-code-eliminates the entire android branch**, including the only
references to `S22_BASE`, `STREAM_URL`, `TELEMETRY_URL`, etc. The strings are
correctly absent from a mock-mode bundle.

## Definitive test (the one that resolves it)
Build in the mode that exercises the branch, then grep the actual bundle:
```
VITE_EDGE_MODE=android npm run build
B=$(ls -t dist/assets/*.js | head -1)
grep -qo "/s22-api" "$B" && echo YES || echo NO        # → YES
grep -qo "192.168.0.84" "$B" && echo YES || echo NO    # → YES
grep -qo "/sensors.json" "$B" && echo YES || echo NO    # → YES
```
All present → the config is genuinely wired. The earlier "missing strings" was DCE,
not corruption.

## Takeaway
- Don't trust or distrust a build hash. Grep the bundle for a marker string, and
  build in the env mode that actually uses the code path.
- Identical hashes across turns are often legitimately identical (idempotent
  mock-mode output). Reserve cache-wipes for when grep proves the *branch that
  should run* is still absent after building in the correct mode.
