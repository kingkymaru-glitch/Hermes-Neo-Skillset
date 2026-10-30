# Local LLM training concepts (LoRA / MCP / memory loop)

Three DISTINCT layers — often confused. They stack; they are not the same thing.

## 1. LoRA = changes WEIGHTS (training-time)
- Low-Rank Adaptation: freeze base, train tiny A×B matrices (rank r). Adapter = few hundred MB.
- Base-specific: trains on ONE base, loads ONLY on that base. Not portable across models.
- Reversible (delete adapter → original), but "wrong" knowledge needs retraining to remove.
- On Mac: Bonsai-demo `llama-finetune` + `llama-export-lora`. See SKILL.md section.

## 2. MCP = runtime TOOLS (no weight change)
- Model Context Protocol: connects model to external tools/data (DBs, APIs, functions).
- Model-agnostic: any model speaking the protocol uses the same server.
- The model's brain is unchanged; it gains the ability to call out.

## 3. Memory loop (our fact_store / gap_analyze) = inference-time DATA
- Knowledge injected into context each turn; user "useful/wrong" signals adjust trust.
- No weight change, harness-agnostic, fully reversible.
- The garrytan/gbrain work built THIS — it is NOT a LoRA; it touches zero weights.

## How they relate
- LoRA improves knowledge/style/reasoning INSIDE the model (offline, no prompt padding).
- MCP improves what the model can DO via external systems.
- Memory loop improves what the model knows per-turn via injected data.
- The memory loop FEEDS a LoRA: captured skills + facts = the training corpus. Compounding both directions.

## Why train at all (vs just the loop)?
- Offline edge reasoning (ROVER-KIT substation box that reasons with no cloud/prompt).
- Founder voice baked into weights.
- Less token overhead (knowledge in weights = shorter prompts).
- Stick with the loop when you want easy correction ("wrong" demotes a fact instantly).
