# MARU — 5-Box architecture frame

The user thinks and names work in terms of this architecture. Map any request
to the right Box so future sessions stay aligned.

MARU = **M**ultimodal **A**nalysis & **R**eal-time **U**nderstanding agent — a
lightweight, liability-aware **triage toolkit** for Structural Health Monitoring
(SHM). Competitive edge vs Bentley iTwin / Autodesk Tandem / Resensys: it is the
connective tissue that visualizes spatial defect data alongside geotech
telemetry, then subjects it to standard-code-governed engineering rules.

```
       ┌───────────────────────────────────────────────┐
       │ BOX 5: MARU  (orchestrator — Sense/Understand/  │
       │         Decide/Act loop)            [planned]    │
       └───────────────────────┬───────────────────────┘
   ┌──────────────┬────────────┴───────────┬──────────────────┐
   ▼              ▼                        ▼                  ▼
 BOX 1         BOX 2                   BOX 3              BOX 4
 Spatial Base  IoT Windsshield         Rules & RAG        Engineer's
 (3D canvas +  (telemetry HUD          (vectorized       Intuition
  LiDAR/points) over spatial points)    codes / specs)    (heuristics)
 ← THIS REPO   ← THIS REPO (next)      [planned]          [planned]
```

| Box | Name | What it is | Status in `my-digital-twin` |
| --- | ---- | ---------- | --------------------------- |
| 1 | Spatial Base | Resium/Cesium 3D canvas; programmable API to log/measure spatial pins | **Built** |
| 2 | IoT Windscreen HUD | High-freq telemetry (tilt/strain/accel) as 2D HUD over 3D points; keep off render thread | **Next build (Layer 2)** |
| 3 | Rules & RAG | Engineering codes vectorized into Supabase pgvector; swap sets (Eurocode / JKR) without code changes | Planned |
| 4 | Engineer's Intuition | Structured heuristic profiles for failure archetypes / site context | Planned |
| 5 | MARU | CrewAI Flow + MCP tools; multimodal SUDA loop; voice + `defect_node` bookkeeping | Planned |

## How the user references features
- "Layer 2 HUD" / "Windscreen overlay" = Box 2 telemetry HUD on the canvas.
- "Box 1" = the current 3D canvas / spatial base.
- "defect_node", "structural_anchor", "telemetry_reading", "sensor_metadata",
  "archetypes" = target Supabase tables (decoupled per architecture rec).

## Durable constraint
Keep `my-digital-twin` a **Vite + React SPA**. No Next.js, no monorepo.
Confirmed by the user twice; the repo README reflects this.

## Companion design docs (user-provided, on Desktop)
- `DT CIVIL MARU/MD FIle IDEA/MARU_Architecture_Core.md`
- `DT CIVIL MARU/MD FIle IDEA/MARU_Development_Steps.md`
- `DT CIVIL MARU/MD FIle IDEA/SHM_Market_and_Github_Landscape.md`
