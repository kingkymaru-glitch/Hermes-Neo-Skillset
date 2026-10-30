# ARRAS Setup Notes

- GitHub repo: kingkymaru-glitch/ARRAS (private)
- Obsidian note: /Users/kamarulhk/Documents/obsidian_maru_1/Projects/ARRAS.md
- Supabase project ref: lxmmxpxjercmhmiuqegq
- Feature branches:
  - arras/reservoir-tab in ss-rover-cloud (LunaV)
  - arras/fleet-dashboard in R-Tessera
- LLM target: Qwen 3.8 27B, fine-tuned on Air Selangor corpus, 4-bit quantized via MLX on Mac Mini cluster
- Data flow: edge nodes -> Supabase time-series -> AI layer (Mac Mini) -> alerts -> LunaV AI tab + R-Tessera dashboard
- Model slots: spatial_model_id for site-scale context, detail_model_id for component-scale defects
- Spatial tab selection: explicit "Set as Spatial" button in 3D Digital Twin tab model sidebar
