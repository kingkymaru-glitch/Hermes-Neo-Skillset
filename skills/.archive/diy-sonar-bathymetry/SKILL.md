---
name: diy-sonar-bathymetry
description: DIY sonar and ROV bathymetry mapping.
---

# DIY Sonar Bathymetry & ROV 3D Mapping

Triggers: "build a sonar", "3D bathymetry", "multibeam/MBES", "single-beam/SBES",
"ROV sonar camera", "Sonair-style", "USBL", "stitch sonar point clouds", "Open Echo",
"cheap bathymetry without commercial survey", "LUNASCAN-SONAR".

## Core mental model
Sonar bathymetry = time-of-flight ranging. Depth D = (c × t) / 2, where
c = speed of sound in water (~1500 m/s, VARIES with temperature/salinity/depth — measure
it with a sound-velocity probe, never assume). Everything past the ranging equation is
correcting that number: transducer draft, heave (waves), tide (datum), ray bending (SVP
refraction), and vehicle attitude (roll/pitch/heading).

## Key design decisions (with pitfalls)
- LINEAR array, not a 2D "DSLR square" grid, for traverse-mapping. A boat/ROV moving
  forward supplies the along-track axis; the array only needs to steer across-track. A 2D
  grid mostly points sonar at empty water above/ahead and still can't skip driving over the
  area. 2D grids are ONLY justified when the volume AROUND the vehicle is the target
  (obstacle-avoidance "sonar camera" / Sonair class) — that needs a full M×N grid, not a
  cross of two lines (a cross gives only two orthogonal slices, not a filled volume).
- 360° fan requires rotation (mechanical failure point + blind sweep gaps between rotations)
  OR a 2D array. A 150° FRONT fan is static solid-state, instant update, simpler. ROV turns
  its body to look elsewhere (like a car's front lidar).
- Short range (5 m) allows high frequency (400 kHz+) → cm-scale resolution. Do NOT over-spec
  range "just in case" — it forces lower freq / worse res.
- PITFALL — surface GPS does NOT track a submerged moving ROV. GPS sits at the tether top
  (fixed on the surface); the ROV is 100 m below and swims off-vertical. Relaying GPS down
  your own tether only tells you the tether-entry point, not the ROV. For pose use
  ICP/overlap self-registration (ROV-relative, no coords) or DVL / USBL.
- Stitching options, ranked by leanness:
  1. ICP / overlap self-registration — clouds register to each other by overlap. Leanest,
     ROV-relative, NO extra sensor. Proves the concept. No geo-coords.
  2. DVL (Doppler Velocity Log) — self-contained metric trajectory via bottom-relative
     velocity. $2k–10k. Add for precision/geo-placement.
  3. USBL — surface beacon + ROV responder; range (two-way travel time) + bearing (arrival
     angle across a surface hydrophone array) → ROV position vs beacon. Buildable DIY as a
     PHASE-2 (second timing domain; surface needs its own beacon + ≥2–3 hydrophones).
  4. Visual-inertial SLAM (ROV camera) — heavy compute, fragile in murk (cam sees 1–2 m).
  5. IMU-only dead reckoning — drifts meters in seconds. Single short scan only.
- Compute split: FPGA/MCU front-end does TX timing + RX beam forming (outputs
  angle/range per ping at ~100 Hz); Pi 5 / Orin only logs + overlays. Pi 5 is enough IF the
  front-end beam-forms; Orin only if you add onboard AI/SLAM.
- Independent tether + own battery (6S LiPo ~22.2 V + buck) beats tapping the ROV's
  proprietary MCP/bus. Keeps the pod a self-contained instrument.
- Operator "movie scan" overlay = SOFTWARE coverage fill (fog-of-war reveal from real
  returns), NOT a physical laser sweep (lasers die in murk). Optional cosmetic laser-line
  footprint marker in clear water only.

## Build sequence (proven lean path)
1. 4-element proof of beam steering → scale to 32-element linear array.
2. Scanner + ICP stitch → proves 3D imaging cheap, ROV-relative.
3. Add DVL or DIY USBL responder for geo-placement (phase 2; do NOT couple into v1).

## Resolution math (sizing)
- Across-track: angular res ≈ fan°/N elements. 32 elem @ 150° → ~4.7°/beam → at 5 m,
  footprint ≈ 5 × tan(4.7°) ≈ 0.41 m cells. 64 elem → ~0.2 m.
- Along-track: ping_rate × speed. 100 Hz @ 0.5 m/s → new slice every 5 mm (downsample).

## References
- references/sonar-theory.md — SBES/MBES beam-forming, ranging, correction chain, full detail.
- references/rov-stitching-usbl.md — pose/stitching options + USBL mechanism, DIY scope.
