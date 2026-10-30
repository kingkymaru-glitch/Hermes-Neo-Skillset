---
name: edge-ai-detection
description: Offline-first YOLO edge detection, cloud export later.
---

# Offline-First Edge AI Detection

## When to use
Building a local AI detection system (drone / IP-cam / webcam / ROV vision) that must run with NO internet at the field site, then sync to cloud later. Pattern proven in the `luna-edge` project (Mavic + Mac-YOLO + LUNAV, hydrodam demo, deep-jungle no-connectivity).

## Core architecture — four swappable layers (config selects all)
1. SOURCE (frame producer, pluggable): webcam / IP-cam (rtsp/http) / Mavic (hdmi-capture or DJI stream) / file (mp4 loop). Live and recorded are just two subclasses yielding `(frame, ts)`. The Detector cannot tell them apart — that is the whole trick.
2. DETECTOR (source-blind): YOLO; skill = weights file (`coco` / `ppe` / `crack` ...). Swap skill, not code.
3. GEO-ADAPTER (optional, per source): maps screen-space bbox → ground (Mavic telemetry lat/long / fixed cam static pose / file-replay telemetry). Kept OUT of the detector core so the detector stays pure vision.
4. SINK (pluggable): stdout / local WebSocket / local SQLite / Supabase (post-mission only).

Result: record once, re-detect later with any new skill on the same footage. One pipeline, every camera, every domain.

## Hard rule: OFFLINE-FIRST
- Everything local on the edge machine (Mac / Orin): capture + YOLO + localhost control UI + local viewer + local store. No Vercel / Supabase / cell at site.
- Cloud (LUNAV / Supabase) = POST-MISSION export only ("process at edge, sync later").
- For the field demo use a lightweight local Cesium viewer, NOT a full web-app boot.

## Gotchas (learned building luna-edge)
- CLOSED-firmware consumer drones (Mavic Air 2): do NOT fly an Orin on them (weight + closed firmware). Run YOLO on the Mac from the controller's local wifi/HDMI. Reserve Orin for OPEN platforms (ArduPilot) or ROV sonar pods.
- Model resolution: ultralytics auto-downloads `yolov8n.pt` when passed that string; custom skills are `<name>.pt` in a `skills/` dir. Resolve skill→path: check local `skills/<name>.pt` first, else alias (`coco`→`yolov8n`), else fail clearly.
- Circular imports: geo/sink modules importing `Detection` must use `..detector.base`, NOT `.base` (they ARE base.py in their own dir).
- macOS system Python is 3.9 — fine. venv + `pip install opencv-python ultralytics flask flask-sock PyYAML`.
- Detect loop: `for frame,ts in source.read(): dets = detector.infer(frame); dets=[geo.attach(d,ts) for d in dets]; [s.emit(dets) for s in sinks]`.

## References
- references/luna-edge-pattern.md — condensed four-layer code sketch + offline-first rules + verified smoke-test approach.
