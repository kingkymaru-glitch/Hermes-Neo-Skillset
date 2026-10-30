# Founder Project Conventions (condensed)

## Vault
- ROOT_DIR: `~/Documents/obsidian_maru_1` (Hermes PRIMARY referral/update surface).
- Resume order: `VAULT MAP.md` → `HermesProgress.md` → `/Projects` → `DT Inspection *`.
- Note convention: `Projects/<NAME>.md`, frontmatter `tags: [maru, <name>, ...]`.
- VAULT MAP.md has a `/Projects` list + a `<!-- graphify:related -->` Related block — add
  both the list entry and a `[[<NAME>]]` line.

## GitHub repo defaults (this founder)
- `gh repo create <NAME> --private --license MIT --description "..." --clone`
- Account: `kingkymaru-glitch` (token via `gh auth`, scopes fine). Repos default private+MIT.
- Local clone lands at `~/<NAME>`.

## MARU overlays (the "connect the dots later" hub model)
1. **Situational** — exists. `src/components/SituationalEntities.jsx`: geo-anchored Cesium
   <Entity> pins + click-HUD, color-coded severity, governance-gated toggle. Clone pattern for
   any new overlay.
2. **VISION / threat** — standalone DMS-CV project → this class. Edge CV (YOLO/TensorRT +
   DPQ-ERR scheduler) → JSON events → operator threat matrix + map + video grid. Seam =
   JSON contract + `POST /api/v1/ingest`. Repo: `kingkymaru-glitch/VISION`, local `~/VISION`.
3. **LUNAV / maintenance** — LunaV Solutions (3D inspection SaaS, `SS Rover Cloud.md`).
   Additive overlay = maintenance placeholders on assets. Operator-authored, slow cadence.

## The seam pattern
One JSON contract + one ingest endpoint. Edge/feeder emits it; hub reads the same envelope
later. MARU's `EdgeDataContext` `real` mode currently expects `{ sensorPayloads: [...] }`;
extend to `{ sensorPayloads, threatEvents }` at wiring — don't change the contract schema.

## Phasing template (each step independently demoable)
- P1 contract + ingest server + mock/edge-sim (runnable, no UI, verified via stdout-to-file).
- P2 operator workbench (threat matrix + map + video grid + clustering).
- P3 wire to hub (add feed to EdgeDataContext; clone SituationalEntities → new pins; toggle).

## VISION design facts (for context, not duplication)
- DPQ-ERR: round-robin 10 of 50 cams @ 2 FPS; lock EOI cam into priority slot; 5-cycle cooldown
  on clear; emit CLEARED at 0. Event-driven <10 Mbps WAN vs 240 Gbps always-on.
- Coordinate model: station center + per-camera offset → absolute lat/lon on every event (geo
  anchor). Station-aware from day one (fleet, not single-site).
