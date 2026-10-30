# Session Resume & Stale-Memory Reconciliation (references)

## Wake-up checklist (run before any work on a resume/fresh-chat prompt)
1. `read_file` `VAULT MAP.md` — index; confirms current product names + note locations.
2. `read_file` `HermesKeyMemories.md` — durable backup of active-project facts; mirror of injected memory.
3. `read_file` `HermesProgress.md` — running log; most recent entries show last shipped work + open blockers.
4. Spot-check the relevant `Projects/` note (and any note the user explicitly named) only if the task needs it.

Steps 1–3 are unconditional. Use `read_file` (line-numbered, paginated) not `cat`.

## Worked example — MARU / R-Tessera false positive (2026-07-27)
- **Symptom:** Injected memory claimed "Founder sold MARU 2026-07-23. LIVE fork = R-Tessera (GH kingkymaru-glitch private, port 5175)." This implied a product rename/sale.
- **Vault check:** `HermesKeyMemories.md` (dated 2026-07-27, AFTER the claimed sale date) recorded NO sale and no rename. `Projects/SSR - R-Tessera.md` was NOT a rename note — it was an internal CesiumJS dual-layer basemap refactor spec (Esri 2D default + lazy Google Photorealistic 3D Tiles toggle).
- **Ground truth:** cwd = `~/my-digital-twin` (the MARU repo); latest git log = MARU-SHIFU sensor-bridge work. No rename anywhere in the actual repo.
- **Resolution:** Vault + cwd both contradicted the injected claim → treated the injected "sold" note as STALE. Corrected injected memory via `memory` `replace` (concise version) so future sessions don't re-act on it. Did NOT rename anything.
- **Rule established:** vault dated after the injected reference date wins; if the vault is silent, cwd/repo ground truth wins; only ask the user when both are genuinely ambiguous.

## Why this matters
Acting on a stale injected "rename/sale" would have changed product naming, repo assumptions, and deployment targets for the whole session — all wrong. Three cheap reads prevented it. The vault is the durable source; injected memory is volatile and can carry reversed or abandoned plans.
