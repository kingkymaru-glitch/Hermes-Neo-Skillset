# Bathymetry / SBES knowledge bank (R-Tessera seabed layer)

Condensed from founder research session 2026-08-11. Domain: hydrographic
survey + sonar + Cesium terrain. Reuse for any "add 3D seabed to the globe" ask.

## Sensor families (how each captures depth)
- SBES (single-beam): one transducer straight down, one depth line/track.
  Cheap ($hundreds–low $k), accuracy ±0.1–0.3m. Coverage = track only; gaps
  interpolated. Best for narrow channels / proof-of-concept.
- MBES (multibeam): 256–512 beam fan, swath ~4–7× depth. Industry standard for
  real 3D. Accuracy ±0.05–0.15m. Cost $10k (low-SWaP) → $200k. THE expensive
  blocker.
- Sidescan sonar: images bottom texture/objects, NOT depth. Complementary.
- ADCP: current profile, not depth. Skip for bathymetry.

## Supporting payload (every config needs)
- GNSS/GPS (RTK ~$500–2k for cm)
- IMU/INS (pitch/roll/heave)
- SVP sound-velocity probe (measures c(z); without it depth is wrong)
- Onboard compute (Raspberry Pi class enough for SBES)

## SBES core theory
Ranging: D = (c × t) / 2. c = speed of sound in water ≈ 1450–1550 m/s,
varies with temp/salinity/pressure. Mackenzie 1981 UNESCO formula gives c(T,S,Z).
~4 m/s c-error = ~0.3% depth error.

## SBES algorithm pipeline (ping → depth)
A. Transmit: short pulse or linear-FM chirp.
B. Receive: preamp + TVG (time-varied gain) compensates 1/r² spreading.
C. Bottom detection: amplitude threshold (weak) → envelope/peak → echo-integral
   shape fit (best, sub-sample cm precision).
D. Ranging: raw = (c × t)/2 using SVP-integrated c.
E. Corrections: draft (transducer below waterline), heave (IMU), tide (datum
   e.g. LAT), ray-bending (IMU pitch/roll; SBES assumes vertical, rejects tilt),
   SVP refraction (integrate c(z)).
F. Georeference: (lon, lat, depth, time) = one sounding.

## Transducer / beam
Freq 200kHz shallow (<100m, narrow beam, hi-res) or 33/50kHz deep. Beamwidth
~10–20°; footprint = depth × tan(bw/2) × 2 (e.g. 20m depth,15° → ~5m spot).
Footprint averaging smears features smaller than it.

## Post-processing (pings → surface)
- Sounding filter: median / 3σ reject outliers (fish, bubbles, double-bottom).
- Gridding: nearest-neighbor / IDW / kriging (best, gives uncertainty) / TIN
  (what Cesium terrain uses). Grid = DEM, negative = underwater.

## Accuracy budget (DIY)
σ_total = sqrt(σ_c² + σ_t² + σ_draft² + σ_heave² + σ_tide²)
Dominant DIY errors: c (no SVP), time-pick (use shape fit), heave (no IMU).
Realistic DIY SBES: ±0.1–0.3m with SVP+RTK+IMU. Survey-grade: ±0.05–0.15m.

## Cheap / DIY proof path
Open Echo (github.com/neumi/open_echo): open-source Arduino echosounder,
transducer ~25€ (200kHz, >30m water range). + $200 RTK-GNSS + small USV hull =
real depth+position for tens of $. Single-beam only, but enough to prove the
full loop: capture → XYZ → mesh → Cesium terrain.

## Why SBES is limited (logic of weakness)
One line only (interpolate between passes), footprint averaging, no across-track
slope data, survey inefficiency (tight mow-the-lawn spacing). This is exactly
why MBES exists — but SBES is enough to PROVE the loop on a USV.

## Public data sources (free)
- GEBCO_2024: global 15 arc-sec (~500m), free download.
- ETOPO1: NOAA 1 arc-min, free.
Both standard; no USV needed for wide-area context.

## Tiling → Cesium terrain
GeoTIFF → quantized-mesh tiles via cesium-terrain-builder / pyentive /
terrainpipeline. Self-host (no paid Cesium ion). Negative elevations = seabed.
