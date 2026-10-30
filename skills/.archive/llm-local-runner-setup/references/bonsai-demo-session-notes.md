# PrismML-Eng/Bonsai-demo Session Notes

Sourced from README + live setup run on M1 Pro, 2026-07-29.

Repo
- full_name: PrismML-Eng/Bonsai-demo
- license: Apache-2.0
- topics: bonsai, llamacpp, llm, mlx, prism-ml, small-models
- default branch: main

## Model Memory Targets (README peak, 27B)

| Model          | Format           | Weights | 4K  | 10K | 100K |
|----------------|------------------|--------|-----|-----|------|
| Bonsai-27B 1-bit| GGUF Q1_0        | 3.53 GiB | 4.8 GiB | 5.2 GiB | 10.8 GiB |
| Bonsai-27B 1-bit| MLX 1-bit        | 3.92 GiB | 5.5 GiB | 5.9 GiB | 11.4 GiB |
| Ternary-27B    | GGUF Q2_0        | 6.66 GiB | 7.8 GiB | 8.1 GiB | 13.7 GiB |
| Ternary-27B    | MLX 2-bit        | 7.05 GiB | 8.6 GiB | 8.9 GiB | 14.4 GiB |
| Bonsai-8B      | all              | smaller | ~2.5 GiB at 8K | | ~10.5 GiB at 65K |

For 16 GB Mac M1 Pro, 27B 1-bit MLX at small context is plausible; ternary 27B is risky.

## setup.sh Steps

1. Xcode CLT
2. uv install
3. `.venv` + `uv sync`
4. HF model download
5. llama.cpp prebuilt binaries download from PrismML-Eng/llama.cpp release
6. MLX fork build (macOS)
7. Open WebUI (`BONSAI_OPENWEBUI=0` skips)
8. Jupyter venv (`.venv-jupyter`, `BONSAI_CODE_INTERPRETER=0` skips)

## setup.sh Observed Behavior

- Interactive prompt for BONSAI_TOKEN may appear as a blank line without visible prompt.
- Steps 3+ can be very slow; single `/bin/sh ./setup.sh` PID with child `uv` downloading means healthy, not hung.
- Last observed stuck point: `Downloading cmake (50.1MiB)` then `hf-xet`, with output silent for several minutes while downloading Python deps.

## macOS Metal Gotcha

- M5 + certain macOS 26.x point releases: `ggml_metal_library_init_from_source` fails due to strict MPP headers.
- Workaround: `GGML_METAL_TENSOR_DISABLE=1 ./scripts/run_llama.sh`
- On M1–M4, precompiled embedded library loads fine; this does not apply.
- macOS build: 26.3 on M1 Pro does not show this breakage.

## Release artifact commit

Setup reporter release bundle for llama.cpp: `prism-b9596-9fcaed7`
URL: https://github.com/PrismML-Eng/llama.cpp/releases/tag/prism-b9596-9fcaed7

## Quick Start (default 27B ternary)

```bash
cd /Users/kamarulhk/Bonsai-demo
./setup.sh
BONSAI_MODEL=27B ./scripts/start_llama_server.sh
```

Chat: http://localhost:8080
Open WebUI: `./scripts/start_openwebui.sh` -> http://localhost:9090

## Vertical Sizing Recommendation Shape

Hardware -> recommended size
- 16 GB Mac: 1.7B or 4B safe; 8B OK; 27B only if 1-bit + small context cap
- 32 GB Mac: 8B comfortable; prefer 1-bit 27B with capped (`8192–32768`) context
- 64+ GB Mac / 16+ GB VRAM Linux: 27B ternary/1-bit with 100K+ context acceptable