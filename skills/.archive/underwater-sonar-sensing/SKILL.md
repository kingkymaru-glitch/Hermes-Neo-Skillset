---
name: underwater-sonar-sensing
description: Low-cost sonar/bathymetry + ROV sensing for Cesium/LUNAV.
---

# Underwater Sonar Sensing (low-cost build)

Use when MARU explores or builds cheap 3D bathymetry / ROV sonar sensing to feed LUNAV or R-Tessera (Cesium terrain). Project context: prove 3D bathymetry can be done cheap — public GEBCO/ETOPO1 grid for wide-area context + DIY USV/ROV sonar for site-specific validation, instead of a $50k commercial MBES + survey vessel.

## When to load
- User mentions bathymetry, seabed mapping, echo sounder, SBES, MBES, multibeam, sidescan, ADCP.
- User wants USV/ROV-mounted sensors to capture depth/data at a site.
- User compares single-beam vs multibeam, or asks about array geometry (line vs 2D grid, rotating vs solid-state, 360 vs front-facing).
- User wants captured sonar data rendered as 3D in Cesium/LUNAV.

## Core theory (condensed — full math in references/bathymetry_sonar_knowledge.md)
- Ranging: D = (c × t) / 2. c = speed of sound in water (1450–1550 m/s), varies with temp/salinity/pressure. MEASURE with sound-velocity probe; never assume.
- SBES: one downward beam → one depth per ping. Cheap, line-only coverage, ±0.1–0.3 m with SVP+RTK+IMU.
- MBES: linear transducer array, steered fan via per-element delay-and-sum (digital beam forming) → hundreds of beams/ping → one cross-track profile per ping; vehicle motion → overlapping swaths → dense point cloud → surface.
- Per-beam: slant_range → across_track = slant×sin(angle), depth = slant×cos(angle). Corrections: draft, heave (IMU), tide, sound-speed refraction (ray trace c(z)), roll/pitch/heading.

## Key design decisions & pitfalls (from discovery session)
1. LINEAR ARRAY is correct for downward mapping + motion. A 2D grid (elements in BOTH vertical and horizontal) is ONLY needed if the vehicle must capture 3D while STATIONARY (hovering). A "cross" of two lines = two orthogonal SLICES, not a filled volume — full M×N grid needed for stationary volumetric sensing.
2. 360° rotating sonar = "sonar lidar" class (Blueprint SoundMetrix, Tritech Gemini, Imagenex). For an ROV that TRAVERSES, a 150° FRONT-FACING static fan + motion = 3D with NO rotation, no servo, no blind-sweep gap. Prefer this — simpler/cheaper.
3. SEMICIRCLE ARRAY + ROTATION blind spot: a bent LINE of elements rotating yields a cylindrical SHELL (constant-range surface), not filled volume. Filled volume needs a 2D curved array with elevation steering. Don't under-build.
4. "Stereo like humans" is the WRONG metaphor. Sonar gets range per beam via time-of-flight (one transducer suffices); it is omnidirectional awareness, not two-eye parallax. Don't design around stereo.
5. 5m RANGE constraint is a gift: enables high frequency (400kHz–1MHz) → cm-scale resolution; round-trip ~6.7ms → 100+ Hz ping rate → near-continuous update, kills blind-sweep.
6. COVERAGE OVERLAY must be SOFTWARE (translucent scanned-polygon fill in Cesium/LUNAV, driven by real point cloud — "fog-of-war" reveal). Physical laser swipe fails in murky water (why you use sonar, not light). Optional: visible laser-line footprint marker for clear-water cosmetic feedback only.
7. HARDWARE lean spec (5m / 150° front / traverse): 32-element linear array @400kHz; beam forming on FPGA/MCU front-end (NOT main board); Raspberry Pi 5 as supervisor (log + overlay + stream); IMU (ICM-20948-class) for roll/pitch/heading geo-registration; 1080p wide cam (4K overkill, only for inspection archive); TETHER for power+data+video (wireless underwater = low-bandwidth acoustic, avoid); pressure-rated enclosure to target depth. Jetson Orin Nano only if adding onboard AI/SLAM or raw-array processing.
8. GEO-LOCATION underwater: GPS doesn't work. Options: USBL acoustic positioning, surface GPS relayed via tether, or ROV-relative map (no global coords). Decides if Cesium layer is geo-anchored or vehicle-relative.
9. DIY array reality: scaling Neumi/open_echo (single-channel, ~25€ transducer) to a 32-ch line is the project. Each channel needs pulser (TX) + LNA+ADC (RX) + delay line. Off-the-shelf 32-ch arrays pricey/specialist.

## Build pipeline (sonar → Cesium)
USV/ROV captures (depth + position + attitude) → post-process to XYZ point cloud → outlier reject (median/3σ) → grid (IDW/kriging) or TIN → Cesium quantized-mesh terrain → loads under LUNAV/R-Tessera 3D tiles. Same pipeline as public GEBCO grid path, just own data. Coverage overlay = translucent scanned-region polygon in operator HUD/map.

## Unresolved spec questions (confirm with user before build)
- Linear (traverse) confirmed, or need hover-3D (2D grid)?
- Tether or wireless?
- Geo-anchored (USBL/surface GPS) or ROV-relative map?
- Target depth rating?
- DIY array build (cheap, slow) or buy module (fast, costly)?

## References
- references/bathymetry_sonar_knowledge.md — full theory distillation (SBES/MBES math, array geometry, 360 sonar products, resolution math, grazing-angle problem).
