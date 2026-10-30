---
name: i-nation-2026-mission-labs
description: Use for I-Nation 2026, MRANTI, SawitDigit, PTK2Dron.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [i-nation, mranti, granti, mission-labs, sawitdigit, ptk2dron, drone-pipeline, oil-palm, low-altitude-economy, proposal]
    related_skills: [lunav-studio, lunascan-development, gaussian-splatting-pipeline]
---

# I-Nation 2026 Mission Labs — LunaV positioning

## When to Use

Load this when MARU talks about any of:
- I-Nation 2026, MRANTI, GRANTI, GTSA, Mission Labs, Pods
- SawitDigit, SawitElite, SawitPure (Oil Palm pods)
- PTK2Dron or the Low Altitude Economy pods
- The LunaV aerial / drone data pipeline, nursery-to-mill data backbone
- Preparing an Expression of Interest or positioning for a grant/mission opportunity

> Triggers: I-Nation 2026 · MRANTI · SawitDigit · PTK2Dron · GTSA · Mission Labs ·
> LunaV aerial / drone data pipeline · nursery-to-mill data backbone.

## Status

- **Expression of Interest registered by MARU (2026-10-25).** Registration does not
  guarantee a seat — Labs are curated. Next work is the pod-specific pitch text and
  the demo.

## The opportunity

I-Nation 2026 (MRANTI, **11 Nov 2026, Le Méridien Putrajaya**) is not a conference.
It is four **closed-door Mission Labs** of 40–50 curated decision-makers "with the
authority to commit". Each lab is broken into **Pods** — small time-bound pilots with
a named lead, a success measure and a stop-or-continue point.

Four pod roles: **Problem Owner** (defines the challenge), **Co-Developer** (brings
delivery capability), **First Customer** (commits to adopt), **Industry Aggregator**
(pulls in its supply chain). LunaV's realistic seat is **Co-Developer**.

Five-step journey: Express Interest → Join the Mission Lab → Lead or Join a Pod →
Pilot and Validate → Commercialise and Scale.

Apply at `form.evenesis.com/i-nation-2026`; enquiries `hello@mranti.my`.
**Registration does not guarantee a seat** — Labs are curated and aimed at Heads of
Department and senior decision-makers.

Full pod requirements (baseline data each wants, partner types each asks for) are in
`references/i-nation-pod-requirements.md`.

## The two pods we target — and the rest we skip

| Mission Lab | Pod | Take? |
|---|---|---|
| Oil Palm | **Pod 3 SawitDigit** — connected data backbone nursery→mill, AI for off-type culling + ripeness detection | **YES — target** |
| Low Altitude Economy | **Pod 3 PTK2Dron** — disaster preparedness/emergency response, data-sharing + analytics for flood/SAR/delivery | **YES — target** |
| Oil Palm | Pod 1 SawitElite (breeding/gene editing) | no |
| Oil Palm | Pod 2 SawitPure (DNA seed QA) | no |
| LAE | Pod 1 supply-chain resilience (OEM/manufacturing) | no |
| LAE | Pod 2 regulatory/certification pathway (CAAM) | no |
| Autonomous Mobility | all 4 pods | no — only thin hook is Pod 3's "mapping/C-ITS provider"; we'd be a supplier |
| Healthy Ageing | all 3 pods | no — clinical, no health product or data |

## The core idea: one pipeline, two modes

**SawitDigit and PTK2Dron are the same pipeline with different triggers and
audiences.** One is scheduled commercial ops, the other is on-demand emergency
response. Both end at a processed 3D record + analytics shared to decision-makers.
So the pitch is: one Supabase project, one GPU worker queue, one 3D viewer, one share
mechanism, one edge runtime — run in two modes.

- **SAWIT mode** (scheduled): nursery → estate → mill, recurring capture, commercial analytics
- **DRON mode** (on-demand): activate → deploy → map → respond, mission-logged

## Pipeline stages — built vs to-add

| Stage | Already built | Must add |
|---|---|---|
| 1 Capture | LUNASCAN (drone video→frames/masking/photogrammetry), Luna-EDGE (offline YOLO), ROVER-KIT camera ingest | flight planning, **repeat-capture scheduling**, telemetry, optional multispectral |
| 2 Ingest | R2 presign upload, Supabase Storage (`gpu-jobs`/`models`), `gpu_jobs` queue | imagery object store keyed site/date/mission, capture manifest, dataset versioning |
| 3 Process | PC2 GPU worker queue; job kinds `odm`, `splat`, `yolo` | `ripeness` (virescens), `offtype`, `flood` (+DEM), `change`, `sar_grid`, `volume`; model registry + training loop |
| 4 Analyse | LUNAV Intel-M — IsolationForest + LSTM anomaly detection, RandomForest RUL | geospatial analytics (coverage %, change maps, ripeness distribution, flood extent, SAR sectors), threshold alerts |
| 5 Record | LunaV Studio — models, markers, zones, certificates, audit report, analytics, documents, share | site asset tree (region→estate→block→palm / mill→line→equipment), block harvest/FFB logs, **mission records** (activation, deployment time, coverage, outcome, cost), MDV-style signed event log |
| 6 Share+Command | LunaV client share token, R-Tessera `project_nodes`/`get_shared_project`/handoff, CctvVisionPage, GpuStatusChip | role-based access, live mission board, alert routing |
| 7 Edge+Sync | Luna-EDGE offline webapp, ROVER-KIT edge worker + tunnel, RoverKitStatus | **offline-first store-and-forward sync**, edge inference for ripeness/off-type, local mission cache |

## Honest gaps — do not overclaim these

1. **No oil palm data.** Platform exists, dataset does not. Need a plantation/mill
   partner, or apply explicitly as the platform layer seeking a data owner.
2. **No trained ripeness/off-type models.** LabelCanvas exists for labelling; the
   models do not. Both need labelled datasets first.
3. **No flight-planning module** — capture is manual today.
4. **No disaster SOPs or agency relationships** (NADMA, JBPM, PDRM) — PTK2Dron is
   MRANTI-coordinated, so that door is theirs to open.
5. **No multispectral capture** — useful, not required to start.

## Demo path (what can actually be shown)

1. Live drone→3D run (LUNASCAN + PC2 queue)
2. LunaV Studio with a site asset tree + pinned findings
3. LUNAV Intel-M anomaly detection on real sensor data
4. **CDM flood simulation** as the PTK2Dron analytics layer — already built
5. Luna-EDGE offline detection as the edge/connectivity story

## Artifacts

- Positioning brief (diagram + stage table + gaps + demo path):
  `~/i-nation-2026/lunav-pipeline-brief.md`
- Narrative one-pager (research fragmentation → study-to-commercial packaging story):
  `~/i-nation-2026/lunav-decision-platform.html` (self-contained, no build, opens in a browser)
- Expression of Interest text, both pods, ready to paste:
  `~/i-nation-2026/eoi-submission.md`
- Full pod requirements transcribed from mranti.my:
  `references/i-nation-pod-requirements.md`
