---
name: llm-local-runner-setup
description: "Discover, size for hardware, and install public local LLM runner demos on macOS/Linux/Windows. Covers GitHub repo triage, README-driven setup.sh patterns, model-family selection by RAM tier, long-running-setup handling, and hardware-specific gotchas like Metal and mac-version quirks. Use when the user asks 'install X locally', 'run this demo on my Mac', 'what can I run here', or when onboarding a quant-model repo onto developer hardware."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [LLM, local, install, setup, llama.cpp, MLX, quantization]
    related_skills: [github-keyless-discovery]
---

# Local LLM Runner Setup

Class-level skill for standing up public local LLM demo repos on real hardware. Focus: match model/runtime to the host, avoid OOM/freezes, and handle slow or interactive setup.sh flows cleanly.

## Discovery

Start with GitHub REST search for the repo, then inspect:
- `stars`, `language`, `default_branch`, `license`, `size_kb`
- `README.md` for Quick Start, model tables, env vars, and known issues
- Recent commits for regressions or hardware-specific fixes
- Issue count (`open_issues_count`); high counts usually mean “ongoing platform breakage you’ll hit too.”

For repos like `PrismML-Eng/Bonsai-demo`, README has: model family toggle, size toggle, upstream migration status, memory tables, macOS/Linux/Windows paths, “What setup.sh does,” and an Appendix FAQ with OS-version-specific breakage.

## Hardware Sizing

Always size before running setup. Capture from `system_profiler` / OS commands:
- exact chip (e.g. `Apple M1 Pro`, not “Apple Silicon”)
- RAM in GiB
- host OS + build

Pick model family/size by memory table in README. Use *peak* figures from the README’s memory table, not weights-only numbers.

Decision logic:
- README-described defaults are often aggressive. A “default 27B” on a 16 GB Mac will OOM or freeze at runtime regardless of what setup/run scripts claim.
- Yields:
  - 16 GB Mac M1 Pro/M2/M3: 8B text-only safe; 4B or 1.7B safest; 27B likely OOM even Q2_0 with KV-cache tricks.
  - 32 GB Mac: 8B excellent; 27B risky unless Q1_0/Q2_0 with small context.
  - 64 GB+ Mac: 27B ternary/1-bit OK with context cap around 8K–32K.
- On Linux with CUDA/Vulkan: 27B is feasible on 16+ GB VRAM; otherwise pick 8B/4B.
- Windows PowerShell aliases: `$env:...` instead of export.

Rule: tell the user the expected peak memory for their chosen model before running setup, not after.

## macOS Metal Gotchas

Newer repo versions frequently contain OS-version-specific Metal breaks.
- README/op-issues check: search for “Metal” + host macOS version.
- M5/A19-specific breakage: runtime Metal compile can fail; workaround is `GGML_METAL_TENSOR_DISABLE=1 ./scripts/...`. Pre-M5 chips are unaffected.
- CUDA source build can OOM during compilation: limited `-j` parallelism if VRAM < 16 GB is already handled by good build scripts; still inspect if build hangs.

## setup.sh Runtime Handling

`setup.sh` is typically:
1. Xcode CLT check
2. uv install
3. Python venv + `uv sync`
4. HuggingFace model download
5. Binary download from GitHub releases
6. MLX source build (macOS only)
7. Open WebUI install (optional)
8. Jupyter code-interpreter venv build (optional)

Signals in the running output:
- If stuck at `Downloading cmake / hf-xet / Resolving / Installing base Python dependencies`: it is slow, not hung. Do not rerun. Use `ps` to confirm background PID still alive; a single `/bin/sh ./setup.sh` process with child `uv`/`python3` activity means it’s downloading.
- If no CPU/network activity for >10 min, only then review and consider a lighter rerun.

Lighter reruns:
- Skip heaviest extras by env before restarting:
  - `BONSAI_OPENWEBUI=0 BONSAI_CODE_INTERPRETER=0 ./setup.sh`
- For repos that accept a HuggingFace token, the prompt is sometimes a blank line that doesn’t show in output; pressing Enter alone skips it. Killing setup is necessary only when already fully stuck, not merely slow.

## Runtime Flags

Key toggles exposed by env or CLI:
- `BONSAI_FAMILY`: model family, default `ternary`
- `BONSAI_MODEL`: model size, default `27B`
- `BONSAI_TOKEN`: HF read-only token; only needed for private 27B repos at time of setup
- `BONSAI_SKIP_GGUF=1`: MLX-only macOS setups, saves disk
- `BONSAI_SKIP_MLX=1`: non-macOS/Intel skip
- `BONSAI_NGL=N`: GPU layer offload override; `0` = CPU-only
- `BONSAI_CTX=N`: context override; `0` is now safe RAM-tiered default in newer scripts, not `-c 0`
- `BONSAI_KV4=1`: 4-bit KV cache experimental
- `BONSAI_SPECULATIVE=1`: Apple Silicon speculative decode still experimental
- `BONSAI_MMPROJ_CPU=1`: vision projector in system RAM for memory-constrained GPUs

CLI extras pass through in the run/start scripts.

## Execution Model

For the user’s hardware:
1. State expected RAM/VRAM usage for the recommended size before any download.
2. Use the repo’s own scripts, not custom commands, unless the scripts are genuinely broken.
3. Run setup.sh in background with notify-on-complete; do not block the user.
4. If OOM risk is real on 16 GB class with 27B, propose 8B/4B sizes rather than blindly running default.

## References

See `references/setup-pattern-observations.md` for the concrete PrismML Bonsai-demo setup behavior, README-sourced memory tables, and observed setup.sh behavior on M1 Pro / 16 GB.