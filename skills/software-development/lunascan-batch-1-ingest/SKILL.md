---
name: lunascan-batch-1-ingest
description: LUNASCAN Batch 1 ingest pipeline — VideoToolbox decode + telemetry + keyframe selection workflow and gotchas.
---

## When to load
Working on LUNASCAN's ingest module: video decode, telemetry parsing, keyframe selection, or its CLI.

## Architecture
Four modules:
- `decoder.py` — PyAV VideoToolbox hwaccel → numpy RGB frames
- `telemetry.py` — SRT/CSV/JSON parser for GPS + attitude (KLV stub)
- `keyframe.py` — Overlap-based pruning via strided thumbnail diff
- `cli.py` — `lunascan-ingest` CLI entry

## Key interface
```
lunascan-ingest --input drone.mp4 --telemetry flight.srt --output ./frames/ --overlap 0.75 --dry-run
```

- `probe_video(path)` → dict with codec, width, height, fps, duration, nb_frames
- `decode_video(path, output_dir)` → yields (frame_np_array, pts, time_base)
- `parse_telemetry(path)` → list of TelemetryPoint (timestamp, lat, lon, alt, yaw, pitch, roll)
- `select_keyframes(frames, overlap)` → (indices, kept_frames)

## Gotchas
- System Python is 3.9.6 (not 3.14 as originally claimed). venv at `.venv/`.
- Full requirements.txt (open3d, coremltools, etc.) causes pip resolver backtracking on Py3.9 — install minimal deps for Batch 1: `av numpy opencv-python pytest`
- PyAV VideoToolbox: set `hwaccel="videotoolbox"` on macOS, fallback to software silently
- Keyframe overlap=0 is special-cased (keep all frames) because threshold formula gives max diff
- Telemetry JSON: check `isinstance(data, list)` BEFORE `data.get("type")` or list input crashes
- Test failures often due to editable install not propagating in subprocess — run pytest as `.venv/bin/python -m pytest tests/test_ingest.py -v` from LUNASCAN root
- Tests use only synthetic data (numpy random frames, temp files) — no real drone footage needed
- `cv2` import is deferred in decoder (only needed for JPEG save) to keep probe/read fast

## Deferred
- KLV (MISB 0601) parser is a stub — needs real DJI/Skydio MPEG-TS sample
- EXIF GPS from JPEG stills (pyexiv2 or PIL) not yet implemented
- No real video decode test — needs a test fixture .mp4 in repo or CI download

## Downstream consumer (Batch 3 — SFM)

Batch 3 `georef.py` loads the telemetry output as GPS/IMU priors for COLMAP sparse reconstruction:

- **Format contract**: JSON array of `{ts, lat, lon, alt, [yaw, pitch, roll]}` OR GeoJSON FeatureCollection with Point geometry.
- **Coordinate system**: WGS84 → ECEF → ENU (East-North-Up), origin at first record's LLA.
- **Prior injection**: `prior_tx/ty/tz` (ENU meters) written to COLMAP's `images` table; `prior_q*` set from yaw/pitch/roll → quaternion (or identity if no IMU).
- **Timing precision**: COLMAP doesn't use `ts` directly — priors are aligned 1:1 by array index to the sorted keyframe list. Keyframes and telemetry records must be in temporal order.

## Verification command
```bash
cd ~/Documents/LUNASCAN && .venv/bin/python -m pytest tests/test_ingest.py -v
```