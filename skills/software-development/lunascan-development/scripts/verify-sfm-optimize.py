#!/usr/bin/env python3
"""Ad-hoc verifier for LUNASCAN Batch 3 SFM feature-extraction optimization.

Run from the repo root with .venv/bin/python:
    .venv/bin/python scripts/verify-sfm-optimize.py

Asserts (Pitfalls 12 / 18 / 19):
  - run_feature_extraction omits --SiftExtraction.first_octave (no 2x upsample)
  - --nfeatures CLI flag is wired through to the COLMAP command (not hardcoded 16000)
  - per-call nfeatures override works
  - _run() default timeout is 7200 (2h) so real 4K datasets don't abort
  - SFM test suite still passes
"""
import subprocess
import sys
import tempfile
from pathlib import Path

# Resolve repo root by walking up from cwd looking for the "lunascan" package.
# Run it from the LUNASCAN repo root (or copy next to it); not from the skill dir.
def _find_repo() -> Path:
    cur = Path.cwd().resolve()
    for p in [cur, *cur.parents]:
        if (p / "lunascan" / "sfm" / "pipeline.py").is_file():
            return p
    return cur  # will fail import clearly if not in a repo

REPO = _find_repo()
sys.path.insert(0, str(REPO))
errs = []


def check(cond, ok_msg, err_msg):
    if cond:
        print(f"OK {ok_msg}")
    else:
        print(f"FAIL {err_msg}")
        errs.append(err_msg)


# 1. Source-level assertions
src = (REPO / "lunascan/sfm/pipeline.py").read_text()
check("--SiftExtraction.first_octave" not in src,
      "first_octave removed from feature_extractor", "first_octave still present")
check("max_feat = nfeatures if nfeatures is not None else self._nfeatures" in src,
      "nfeatures wired into cmd", "nfeatures not wired")
check("timeout: int | None = 7200" in src,
      "timeout default 7200 (2h)", "timeout not 7200")
check("nfeatures: int = 4000," in src,
      "constructor accepts nfeatures param", "constructor missing nfeatures param")

cli = (REPO / "lunascan/sfm/cli.py").read_text()
check("nfeatures=args.nfeatures" in cli,
      "CLI --nfeatures passed to COLMAPPipeline", "CLI not passing nfeatures")

# 2. Live cmd capture (no real COLMAP run)
import cv2
import numpy as np
from lunascan.sfm.pipeline import COLMAPPipeline

p = COLMAPPipeline(nfeatures=4096)
cap = {}
def fake_run(cmd, timeout=None):
    cap["cmd"] = cmd
    return type("P", (), {"returncode": 0, "stdout": "", "stderr": ""})()
p._run = fake_run

with tempfile.TemporaryDirectory() as td:
    dbp = Path(td) / "c.db"
    ip = Path(td) / "img"; ip.mkdir()
    cv2.imwrite(str(ip / "f.jpg"), np.zeros((32, 32, 3), np.uint8))
    p.run_feature_extraction(dbp, ip)
    cmd = cap["cmd"]
    check("--SiftExtraction.first_octave" not in cmd,
          "live cmd omits first_octave", "live cmd still has first_octave")
    idx = cmd.index("--SiftExtraction.max_num_features")
    check(cmd[idx + 1] == "4096", "live cmd uses nfeatures=4096",
          f"live max_num_features={cmd[idx+1]}")

    p2 = COLMAPPipeline(nfeatures=4000)
    p2._run = fake_run
    p2.run_feature_extraction(dbp, ip, nfeatures=8192)
    cmd2 = cap["cmd"]
    i2 = cmd2.index("--SiftExtraction.max_num_features")
    check(cmd2[i2 + 1] == "8192", "per-call nfeatures override works (8192)",
          f"override failed: {cmd2[i2+1]}")

# 3. SFM suite
r = subprocess.run([str(REPO / ".venv/bin/python"), "-m", "pytest",
                    "tests/test_sfm.py", "-q"], cwd=REPO,
                   capture_output=True, text=True, timeout=60)
check(r.returncode == 0, "SFM suite passes", f"suite rc={r.returncode}")

if errs:
    print(f"\nFAIL {len(errs)}:")
    [print(f"  {e}") for e in errs]
    sys.exit(1)
print("\nAd-hoc verification PASSED - SFM feature extraction optimized (A+B+D)")
