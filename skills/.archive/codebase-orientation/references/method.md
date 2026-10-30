# Codebase Orientation — Method & Example Notes

## Condensed technique

1. Version = three sources, always cross-check:
   - `package.json` `version`
   - in-code constant (grep `VERSION =` / `APP_VERSION`)
   - git: `git describe --tags --always`, `git tag`, `git log --oneline -8`,
     `git branch --show-current`, `git status --short`
   - Report HEAD-vs-tag commit delta + any mismatch.

2. Surface the source tree fast:
   - `search_files` target=`files` pattern=`*` in `src/` → every module.
   - Read config/registry files first (`*Registry`, `*Service`, `*Manager`,
     `apiUtils`, `vite.config`) — they declare features declaratively.

3. Map functions:
   - `search_files` output_mode=`content` with a combined pattern, e.g.
     `^(function|const) |export (function|default|const)|<Component|fetch|connect`
   - Group by area; table each: Function | What | Status | Location.

4. Status vocabulary: LIVE / SCAFFOLD (key/env-gated, disabled rows) / NOT BUILT.
   Back every claim with `file:line`. Never invent symbols.

5. Architecture: short ASCII "who calls whom" tree + swap paths for persistence.

6. Fork notes: how to add a layer/provider, swap storage, env vars, ports
   (flag collisions), crash caveats.

7. Verify: `npm run lint` + `npm run build` for JS/TS; facts from real reads.

## Real example (MARU / my-digital-twin, 2026-07-23)

- Version: app reports `v0.2.0-STABLE` (App.jsx:92); git tag `v0.2.0` @ ac9ba47;
  but `package.json` = `0.0.0` and HEAD 48 commits ahead. → recommended bump.
- Registry-driven: `layerRegistry.js` (map layers), `governanceRegistry.js`
  (egress providers). Adding a feature = one config object, no map rewrite.
- Status split:
  - LIVE: globe + base layers, governance gate, mock telemetry, Obsidian-backed
    Map Nodes (local bridge localhost:8799), Situational Context (keyless),
    Connection Manager (S22/iPhone via Vite proxy).
  - SCAFFOLD: weather overlays (need VITE_OPENWEATHER_API_KEY), `futurePaid`
    provider (disabled), `assets` Supabase table missing (falls back to demo).
  - NOT BUILT: in-globe GLB (crashed renderer → avoided; Dam Gate shown via
    sandboxed iframe of standalone Three.js HTML).
- Gotcha that produced a memory correction: prior notes referenced RIINA
  branding / `AppShell.tsx` / `AdminPanel.tsx` — those belong to a DIFFERENT MARU
  fork. The `my-digital-twin` repo has none of them. Always map the actual repo,
  not stale cross-fork memory.
- Port: nodes bridge on 8799 (NOT 8787 — collides with cursor-hy3-proxy).

Deliverable written: `MARU_FUNCTION_MAP.md` (see SKILL.md §Deliverable Structure).
