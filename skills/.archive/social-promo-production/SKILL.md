---
name: social-promo-production
version: 1
author: Neo
license: MIT
description: Branded promo frames; bake logo+copy with PIL compositing.
metadata:
  hermes:
    tags: [social-media, promo, video, tiktok, reels, branding, pil]
    related_skills: [creative/sketch, creative/claude-design, baoyu-infographic]
---

# Social Promo Production (fallback path: image keyframes + PIL branding + CapCut)

## When to Use
- User asks for a TikTok / Instagram Reels / short-form promo, ad, or "viral video like the trending ones" for a product, store, or brand.
- FLUX 3 / video generation is unavailable and you must fall back to still keyframes composited into a video later (CapCut).

## Trigger
- User wants a TikTok / Reels / short-form promo for a product or brand.
- "Make me a video like the trending ones", "create a promo for X", "viral ad for my store".
- Especially when FLUX 3 / video generation is unavailable and you must fall back to still keyframes.

## Workflow
1. **Research trending patterns** — pull 3-5 current signals (hook length, sound-off text, saves>likes, 9:16, trending audio). See `references/trending-shortform-2026.md`.
2. **Verify the brand/product online AND against the user's reference image.** The screenshot they attach may depict a DIFFERENT product than the one they name — flag the mismatch (e.g. screenshot showed Pirelli Angel, user said Diablo Rosso).
3. **Write a paste-ready video prompt** — hook (0-3s), body, close, audio note, 9:16, 15-20s.
4. **Generate keyframes with image_generate** (FAL FLUX 2 is the working backend; FLUX 3 video is NOT free right now — do not retry it, switch to image gen). Produce 3-4 frames: hook/spin-up, macro detail, action, static hero. Match the brand's real visual cues (e.g. Diablo Rosso has RED sidewall lettering + aggressive supersport tread; the user's studio shot used a white seamless backdrop).
5. **BRAND THE FRAMES — do not skip this.** Users expect the logo and copy IN the images. Design a wordmark with PIL and composite it (see `scripts/brand_composite.py`). Bake punchlines as text overlays. If you only hand back raw AI frames and say "overlay in CapCut", the user will come back with "there's no logo anywhere — put it on the bike." Bake it.
6. **Deliver** the tagged frames + a CapCut assembly sequence (see `templates/capcut_assembly.md`). State the model used and that branding was composited, not AI-rendered.

## Key technique: branding via PIL (never trust the model for text)
AI image models mangle brand names, logos, and copy. The reliable path:
- Build a transparent wordmark in PIL (black word + accent-colored second word + small icon), using Arial Black (`/System/Library/Fonts/Supplemental/Arial Black.ttf`) or SF Compact Bold (`/Library/Fonts/SF-Compact-Display-Bold.otf`) — both present on macOS.
- `paste()` with a soft drop shadow for legibility over busy frames.
- `bake_text()` centered; **MEASURE `textlength` with the chosen font vs frame width BEFORE baking** and shrink the font until it fits with margin. Text wider than the frame is silently clipped (learned the hard way: "YOUR TYRES ARE" at 0.058*H measured 1166px vs 1152 frame → clipped; shrank to 0.050*H → 1008px, fit).

## Pitfalls
- **Text clipping**: always measure; center-aligned text spills both edges if over-width.
- **Vision endpoint is flaky** (404 / timeout / connection errors). Verify branding by measuring text width programmatically, not by depending on vision_analyze.
- **Logo "on the bike" is a composite decal, not factory paint.** For authentic brand placement, composite the wordmark onto a REAL product photo the user supplies, rather than AI art.
- **Video backend down → image fallback**: FLUX 3 free period ended; image_generate (FAL) still works. Don't burn budget retrying video.
- **Branding text not baked in**: the #1 reason a user rejects the output. Bake logo + punchline; treat CapCut as the motion/audio layer, not the place branding first appears.

## Deliverables checklist
- [ ] 3-4 tagged PNG keyframes on Desktop (or requested path)
- [ ] transparent wordmark PNG (reusable)
- [ ] the build script (re-runnable for tweaks)
- [ ] CapCut assembly sequence

## Support files
- `references/trending-shortform-2026.md` — condensed trending patterns + hook line bank.
- `scripts/brand_composite.py` — reusable PIL compositor (wordmark + punchlines onto frames).
- `templates/capcut_assembly.md` — tap-by-tap CapCut edit for a 4-frame 9:16 promo.
