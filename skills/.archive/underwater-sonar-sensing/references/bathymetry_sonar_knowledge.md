# Bathymetry & Sonar Knowledge Bank (discovery session distillation)

Condensed from a MARU discovery session on building cheap 3D bathymetry + ROV sonar for LUNAV.
Companion to SKILL.md `underwater-sonar-sensing`. Not a mirror of upstream docs — just the load-bearing facts.

## SENSOR FAMILIES
- SBES (single-beam): one downward transducer, one depth/ping. $hundreds–low$k. ±0.1–0.3 m with SVP+RTK+IMU. Line coverage only.
- MBES (multibeam): fan of 256–512 beams, swath ≈ 4–7× depth. Industry standard for 3D seabed. Pro units $40k–$200k+; low-SWaP (MS400U, HydroBeam M4) still $10k+.
- Sidescan sonar: images bottom texture/objects, NOT depth. Complementary.
- ADCP: water-column current, NOT depth. Skip for bathymetry.

## RANGING MATH
- D = (c × t) / 2. c = speed of sound (1450–1550 m/s).
- UNESCO/Mackenzie 1981 c(T,S,Z):
  c = 1448.96 + 4.591T − 0.05304T² + 2.374e-4 T³ + 1.340(S−35)
      + 0.0163Z + 1.675e-7 Z² − 0.01025T(S−35) − 7.139e-13 T Z³
  T=°C, S=ppt, Z=m. 4 m/s c-error ≈ 0.3% depth error (0.3 m @100 m).
- Footprint diameter ≈ depth × tan(beamwidth/2) × 2. 20 m, 15° beam → ~5 m spot.

## SBES ALGORITHM PIPELINE
1. Transmit chirp/broadband pulse. 2. RX + TVG (time-varied gain, compensates 1/r² + absorption). 3. Bottom detect: amplitude threshold → envelope/shape-fit peak (cm precision). 4. Ranging with SVP-integrated c. 5. Corrections: draft, heave (IMU), tide→datum (LAT), ray-bending, SVP refraction. 6. Georeference → sounding (lon,lat,depth,time).
- Output formats: .all (Kongsberg), .sgy (SEG-Y), or XYZ/CSV for DIY. Open Echo → timestamped (depth,lat,lon) rows.

## MBES BEAM FORMING
- Transmit: array fires elements with microsecond delays → steered fan (one ping, not many).
- Receive: digital beam forming (delay-and-sum per steering angle) isolates each beam's echogram from the mixed return.
- Per beam: slant_range = (c×t)/2; across_track = slant×sin(θ_corr); depth = slant×cos(θ_corr); subtract draft, apply heave/tide; attach GPS+heading+time → 3D point.
- One ping = one cross-track profile (sector/pie-slice on seabed, NOT a rectangle). Boat/ROV motion stacks slices → swath → point cloud → TIN surface.
- Swath width ≈ depth × 2×tan(half_fan_angle). 100 m, 150° fan → several hundred m.

## ARRAY GEOMETRY (the key debate)
- Linear array = steers fan in ONE plane → 2D slice. Needs motion for 3rd dim. Right for mapping.
- 2D grid (M×N elements) = steers azimuth+elevation → fills 3D volume in ONE ping (stationary). Costs M×N channels (32×32=1024). Sonair-class is the real product (low-res, short-range, solid-state).
- "Cross" of two lines = two slices only, NOT volume.
- Semicircle + rotation: bent LINE rotating → cylindrical shell (constant-range surface). Needs 2D curved array w/ elevation for filled volume.
- Camera (DSLR square) analogy FAILS: light is passive 2D angular field; sonar is active round-trip where travel time = depth, can't "snapshot" a volume. Square array mostly points at empty water.

## 360 / ROTATING SONAR PRODUCTS (real)
- Rotating mechanical: Blueprint Subsea SoundMetrix (360° 3D point cloud), Tritech Gemini 720i/sk, Imagenex 852, BlueView (Teledyne). = sonar lidar. Blind between sweeps.
- Solid-state 2D array: Sonair (robotics 3D ultrasonic "sonar camera"), Kraken AquaPix, Kongsberg ME70. Instant 3D, no moving parts, expensive/rare.

## RESOLUTION MATH (5 m / 150° front spec)
- 32 elements → 150/32 ≈ 4.7°/beam → 5m×tan(4.7°) ≈ 0.41 m across-track cell.
- 64 elements → 2.3° → ~0.2 m cell.
- Along-track: ping_rate × speed. 100 Hz @ 0.5 m/s → slice every 5 mm (downsample).
- 5 m round-trip ≈ 6.7 ms → 100+ Hz achievable → near-continuous, kills blind-sweep.

## GRAZING-ANGLE PROBLEM
- Outer/far-forward beams hit seabed at shallow angle → weak echo, surface multipath, unreliable bottom detect. Surveys discard outer 20–30% of swath. Reason you can't just "look far forward" with quality — must drive over it.

## ACCURACY BUDGET
- σ_total ≈ sqrt(σ_c² + σ_t² + σ_draft² + σ_heave² + σ_tide²).
- DIY dominant errors: c (no SVP), time-pick (use shape-fit), heave (no IMU → calm water + slow).
- Realistic DIY SBES: ±0.1–0.3 m. Survey-grade: ±0.05–0.15 m.

## LUNAV / CESIUM INTEGRATION
- Point cloud (lon,lat,depth) → grid/TIN → Cesium quantized-mesh terrain (self-host, no paid ion). Loads under existing 3D tiles.
- Coverage overlay: translucent scanned-polygon fill in operator HUD/map, fed by real returns (fog-of-war). Optional physical laser-line footprint marker (clear water only).
- Same pipeline as public GEBCO_2024 / ETOPO1 grid path — own data instead of public grid.

## OPEN-SOURCE / DIY REFS
- github.com/Neumi/open_echo — open-source Arduino-compatible echosounder, ~25€ 200kHz transducer (>30 m water range). Single-channel starting point.
- Public grids: GEBCO_2024 (15 arc-sec ~500 m), ETOPO1 (1 arc-min, NOAA) — free, no USV needed for context.
- Cesium terrain build: cesium-terrain-builder / pyentive / terrainpipeline (quantized-mesh).
