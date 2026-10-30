#!/usr/bin/env python3
"""Convert a DJI drone telemetry SRT to the JSON the LUNASCAN SFM module needs.

DJI embeds GPS in bracket-key notation inside the SRT subtitle text:
    [latitude: 2.957820] [longitude: 101.756079] [altitude: 29.100000]

LUNASCAN's ingest parse_telemetry handles CSV SRT, but the SFM load_telemetry
wants JSON {ts, lat, lon, alt}. This script bridges the gap.

Usage:
    .venv/bin/python scripts/dji-srt-to-json.py DJI_0703.SRT telemetry.json [--fps 30]

Writes JSON plus a CSV sidecar (ts,lat,lon,alt) for ingest's parse_telemetry.
"""
import argparse
import csv
import json
import re
import sys

PATTERN = re.compile(
    r"\[latitude:\s*([\d.]+)\]\s*"
    r"\[longitude:\s*([\d.]+)\]\s*"
    r"\[altitude:\s*([\d.]+)\]"
)


def convert(srt_path: str, fps: float = 30.0) -> list[dict]:
    with open(srt_path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    records = []
    for i, m in enumerate(PATTERN.finditer(text)):
        lat, lon, alt = float(m.group(1)), float(m.group(2)), float(m.group(3))
        records.append({"ts": i / fps, "lat": lat, "lon": lon, "alt": alt})
    return records


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="DJI SRT → LUNASCAN telemetry JSON")
    ap.add_argument("srt")
    ap.add_argument("out")
    ap.add_argument("--fps", type=float, default=30.0, help="assumed capture fps (default 30)")
    args = ap.parse_args(argv)

    recs = convert(args.srt, args.fps)
    if not recs:
        print(f"WARNING: no GPS records parsed from {args.srt}", file=sys.stderr)
        return 1

    with open(args.out, "w") as f:
        json.dump(recs, f)

    csv_path = args.out.rsplit(".", 1)[0] + ".csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ts", "lat", "lon", "alt"])
        for r in recs:
            w.writerow([r["ts"], r["lat"], r["lon"], r["alt"]])

    print(f"Parsed {len(recs)} GPS points → {args.out} (+ {csv_path})")
    print(f"  lat {recs[0]['lat']:.6f}..{recs[-1]['lat']:.6f}  "
          f"lon {recs[0]['lon']:.6f}..{recs[-1]['lon']:.6f}  "
          f"alt {recs[0]['alt']:.1f}..{recs[-1]['alt']:.1f}m")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
