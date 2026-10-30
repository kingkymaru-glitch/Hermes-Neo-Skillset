# MARU Products → Vertical-AI Thesis Map

How ROVER-KIT and LunaV already satisfy the "defensible vertical AI" profile, and the
one arrow to pull (toward agentic automation). Built 2026-08-25.

## ROVER-KIT (DMS-CV / substation edge-AI vision)
- What it is: offline edge-AI computer vision for substation / DMS-CV inspection.
  MIT, private repo `kingkymaru-glitch/ROVER-KIT`, local `~/VISION`.
- Already defensible: substation defect dataset + offline edge runtime + energy-regulatory
  domain.
- Agentic target: Vision -> Measure -> Classify -> Route agents, all air-gapped on the edge.
- Pitch line: "Physical AI for the grid edge — agentic inspection that runs offline."

## LunaV (R-Tessera / Studio / Labs / WebAR / Dimension Tool)
- What it is: CesiumJS 3D digital-twin for infrastructure inspection. Dimension Tool =
  manual inspection record (value + note), pale-yellow AutoCAD-style markers.
  WebAR at lunavsolution.vercel.app/ar/.
- Already defensible: inspection-record schema + CesiumJS geo domain + WebAR field capture.
- Agentic target: twin becomes self-reporting — deviations from baseline auto-generate
  inspection records + tasks.
- Known link gap: R-Tessera -> Studio is live (one-way); Studio -> R-Tessera Labs back-link
  is MISSING. Close it so twin + SaaS read as one surface.

## Shared moat argument
One agent runtime (Vision/Measure/Classify/Compare/Route/Drift/Report) serving two
front-ends (edge for ROVER-KIT, web twin for LunaV). Lower cost to scale, one pitch
surface, future-proof (secure AI = Gartner #9). None of the agent layer requires
rewriting the core CV model — it's a thin layer on top.
