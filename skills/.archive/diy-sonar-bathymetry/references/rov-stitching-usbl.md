# ROV Pose / Stitching / USBL (from LUNASCAN-SONAR discovery, 2026-08-11)

## The surface-GPS trap (do NOT repeat)
GPS at tether top is FIXED on the surface. ROV is 100 m below and swims off-vertical.
Relaying GPS down your own tether tells you only the tether-entry point, NOT the ROV.
Surface GPS is useless for submerged-mover pose. Dropped this idea in session.

## Stitching options (ranked by leanness)
1. ICP / overlap self-registration — clouds register to each other by overlap. ROV-relative,
   NO extra sensor, no geo-coords. Leanest; proves the concept. CHOSEN for v1.
2. DVL (Doppler Velocity Log) — bottom-relative velocity → self-contained metric trajectory.
   $2k–10k. Add later for precision / geo-placement.
3. USBL — surface beacon + ROV responder. Range = two-way travel time × c. Bearing =
   arrival-angle difference across a surface hydrophone array (≥2–3 hydrophones, known
   baseline). → ROV position vs beacon. Buildable DIY as PHASE-2.
4. Visual-inertial SLAM (ROV cam) — heavy, fragile in murk (cam sees 1–2 m). Avoid.
5. IMU-only dead reckon — drifts meters/sec. Single short scan only.

## USBL DIY feasibility (since pod already does sonar)
- ROV side: pod's array acts as responder — reuse front-end + Pi. Low added cost.
- Surface side: own beacon + ≥2–3 hydrophones logging arrival times = NEW build.
- Different timing domain than mapping fan; time-multiplex if sharing one transducer.
- Verdict: doable DIY for few-hundred $ in parts, but a distinct workstream. Phase 2 only.

## Locked LUNASCAN-SONAR spec (founder answers)
- Linear 32-elem phased array @400 kHz, 150° front fan, 5 m range.
- RPi5 + FPGA/MCU front-end (32 angle/range per ping ~100 Hz) + IMU ICM-20948.
- 6S LiPo (~22.2 V) + buck. Independent cat6e tether (NOT ROV MCP). 100 m-rated tube.
- ROV-relative photogrammetry stitch, post-dive from SD. Mount on owned FIFISH / Chinook.
- Open questions: array orientation (level vs tilt down); accept ROV-relative v1; USBL phase 2.

## Products for reference (proven designs)
- Sonair — solid-state 2D-array volumetric sonar "camera" (obstacle awareness). Inspiration.
- Blueprint Subsea SoundMetrix, Tritech Gemini 720i — rotating mechanical 360° sonar.
- Open Echo (Neumi) — open-source single-ch echosounder (front-end starting point).
