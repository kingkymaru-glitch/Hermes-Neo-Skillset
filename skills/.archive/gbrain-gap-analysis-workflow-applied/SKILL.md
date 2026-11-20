---
name: gbrain-gap-analysis-workflow-applied
description: "GBrain gap-analysis workflow applied"
---

## Type
success pattern (auto-captured)

## Trigger


## Why this exists (captured automatically)
Auto-captured after a hard solve / mistake. Reuse instead of re-deriving.

## Steps
Before memory-dependent answer: run gap_analyze.py recall. If gap_signal=true, surface gaps[]. Synthesize from facts. After hard solve: skill_capture.py --title --force.

## Pitfalls
Memory at 2200 chars — consolidate before adding. FTS5 degraded, use LIKE fallback.

## Verification / Evidence
gap_analyze recall 'GBrain' returned gap_signal=true, gaps=['brain']. gap_analyze recall 'memory patterns' returned 5 facts.
