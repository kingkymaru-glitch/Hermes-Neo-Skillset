---
name: gap-analyze-feedback-must-not-double-count-retrieval-on-helpful
description: "gap_analyze feedback must not double-count retrieval on --helpful"
---

## Type
FAILURE AUTOPSY (auto-captured)

## Trigger
feedback --helpful kept fact at 0.5

## Why this exists (captured automatically)
Auto-captured after a hard solve / mistake. Reuse instead of re-deriving.

## Steps
feedback increments helpful_count ONLY

## Pitfalls
double-counting retrieval dilutes positive signal

## Verification / Evidence
caught 2026-08-20, verified live
