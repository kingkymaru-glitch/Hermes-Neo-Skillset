# Artifact catalog — worked example (multi-repo dev cleanup)

Calibration numbers from a real session across 11 repos on a dev Mac. Shows
typical size split between regenerable junk and protected assets, so you can
quote ballpark frees to the user before running.

## Repos surveyed + total size
- Bonsai-demo        13G   (10G = models/ LLM weights — PROTECTED, needs BONSAI_TOKEN to refetch)
- luna-edge          2.9G
- lunavsolution-code 736M  (node_modules 495M + .next 238M)
- ComfyUI            1.4G  (only __pycache__ ~8M regenerable; source is .py)
- web-ui             2.9M
- my-digital-twin    405M  (node_modules 387M + .vite 35M + dist 14M)
- awesome-llm-apps   3.8M
- VISION             188K
- riina              193M  (node_modules 190M + .vite 12M + dist 1.3M + .vercel)
- osiris             1.2G  (node_modules 636M + .next 592M)
- lunav-labs         494M  (node_modules 478M + dist 14M + .vercel)

## What "Lean & safe" removed (~0.9 GB) — apps stay runnable
- 51 × .DS_Store files
- ComfyUI __pycache__ (~8M)
- lunavsolution-code/.next (238M) + osiris/.next (592M)
- dist: my-digital-twin 14M + riina 1.3M + lunav-labs 14M
- .vite caches (my-digital-twin/riina/lunav-labs)
- .vercel caches (riina/lunav-labs)

## What "Full lean" adds (~2.1 GB more) — must npm install to run again
- node_modules in: lunavsolution-code, my-digital-twin, riina, osiris, lunav-labs

## What "Everything" adds (+10 GB) — high re-fetch cost
- Bonsai-demo/models (private HF weights; needs BONSAI_TOKEN). Do NOT do this
  unless the user explicitly confirms.

## Gotcha captured
- `ComfyUI/comfy/__init__.py` was MISSING after cleanup, but
  `git cat-file -e HEAD:comfy/__init__.py` → NOT IN HEAD: it was never in the
  repo. The cleanup (which only removed __pycache__) was NOT the cause.
