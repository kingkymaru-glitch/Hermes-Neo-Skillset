# LUNASCAN Drone Input Format

DJI drones produce two files per sortie that feed into LUNASCAN:

## Input files
- **`.mov` / `.mp4`** — 4K video (walk-orbit of the asset being inspected)
- **`.srt`** — SubRip subtitle file containing GPS telemetry (lat/lon/alt per frame, embedded as subtitle text lines within the `.srt` format)

## Pipeline invocation

```bash
.venv/bin/python -m lunascan.pipeline \
  --video DJI_0123.MOV \
  --telemetry DJI_0123.SRT \
  --output-dir ./output/
```

## Key user-facing clarification

LUNASCAN is a **standalone CLI** that runs on the inspector's Apple Silicon Mac. There is NO "upload video" UI in the LunaV dashboard. The dashboard only imports the finished `.glb` that LUNASCAN has already produced and uploaded to R2 (via the `+Import from LUNASCAN` button).

The full end-to-end flow:
1. Fly drone → collect `.MOV` + `.SRT`
2. Transfer to Mac → run LUNASCAN CLI
3. LUNASCAN produces `.glb` + `manifest.json`
4. Upload to R2 (manual or `--r2-upload` flag)
5. LunaV dashboard → `+Import from LUNASCAN` → model appears in viewer