---
name: local-llm-runner-setup
description: "Install, monitor, and recover local LLM runner repos and wrappers (llama.cpp, MLX, vendor demos) on macOS/Linux/Windows. Covers battery-check patterns for long setup scripts, rerun strategies, and hard-stop fixes like missing Metal toolchain."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [llama.cpp, MLX, setup, macOS, Metal, installer]
    related_skills: [llama-cpp]
---

# Local LLM Runner Setup

Use this skill when the user asks to install a local LLM runner/repo — especially vendor demo wrappers around llama.cpp / MLX — and when a setup script stalls, fails, or requires a system-toolchain install.

## Trigger

- "install X demo/repo on my Mac/PC"
- Setup scripts that hang, timeout, or stop on compiler/runtime checks
- Metal toolchain, Xcode CLT, CUDA toolkit, ROCm, or Vulkan SDK missing

## Setup-script watch pattern

1. Launch the installer in a tracked background session with `notify_on_complete=true` when possible.
2. If it appears stuck:
   - Inspect the running process with `process(action='list')` / `ps aux` first.
   - If the installer still runs and is still downloading/building, re-poll with `process(action='poll')` instead of killing immediately.
3. If the installer exits non-zero:
   - Read the last lines from the captured output — failures are almost always at the very end.
   - Match against `references/installer-fixes.md` for the exact blocker and rerun command.

## Vendor demo: PrismML Bonsai-demo

Path: clone `PrismML-Eng/Bonsai-demo` then run `./setup.sh` (Linux/macOS) or `.\setup.ps1` (PowerShell).

Environment variables:
- `BONSAI_FAMILY=ternary|bonsai|all`
- `BONSAI_MODEL=27B|8B|4B|1.7B|all`
- `BONSAI_OPENWEBUI=0` / `BONSAI_CODE_INTERPRETER=0` to skip heavy extras
- `BONSAI_SKIP_GGUF=1` or `BONSAI_SKIP_MLX=1` to prune formats
- `BONSAI_CTX=0` is RAM-tiered safe default; do not pass literal `-c 0`

Known macOS hard failure:
- Symptom: `The 'metal' compiler is present but cannot execute.`
- Fix:
  ```bash
  sudo xcodebuild -license accept
  xcodebuild -runFirstLaunch
  xcodebuild -downloadComponent MetalToolchain
  ```
  Then rerun `./setup.sh`.
- Note: on Apple Silicon, `sudo` requires a real terminal for password entry; background execution cannot complete it. Surface the commands to the user and wait for explicit continue.

Iron Law — do not overinstall:
- Default machine state is a fixed constraint. Prefer minimal install unless the user opts into extras.
- On M1 Pro / 16 GB, default to running single-turn, omit Open WebUI unless requested.

## Re-run contract

- Do not silently hardcode model/family choices; confirm before changing `BONSAI_FAMILY`/`BONSAI_MODEL`.
- If the user says "let it run," only poll progress. Only cancel and switch paths on explicit user instruction.
- When recovery requires user-side sudo/terminal input, hand off exact commands and stop.

## References

- `references/installer-fixes.md` — exact error → fix mappings