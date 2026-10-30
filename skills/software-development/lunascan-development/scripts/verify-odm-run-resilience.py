#!/usr/bin/env python3
"""Verify lunascan.odm.run_odm tolerance for OpenMVS non-zero exit.

Real failure mode (2026-08-07, dataset 701): ODM's dense fusion OOMs and falls
back to tiling, logs a warning, and exits non-zero -- yet still writes
odm_texturing/odm_textured_model_geo.glb. The old run_odm aborted on
returncode != 0 BEFORE copying, so no site_model.glb was produced.

This script mocks the docker subprocess (non-zero exit, glb present) and asserts
run_odm now copies the glb and reports degraded-success instead of failing.

Run from the LUNASCAN repo root:
    .venv/bin/python /path/to/scripts/verify-odm-run-resilience.py
"""
import sys
import tempfile
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve()
for cand in (REPO.parents[3], REPO.parents[4]):
    if (cand / "lunascan" / "odm.py").exists():
        sys.path.insert(0, str(cand))
        break
else:
    sys.path.insert(0, ".")
import lunascan.odm as odm


def main() -> int:
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "out"
        out.mkdir()
        kf = Path(d) / "kf"
        kf.mkdir()
        # minimal valid JPEG so geotag stage has something
        (kf / "frame_000000.jpg").write_bytes(
            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9"
        )
        # fake the produced glb inside the ODM project dir
        proj = out / "odm" / "code" / "odm_texturing"
        proj.mkdir(parents=True)
        (proj / "odm_textured_model_geo.glb").write_bytes(b"GLBFAKE")

        class FakeProc:
            returncode = 1
            stderr = "OpenMVS ran out of memory, turning on tiling"
            stdout = ""

        with mock.patch.object(odm, "_image_present", return_value=True), \
             mock.patch.object(odm.subprocess, "run", return_value=FakeProc()):
            res = odm.run_odm(kf, out, telemetry_path=None, fast=True)

    final = out / "site_model.glb"
    ok = bool(res.get("success")) and final.is_file()
    print(f"  [{'PASS' if res.get('success') else 'FAIL'}] run_odm returns success on ODM non-zero exit")
    print(f"  [{'PASS' if final.is_file() else 'FAIL'}] site_model.glb copied from geo .glb")
    print(f"\nRESULT: {'ALL PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
