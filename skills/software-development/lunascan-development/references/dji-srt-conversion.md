# DJI SRT Telemetry Conversion

DJI drones (Mavic, Air, Mini series) embed GPS telemetry in SRT subtitle sidecar files. The format uses HTML `<font>` tags with bracket-delimited key-value pairs.

## SRT Format

```
1
00:00:00,000 --> 00:00:00,033
<font size="36">SrtCnt : 1, DiffTime : 33ms
2026-08-05 16:52:54,192,906
[iso : 100] [shutter : 1/1000.0] [fnum : 280] [ev : 0] [ct : 5600] [color_md : default] [focal_len : 240] [latitude: 2.957820] [longitude: 101.756079] [altitude: 29.100000] </font>
```

Key fields: `latitude`, `longitude`, `altitude`. Also present: `iso`, `shutter`, `fnum`, `ev`, `ct`, `color_md`, `focal_len`.

## Conversion Script

Save as `convert_dji_srt.py` and run before the pipeline:

```python
#!/usr/bin/env python3
"""Convert DJI SRT telemetry to LUNASCAN-compatible JSON."""
import re, json, sys
from pathlib import Path

def convert(srt_path: str, out_path: str, fps: float = 30.0):
    text = Path(srt_path).read_text(errors="replace")
    pattern = re.compile(
        r'\[latitude:\s*([\d.]+)\]\s*\[longitude:\s*([\d.]+)\]\s*\[altitude:\s*([\d.]+)\]'
    )
    records = []
    for match in pattern.finditer(text):
        lat, lon, alt = float(match.group(1)), float(match.group(2)), float(match.group(3))
        records.append({"ts": len(records) / fps, "lat": lat, "lon": lon, "alt": alt})

    with open(out_path, "w") as f:
        json.dump(records, f)

    print(f"Converted {len(records)} GPS points → {out_path}")
    if records:
        print(f"  Lat: {min(r['lat'] for r in records):.6f} – {max(r['lat'] for r in records):.6f}")
        print(f"  Lon: {min(r['lon'] for r in records):.6f} – {max(r['lon'] for r in records):.6f}")
        print(f"  Alt: {min(r['alt'] for r in records):.1f}m – {max(r['alt'] for r in records):.1f}m")

if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])
```

## Usage

```bash
python3 convert_dji_srt.py DJI_0703.SRT telemetry.json
lunascan-pipeline --video video.mp4 --telemetry telemetry.json ...
```

## Why This Matters

The pipeline's `--telemetry` flag passes directly to SFM's `load_telemetry()`, which only handles JSON. The ingest module's `parse_telemetry()` handles CSV-format SRT but NOT DJI's bracket-key-value format. Without conversion, the pipeline silently gets zero telemetry records — COLMAP gets no GPS priors, and the sparse cloud lacks georeferencing.

## Real-world Data

Tested on DJI Mavic 3 footage (2026-08-06):
- 61-second 4K video → 1,842 SRT entries
- Lat range: 2.9571 – 2.9585 (~150m)
- Lon range: 101.7558 – 101.7571 (~150m)
- Alt range: 29.0m – 50.1m (drone ascending during flight)