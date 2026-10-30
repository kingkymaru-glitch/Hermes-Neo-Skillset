# Sonar Theory — SBES / MBES detail (from LUNASCAN-SONAR discovery, 2026-08-11)

## Ranging equation
D = (c × t) / 2
- D depth, c speed of sound in water (~1500 m/s), t two-way travel time.
- c varies with T (temp), S (salinity), Z (depth). Use SVP probe; integrate c(z) for ray
  bending. UNESCO/Mackenzie 1981 empirical formula in full form.

## Single-Beam Echo Sounder (SBES)
- One transducer straight down → one depth line under boat.
- Cheap ($hundreds). Accuracy ~±0.1–0.3 m. Coverage = only track line; gaps interpolated.
- Transducer freq: 200 kHz shallow (<100 m, narrow beam, high res) or 33/50 kHz deep.
- Beamwidth ~10–20°; seabed footprint ≈ depth × tan(bw/2) × 2. Averages fine detail.
- Open-source build: Neumi/open_echo (github) — Arduino-compatible, ~25€ 200 kHz transducer.

## Multibeam (MBES) — how one ping → surface profile
- Transmit array = row of elements. Delay firing across elements → steer fan (beam steering).
- Receive: digital beam forming (delay-and-add) isolates echo per steering angle → many beams.
- Per beam at angle θ: slant_range = (c × t)/2; across_track = slant_range × sin(θ);
  depth = slant_range × cos(θ). Subtract draft, apply heave + tide → datum.
- One ping = one cross-track PROFILE (a slice). Boat motion stacks slices → swath → point
  cloud → grid/triangulate → seafloor surface.
- Swath width ≈ depth × 2 × tan(half_fan_angle). 150° fan @ 100 m → several hundred m.
- Corrections beyond SBES: roll (±0.01°), pitch, heading, sound-speed ray tracing (outer
  beams discarded 20–30% for clean data).

## Why linear not 2D grid (for traverse mapping)
- Target is 2D seabed below; motion supplies along-track. Linear array steers across-track
  only = minimum geometry. 2D grid points at empty water, can't skip traversing.

## Cost reality
- "Expensive" = commercial MBES ($40k–200k) + survey vessel. Remove by: public GEBCO grid
  (wide context, $0) + Open-Echo DIY (site validation, $tens). Proves loop cheap.

## Post-processing
- Sounding filter: median / 3σ reject (fish, bubbles, double-bottom).
- Gridding: IDW, kriging (best, gives uncertainty), TIN (what Cesium terrain uses).
- Output XYZ → Cesium quantized-mesh terrain under LUNAV/R-Tessera 3D tiles.
