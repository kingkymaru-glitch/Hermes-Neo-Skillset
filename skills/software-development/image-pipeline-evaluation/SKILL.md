---
name: image-pipeline-evaluation
description: Use when comparing image/video enhancement pipelines.
version: 1.0.0
tags: [computer-vision, image-processing, video, evaluation, benchmark, opencv]
license: MIT
---

# Evaluating image / video enhancement pipelines

## When to use

Choosing, tuning or signing off on an image-or-video enhancement pipeline — underwater colour
correction, low-light lift, dehaze, denoise, colour restore, upscale. The job is deciding WHICH
candidate is right, with evidence, and spotting when one is actively harming the footage.

## Procedure

1. **Get real footage before judging anything.** Synthetic or test-pattern input is fine for
   proving the harness runs, and is worthless for choosing a pipeline — it does not contain the
   degradations the pipelines are meant to fix, so it flatters whichever candidate suits the
   synthesiser. Say so out loud rather than quietly ranking on it.
2. **Measure, do not eyeball.** Run every candidate on the **same frame** and print one table.
   This metric set catches the failures the eye misses:

   | metric | why |
   |---|---|
   | per-channel means (B/G/R) | which channel a correction is eating |
   | R−B balance | colour cast direction and magnitude |
   | contrast (std of greyscale) | the only gain people usually look at — necessary, not sufficient |
   | mean brightness | catches darkening that contrast alone hides |
   | **% crushed** (grey < 12) | the single best tell: shadows destroyed to black |
   | % blown (grey > 243) | highlights destroyed |

3. **Write a labelled side-by-side still sheet** (`RAW | A | B | C`) for the human. The eye still
   decides whether the result is *acceptable* — the numbers only decide whether it is *honest*.
4. **Time every candidate on the same clip.** ms/frame and derived fps. A candidate that wins on
   quality but costs 8x more is a different decision than one that wins on both.
5. **Read the clip's own statistics before choosing.** Contrast, brightness, cast.

## Rules

- **Judge on contrast gained AND brightness/colour preserved.** A heavy dehaze routinely matches a
  mild one on the contrast column while halving mean brightness and crushing ~10% of the frame to
  near-black. Ranking on contrast alone is how a destructive pipeline gets selected.
- **Pipeline choice is scene-conditional, not fixed.** Footage that is already high-contrast does
  not need correction; applying a strong one to it removes information rather than leaving it
  alone. Report the choice as a rule over measurable scene character, not as one winner.
- **Keep a no-op baseline in every run.** Enhancement disabled is the floor: it exposes measurement
  overhead and makes every other row interpretable.
- **Never conclude from one clip.** Degradation classes cluster — the failure modes live in the
  classes you have not tested yet. State which classes remain uncovered.
- **Corroborate a visual read with pixel measurement before acting on it.** Downscaled or
  low-contrast crops produce confident wrong readings — a silently blank element read as "absent",
  a glyph edge read as a missing character. Count pixels, extents or channel values to settle it.
- **Record which candidate produced a result, with its parameters.** A verdict without its
  settings is not reproducible; write them to a preset or a per-frame CSV.

## Identifying which pipeline a live session is actually running

Per-stage latency is a fingerprint — candidates differ enough in cost that a stage timing
identifies one unambiguously (e.g. a heavy iterative filter at ~8x the cost of a light one). So a
screen recording of the app's own status readout is a measurement, not just a demo: read the
numbers off it instead of asking which setting was used.

Corollary: keep the per-stage timing visible in the UI, and log the stage breakdown per frame.
An app whose status bar shows `grab / pre / enhance / overlay / total` makes every user report
self-diagnosing.

## Reporting the result

Numbers table first, then the recommendation with concrete settings, then what is still untested.
Give the operator the parameter values to change, not the direction of change. If the measured
winner is also the cheap one, say both — it changes how much they trust the result.

## Related

- `local-webapp-verify`, `source-vs-rendered-verify` — verifying a running system matches intent.
- Any project with a device/backend abstraction: keep the *algorithm* layer pure so the same
  measurement harness runs on every backend, and record which backend produced each number.
