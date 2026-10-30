# Video Trimmer Architecture

## Overview

The video trimmer lets users cut unwanted footage (takeoff, landing, travel) before processing. A thumbnail strip shows evenly-spaced frames; clicking sets start/end markers. The selected frame range is passed through the entire pipeline.

## Files involved

| File | Role |
|------|------|
| `lunascan/ingest/decoder.py` | `extract_thumbnails()` — extracts 160px JPEG thumbnails at N-second intervals |
| `lunascan/ingest/decoder.py` | `trim_video()` — cuts video file (ffmpeg -c copy or PyAV re-encode) |
| `lunascan/ingest/decoder.py` | `decode_video()` now accepts `start_frame`/`end_frame` for range-limited decode |
| `lunascan/ingest/cli.py` | `--start-frame` / `--end-frame` CLI flags |
| `lunascan/pipeline.py` | `_run_ingest()` passes `start_frame`/`end_frame` to ingest CLI |
| `app/main_window.py` | Video Trimmer UI group: QScrollArea thumb strip, click handlers, trim info label, Reset Trim button |
| `app/worker.py` | `PipelineWorker` stores `start_frame`/`end_frame`, calls `trim_video()` pre-processing step, passes trimmed file to `_run_ingest` |

## Thumbnail extraction (`extract_thumbnails`)

```python
from lunascan.ingest.decoder import extract_thumbnails

thumbs = extract_thumbnails("drone.mp4", interval_sec=2.0, thumb_width=160)
# Returns list of dicts: {frame_idx, timestamp, thumb_data (JPEG bytes)}
```

- Decodes every `interval_sec * fps` frames from the video
- Resizes to 160×90 (maintaining aspect ratio), JPEG quality 60
- Real-world: 32 thumbnails from a 61s 4K 30fps video (~3-4KB each)
- Uses PyAV for hardware-accelerated decode (VideoToolbox on Apple Silicon)

## Frame range trimming in decode_video

```python
def decode_video(path, start_frame=0, end_frame=None):
    # Frames 0..start_frame-1 are decoded and skipped (counted but not yielded)
    # Frames start_frame..end_frame-1 are decoded and yielded
    # At end_frame, container closes and generator returns
```

Performance: frame skipping still decodes (no seek on h264), so a start_frame of 1800 on a 1843-frame video saves ~0 frames of processing. The real savings come from `end_frame` — it stops the decode early rather than processing the entire video.

However, this is the FALLBACK path. The primary trim mechanism is `trim_video()` below.

## Video preprocessing: `trim_video()` (actual cut)

The `trim_video()` function in `lunascan/ingest/decoder.py` attempts to cut the video file BEFORE the pipeline runs. The worker calls this as a pre-processing step.

```python
from lunascan.ingest.decoder import trim_video

result = trim_video(
    original_video, output_dir / "trimmed_original.mp4",
    start_frame=360, end_frame=2500,
)
# → If ffmpeg available: new MP4 containing only frames 360–2499
# → If ffmpeg unavailable: returns original path (worker falls back to frame-range decode)
```

**Implementation priority:**
1. ffmpeg with `-c copy` (fast, keyframe-accurate, no re-encode) — ~1s for 100 frames
2. **Fallback: returns original path** — worker switches to frame-range decode via `_run_ingest(start_frame=..., end_frame=...)`, which is fast and reliable

The ffmpeg approach with `-c copy` trims at the nearest keyframe boundary, so the output may have slightly more frames than requested. This is acceptable — the ingest keyframe selector will prune them.

**Why no PyAV fallback:** PyAV re-encoding for 4K h264 was slow (minutes), had encoder compatibility issues in the DMG sandbox (`libx264` availability varies), and produced `[Errno 22] Invalid argument` errors in PyInstaller bundles. Frame-range decode in `decode_video()` is faster, more reliable, and already proven working.

**Worker integration** (`app/worker.py`):
- Before Batch 1 (ingest), if `start_frame > 0 or end_frame is not None`, the worker:
  1. Calls `trim_video()` to attempt file-level trim
  2. If result == original video path: sets `ingest_start = self._start_frame`, `ingest_end = self._end_frame` (frame-range decode)
  3. If result is a new file: sets `video_to_process = result`, `ingest_start = 0`, `ingest_end = None`
  4. Ingest is called with `start_frame=ingest_start, end_frame=ingest_end`

## UI architecture

The `Video Trimmer` QGroupBox sits between Output Directory and Pipeline Progress in `_build_ui()`.

**Components:**
- `self._thumb_scroll` — QScrollArea (max height 110px, horizontal scroll, no vertical scroll)
- `self._thumb_container` / `self._thumb_strip` — QHBoxLayout holding QLabel widgets
- `self._thumb_labels` — list of QLabel widgets, each with a 160×90 QPixmap
- `self._trim_info` — QLabel showing current trim range (e.g. "Trim: frame 360 → 2500 (12.0s — 83.3s)")
- Reset Trim button — clears selection back to full range

**Click behavior:**
- First click → sets start marker (green border `#238636`)
- Second click → sets end marker (red border `#f85149`)
- Subsequent clicks → cycle (start/end toggle)
- `_update_trim_info()` computes timestamps assuming 30fps

**State tracking:**
- `_trim_start: int = 0` — first frame index
- `_trim_end: int | None = None` — last frame index (exclusive, None = full video)
- `_thumb_data: list[dict]` — raw thumbnail data from extract_thumbnails
- Reset clears all three

**Wiring:**
- `_pick_video()` → calls `_build_thumbnails()` after path is set
- `dropEvent()` → calls `_build_thumbnails()` on MP4/MOV drops
- `_start_pipeline()` → passes `start_frame=self._trim_start, end_frame=self._trim_end` to `PipelineWorker()`
- `_reset_all()` → calls `_clear_thumbs()`, resets `_trim_start=0`, `_trim_end=None`

**Pass-through chain (new — trim before ingest):**
```
MainWindow._trim_start/_trim_end
  → PipelineWorker(start_frame=..., end_frame=...)
    → trim_video(original, trimmed_path, start_frame, end_frame)  [pre-processing step]
    → _run_ingest(video_to_process=trimmed_path, start_frame=0, end_frame=None)
      → ingest CLI decodes trimmed file from frame 0
```

## Video timeline format for DJI drone footage

- Container: MP4 (QuickTime)
- Codec: h264 (High@L5.1 or L5.2 for 4K)
- Typical fps: 29.97 or 30
- 4K resolution: 3840×2160
- 1-minute flight at 30fps: ~1800 frames
- DJI filenames: `dji_fly_YYYYMMDD_HHMMSS_model_video.mp4`
- SRT telemetry is an optional sidecar with matching timestamp