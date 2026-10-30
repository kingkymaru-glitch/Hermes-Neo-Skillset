---
name: vision-tool-down-workaround
description: "Vision tools 404? Verify visually without seeing the image."
version: 1.0.0
author: Hermes Agent
license: MIT
---

## When this applies
- `vision_analyze(image_url=...)` or `browser_vision(...)` returns `HTTP 404`.
- You get a screenshot path but cannot load it into context.
- Any task depending on *looking at* a rendered page, map, chart, or image.

## The rule (non-negotiable)
DO NOT fabricate image content. Never describe pixels you haven't seen.
State vision is down, then work around it:

### 1. Introspect the live runtime instead of pixels
- `browser_console(expression=...)` — evaluate JS in page context. Temporarily
  expose state: `if (typeof window !== 'undefined') window.__X = ...` in the
  component (DEBUG — remove after). Read counts, modes, positions.
- `browser_snapshot()` — accessibility tree; confirms controls + state without
  seeing styling.
- Cesium example: expose `window.__viewer`, count entities, read `scene.mode`
  (2=2D,3=3D), check NaN, convert a known entity's ECEF→lon/lat vs source.
  See `cesium-resium-react` G38.

### 2. Read the screenshot from disk (it IS saved)
Screenshots write to `~/.hermes/cache/screenshots/`. You can't see them, but:
- `ls -la` proves the capture happened.
- Hand the path to the user: "open <path> to confirm."
- If vision recovers, retry `vision_analyze` on that same path.

### 3. Reason from the code path
For visual complaints ("looks sparse", "wrong place"), reason about projection
+ line visibility, NOT dataset counts (see `cesium-resium-react` G36/G37).
State the inference as inference.

### 4. Ask the user to describe it
"I can't see the image (vision 404). Describe what you see?" Their words +
your code reasoning is usually enough to act.

## Pitfalls
- Fabricating image content = lying. Never.
- One 404 = backend down; report it, don't retry in a loop.
- The 404 is upstream, not a config you can flip.

## Verification
Prove the rendered state another way (console / snapshot / file exists)
before claiming a visual fix is correct.
