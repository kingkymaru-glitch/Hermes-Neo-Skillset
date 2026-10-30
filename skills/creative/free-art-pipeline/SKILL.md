---
name: free-art-pipeline
description: "Free art generation, no paid APIs."
version: 1.0.0
author: Neo
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [art, image, generation, free, pipeline]
---

# Free Art Pipeline

Generate visual content without paid APIs. Uses free/local tools only.

## When to Use

- Generate images from text prompts
- Create generative art
- Produce visual content for marketing, social media, or presentations
- Create diagrams, illustrations, or concept art

## Free Tools Available

### 1. ComfyUI (Local, Unlimited)
- Local Stable Diffusion server
- Free, unlimited generations
- Requires: ComfyUI running locally
- Best for: Photorealistic images, concept art, illustrations

### 2. fal (Free Tier)
- Cloud image generation API
- Free tier with rate limits
- Requires: FAL_API_KEY
- Best for: Quick generations without local setup

### 3. p5js (Code-Based, Free)
- Generative art via JavaScript
- No API key required
- Best for: Abstract art, patterns, data visualization

### 4. ASCII Art (Terminal, Free)
- Text-based art via terminal
- No dependencies
- Best for: Quick visuals, terminal demos, retro aesthetics

### 5. SVG Generation (Code, Free)
- Vector graphics via code
- No dependencies
- Best for: Diagrams, icons, logos, scalable art

## Pipeline

### Text-to-Image (Photorealistic)
1. Use ComfyUI if running locally
2. Fall back to fal free tier
3. Fall back to p5js generative art

### Generative Art (Abstract)
1. Use p5js for algorithmic art
2. Use SVG for vector-based art
3. Use ASCII art for terminal output

### Diagrams & Visualizations
1. Use SVG for scalable diagrams
2. Use p5js for interactive visualizations
3. Use Mermaid for flowcharts

## Examples

```bash
# ComfyUI (local)
curl -X POST http://localhost:8188/prompt -d '{"prompt": "a futuristic city"}'

# fal (free tier)
curl -X POST https://api.fal.run/fal-ai/flux/dev -H "Authorization: Key $FAL_API_KEY" -d '{"prompt": "a futuristic city"}'

# p5js (generative art)
# Write a p5.js sketch and run in browser

# SVG (vector art)
# Generate SVG markup directly
```

## Security

- Never print or log API keys
- Sanitize all user prompts before sending to APIs
- Respect rate limits on free tiers
- Prefer local tools when available

## Notes

- ComfyUI is the best option for unlimited free generation
- fal free tier is good for occasional use
- p5js and SVG are always free with no limits
- ASCII art is great for quick terminal visuals
