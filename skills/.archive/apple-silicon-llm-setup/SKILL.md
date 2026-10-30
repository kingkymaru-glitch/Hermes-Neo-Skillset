---
name: apple-silicon-llm-setup
description: Setup, diagnose, and fix local LLM runners on macOS / Apple Silicon (Metal, MLX, llama.cpp, Bonsai, Ollama). Covers missing Metal toolchain, runtime shader compile failures, venv/binary compatibility, and rerun-after-fix patterns.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [macOS, Apple Silicon, Metal, MLX, llama.cpp, local LLM, setup]
    related_skills: [llama-cpp, serving-llms-vllm]
---

# Apple Silicon Local LLM Setup

Setup and recover local LLM runners on macOS, with emphasis on Metal / MLX / llama.cpp stacks.

## When to use
- User asks to install/run a local LLM runner on macOS (Bonsai-demo, llama.cpp frontends, MLX-backed apps, Ollama).
- Setup fails at the MLX/Metal build stage with errors mentioning the metal compiler or shader compilation.
- User reports that `setup.sh` / installer exits non-zero after downloading models but before finishing Python/MLX pieces.
- User wants to LoRA-finetune / train an adapter on a local model (Bonsai, llama.cpp GGUF) on Apple Silicon.

## Core sequence
1. Verify hardware tier: M1/M2/M3/M4/M5, memory, macOS version.
2. Clone / prepare the project.
3. Run setup. If it completes, proceed to launch commands.
4. If it fails specifically during MLX/Metal steps, apply the Metal toolchain fix below, then rerun setup.

## Metal toolchain fix (M-series Macs)
**Symptom:** setup exits after GGUF download with:
```
The 'metal' compiler is present but cannot execute.
The Metal Toolchain component may not be installed.
```
**Cause:** macOS installs the Metal headers by default but not the on-device compiler component needed by ggml/MLX runtime shader compilation, especially on fresh machines or after OS upgrades.
**Fix:**
```bash
sudo xcodebuild -license accept
xcodebuild -runFirstLaunch
xcodebuild -downloadComponent MetalToolchain
```
Then rerun `./setup.sh` from the project root.

## Pitfalls
- **`sudo` requires a real terminal.** These three commands cannot run non-interactively from a background shell/agent because `sudo` has no TTY for the password. Route them to user-terminal execution and wait for confirmation before continuing.
- **Re-running setup is safe.** The scripts skip already-completed stages (deps, downloads, binaries), so re-running after the fix is low-risk.
- **M5-specific Metal header regressions on macOS 26.x.** If runtime later fails with `ggml_metal_library_init_from_source: error compiling source`, the workaround is `GGML_METAL_TENSOR_DISABLE=1 ./scripts/start_llama_server.sh`. This is distinct from the missing-toolchain install-time failure.

## Post-setup launch pattern (Bonsai-demo)
```bash
cd <repo>
./scripts/start_llama_server.sh
# chat UI: http://localhost:8080
```

## Tuning knobs
- `BONSAI_NGL=0` — force CPU if Metal decode is slower than expected.
- `BONSAI_CTX=N` — pin context instead of RAM-tiered default.
- `BONSAI_KV4=1` — 4-bit KV cache for long contexts on 16GB-class machines.
- `BONSAI_MMPROJ_CPU=1` — keep vision projector in system RAM to free VRAM.

## Local LLM training (LoRA) on Apple Silicon

The same Bonsai-demo rig that runs models can also TRAIN a LoRA adapter on its
base — no separate install. Verified on this Mac (M1 Pro, 16GB):

- Binaries present: `bin/mac/llama-finetune` and `bin/mac/llama-export-lora`.
- Confirmed training knobs (from `--help`):
  - `-m/--model FNAME` — frozen base (e.g. `models/ternary-gguf/27B/Ternary-Bonsai-27B-Q2_0.gguf`)
  - `-opt/--optimizer sgd|adamw`, `-lr/--learning-rate`, `-lr-min`, `-decay-epochs`, `-wd/--weight-decay`
  - `-epochs N`, `-b/--batch-size`, `-ub/--ubatch-size`, `-c/--ctx-size`
  - `--lora FNAME` — load an adapter (inference / continue training); `llama-export-lora` writes the trained adapter
- The data-input flag (standard llama.cpp: `--train-data`) MUST be confirmed via
  `./bin/mac/llama-finetune --help` before a real run — do not assume the flag name.

### LoRA base-specificity (hard constraint)
A LoRA trains on ONE base and only applies to that exact base. Ternary-Bonsai-27B
is Qwen3.6-27B in ternary — its adapter loads ONLY on Qwen3.6-27B-family builds.
It will NOT load on Llama/Mistral/etc. Pick the base once; switching base = retrain.

### The real bottleneck is the dataset, not the training
A LoRA on too little text overfits and gains nothing. For a LUNAV/ROVER-KIT
adapter the corpus must come from the actual repos + Obsidian notes
(`~/lunavsolution`, `~/VISION` or `~/ROVER-KIT`), NOT just the handful of
holographic facts. Captured memory-loop skills are seed material; the repos are
the meat. Assemble a real corpus (JSONL / text) before training.

### RAM reality on 16GB-class Macs
Training a LoRA on a 27B base on 16GB is RAM-tight and slow (base 6.7GB +
optimizer state). The 8B Bonsai variant trains far faster with the same
architecture/LoRA compat. Prefer 8B for iteration, 27B when quality demands it.

See `references/bonsai-27b.md` for the model explainer and
`references/local-llm-training-concepts.md` for LoRA-vs-MCP-vs-memory-loop.

## When NOT to use
- Intel Macs: skip MLX entirely; use llama.cpp CPU/Metal binaries only.
- Linux: use the CUDA/Vulkan/CPU build paths; this skill does not cover ROCm/CUDA specifics.
- This skill covers RUN + LoRA-TRAIN on Apple Silicon. It does not cover full
  pretraining or cloud GPU training clusters.