---
name: source-vs-rendered-verify
description: "Verify a rendered data layer matches its source dataset."
version: 1.0.0
author: Hermes Agent
license: MIT
---

## When this applies
- You render external data (GeoJSON, JSON feed, API) on a map/UI and the user
  says it "doesn't match the source" / "fewer items" / "wrong places".
- Before claiming the render is correct from dataset parity alone.
- Generalizes `cesium-resium-react` G38/G39 to ANY data layer (not just Cesium).

## The trap
"Count the data, not the screen" is the WRONG verification for a visual
fidelity complaint. The user judges the RENDERED SURFACE. Dataset parity (718
vs 717) is not proof the pixels are right. (See `cesium-resium-react` G36.)

## Steps (get ground truth from the render, not the dataset)
1. **Introspect the live output.** For web: expose app state
   (`window.__X = ...` DEBUG, remove after) + `browser_console` to count
   rendered items, read modes, check for NaN/empty. For a map: count entities
   + convert a KNOWN item's coordinates back to source space to compare.
2. **Diff source vs bundled.** Re-fetch the live source; compare
   `feature_id`/keys/feature count vs the bundled file (Node `Set` diff). 0
   drift = data fine. (Does NOT prove render is right — only that data matches.)
3. **Coordinate/transform check.** For geo: sanity-check a KNOWN feature's
   lon/lat range from raw source (e.g. a transatlantic cable should be
   lon -76..-3 / lat 36..46, NOT lat -76). A flipped range = lat/lon swap.
4. **Visibility/projection.** If count+coords are right but it "looks wrong":
   check color/alpha/width (faint thin lines read as "few") and projection
   (3D globe foreshortens vs flat 2D). Default flat 2D to match 2D references.
5. **Stale cache?** If introspection shows correct count/mode/coords for a
   known item, the code IS correct → user sees an OLD BUILD. Hard-refresh;
   compare live build hash (`curl <site> | grep assets/index-`) vs local
   `npm run build` hash.

## Pitfalls
- Don't layer more fixes on a verified-correct render (that's how cycles burn).
- Don't answer a visual complaint with raw dataset counts as "proof".
- If you can't see the screen (vision down), say so; reason from code path.
  See `vision-tool-down-workaround`.

## Verification
- Introspection shows rendered count == source count, 0 NaN, known item at
  correct source coordinates. OR: live build hash matches local build.
