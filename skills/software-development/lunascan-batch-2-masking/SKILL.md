---
name: lunascan-batch-2-masking
description: LUNASCAN Batch 2 — CoreML/Neural Engine dynamic object removal (YOLO seg + binary mask generation)
---

# LUNASCAN Batch 2 — Masking (Dynamic Object Removal)

## Trigger

When implementing, debugging, or extending `lunascan/masking/` — the CoreML Neural Engine dynamic object removal module.

## Overview

This batch processes keyframes from Batch 1 and generates binary mask images:
- **0** = static ground/structures (keep for SfM)
- **255** = dynamic objects (exclude from feature matching)

Target dynamic COCO classes: person(0), car(2), motorcycle(3), bus(5), truck(7), boat(8).

## Architecture

```
lunascan/masking/
  __init__.py     # package marker
  detector.py     # YOLO wrapper, MPS backend, class filter, CoreML export
  masker.py       # detections → binary mask images (bbox fallback + seg masks)
  cli.py          # lunascan-mask CLI entry point
tests/
  test_masking.py # 14 synthetic tests (no model download needed)
```

## Dependencies

- `ultralytics>=8.3.0` (pulls torch 2.8+, torchvision 0.23+)
- `numpy`, `opencv-python` (already in requirements)

## Key Design Decisions

1. **YOLOv8n-seg** (~6 MB nano segmentation model) — auto-downloaded on first use
2. **MPS backend** — auto-detected on Apple Silicon via `torch.backends.mps.is_available()`
3. **Lazy loading** — `DynamicDetector._ensure_model()` only loads on first `detect()` call
4. **Warm-up pass** — single 64×64 inference to prime MPS command queues
5. **Bbox fallback** — if no instance masks available, fills bounding boxes as rectangles
6. **Synthetic tests only** — no model download in CI; mock detections exercise all paths

## CLI Usage

```
lunascan-mask --keyframes ./frames/ --output ./masks/ --classes person,car,truck,bus
lunascan-mask --keyframes ./frames/ --dry-run                    # config only
lunascan-mask --keyframes ./frames/ --export-coreml model.mlpackage  # CoreML export
```

## Memory-efficient batch processing

Batch 2 now processes keyframes in configurable chunks instead of loading ALL frames into memory at once. This prevents memory explosion on large keyframe sets (e.g., 700 4K frames = ~17 GB all-at-once vs ~400 MB at batch-size 16).

| batch-size | ~memory per batch (4K) | ~total memory |
|------------|------------------------|---------------|
| 4          | 100 MB                 | 100 MB        |
| 8          | 200 MB                 | 200 MB        |
| 16 (default) | 400 MB              | 400 MB        |
| 32         | 800 MB                 | 800 MB        |

**How it works:** Each batch: load N frames → YOLO detect → generate masks → `del` frames. The model stays loaded once (reused across batches). Only the current batch's frames + YOLO tensors are in memory at any time.

**CLI usage:**
```
lunascan-mask --keyframes ./frames/ --batch-size 4   # tight memory
lunascan-mask --keyframes ./frames/ --batch-size 32  # faster, more RAM
```

**Pipeline usage:**
```
lunascan-pipeline --video drone.mp4 --batch-size 8
```

Default is 16 — balances throughput and memory on 16GB Apple Silicon Macs.

## Test Commands

```bash
# Synthetic tests (no model download, no GPU needed):
.venv/bin/python -m pytest tests/test_masking.py -v

# Full suite:
.venv/bin/python -m pytest tests/ -v

# Individual:
.venv/bin/python -m pytest tests/test_masking.py::TestMaskBenchmark::test_benchmark_synthetic_100_frames -v
```

## Gotchas

- **Python 3.9**: `ultralytics` works on 3.9 (minimum 3.8). No issues so far.
- **MPS detection**: `torch.backends.mps.is_available()` returns True on Apple Silicon Macs with PyTorch 2.x.
- **First inference slow**: model download (~6 MB) + warm-up. Second run is fast.
- **CoreML export**: requires `coremltools>=7.0` (already in setup.py). Export creates `.mlpackage` directory.
- **Mask resolution**: instance masks are resized from model resolution (320-640) to frame resolution via cv2.resize with nearest-neighbor interpolation.
- **Mock fragility**: instance mask tests require Tensor-like mocks (`.cpu().numpy()` chain). Prefer bbox fallback tests for unit coverage; instance mask path is tested in integration.

## File Line Counts

| File | Lines | Purpose |
|------|-------|---------|
| detector.py | ~160 | YOLO wrapper, MPS, CoreML export |
| masker.py | ~135 | Detections → binary masks |
| cli.py | ~130 | CLI entry + benchmark |
| test_masking.py | ~210 | 14 synthetic tests |

## Downstream consumer (Batch 3 — SFM)

Batch 3 `extractor.py` consumes the mask output directly:

- **File naming**: masks must be named `<keyframe_stem>_mask.png` (e.g. `frame_000.png` → `frame_000_mask.png`). The CLI globs for `*_mask.png`.
- **Pixel contract**: 0 = static (keep), 255 = dynamic (exclude). Batch 3 checks `mask[y,x] == 255` to decide whether to drop a SIFT keypoint.
- **Alignment**: mask dimensions must match the original keyframe exactly (same W×H). The masker already does this via `cv2.resize`.
- **Filter approach**: SIFT is extracted on the *full* unmasked image first, then keypoints inside mask==255 regions are removed. This preserves features near mask boundaries that would be lost if the image were pre-blacked.