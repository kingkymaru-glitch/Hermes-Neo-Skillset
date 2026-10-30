# Bonsai 27B — model explainer (verified + whitepaper)

## What it is
- Bonsai 27B = Qwen3.6-27B compressed to sub-4-bit weights. NOT a new architecture; a compression method applied to an existing 27B.
- Ternary: weights ∈ {-1, 0, +1} + small FP16 group scaling → ~1.7 bits/weight → 5.9–6.7 GB.
- 1-bit: weights ∈ {-1, +1} → ~1.125 bits/weight → 3.9 GB (fits iPhone 17 Pro Max).
- Whitepaper claims retain 27B-class thinking/reasoning/agentic: 95% of FP16 at ternary (avg 80.49/85.07), 90% at 1-bit (76.11). Conventional low-bit (IQ2_XXS) loses reasoning/tool-calling below 4-bit.

## Why 27B runs on a 16GB Mac
1. Footprint: 6.7GB ternary fits in 16GB with headroom for OS + KV + activations.
2. Memory-bandwidth-bound decode: smaller weights = less data moved per token = faster. Ternary moves ~3x fewer bytes/token than Q4.
3. Hybrid attention: Qwen3.6-27B is ~75% linear attention → KV cache stays small → 256K-token context feasible on-device. KV at FP16 ~64 KiB/token (6.3GB @100K); demo defaults RAM-tiered context (8K–131K) to avoid OOM.
4. Metal GPU offload via BONSAI_NGL (default all layers on Metal).

## On this Mac (verified)
- Apple M1 Pro, 16GB, arm64.
- Weights already downloaded: `models/ternary-gguf/27B/Ternary-Bonsai-27B-Q2_0.gguf` (6.7GB) + mmproj x2 + dspark drafter. Total ~10GB.
- Compiled `bin/mac/llama` with Metal backend present.
- Vision: mmproj enables image/PDF input. Native tool_calls + thinking (reasoning_content).
- BONSAI_TOKEN not needed to run what's already on disk (needed only to re-download; 27B repos currently private).

## Launch
```bash
cd ~/Bonsai-demo
./scripts/start_llama_server.sh   # chat+vision+tools at http://localhost:8080
# or one-shot:
./scripts/run_llama.sh -p "Hello!"
```
Tuning: BONSAI_NGL=0 (CPU if Metal slow), BONSAI_CTX=N, BONSAI_KV4=1 (long ctx), BONSAI_MMPROJ_CPU=1 (free VRAM).

## Caveats
- 27B on 16GB is RAM-tight; expect slower than whitepaper's 26 tok/s.
- 8B/4B Bonsai variants fit far more comfortably — use for iteration.

## Relationship to LoRA (see local-llm-training-concepts.md)
Bonsai 27B can be LoRA-trained on domain text (LUNAV/ROVER-KIT) — the finetune
binary is in the same rig. Adapter is base-specific (Qwen3.6-27B only).
