# DTwin pipeline performance: exhaustive → sequential matcher

Finding from the 2026-08-15 production pass, watching a live TESTMALL build.

## The bottleneck
`colmap exhaustive_matcher` brute-force matches EVERY image pair = N².
For a 300-frame build: 44,850 pairs. On this Mac it took ~4.2 HOURS and was
still on matching block 31/36 when observed. That single stage dominated the
whole build.

Root cause: DTwin's input is a VIDEO — frames are temporally ordered and
consecutive frames overlap. Brute-forcing all pairs is wasteful; you only need
each frame matched against its temporal neighbors.

## The fix
`colmap sequential_matcher` matches frame i against i±overlap.
- Pairs: 44,850 → 3,000 (overlap=10) = ~15× fewer
- Matching time: ~4.2h → ~8-10 min (estimated)

Suggested invocation (in `tools/pipeline.sh`):
```bash
run_timed "$MATCH_TO" colmap sequential_matcher \
  --database_path "$DB" \
  --SequentialMatching.overlap 10 \
  --SequentialMatching.loop_detection 1 \
  --FeatureMatching.use_gpu 0
```
`loop_detection` handles a drone/video that sweeps and revisits a spot, so
non-consecutive revisits still get matched.

## MATCH_TO budget must change too
The current budget is `N*N*0.12 + 120` (seconds), sized for exhaustive = ~3h for
300 frames. Sequential is O(N×overlap), so a sane bound is `N*overlap*~0.05 +
120` → ~10-15 min. Keep it bounded (hang protection) but don't keep the huge N²
budget.

## When NOT to use sequential
- Unordered photo sets (many separate shots, no temporal order) → `exhaustive`
  (few images) or `vocab_tree_matcher` (many images).
- For DTwin's core use case (video/walkthrough/drone), sequential is correct.

## Confirmed available
`colmap sequential_matcher --help` shows `--SequentialMatching.overlap (=10)`,
`--SequentialMatching.loop_detection (=0)`, `--SequentialMatching.loop_detection_period`,
`--SequentialMatching.loop_detection_num_images`, etc.

## Timing caveat
The perl alarm-kill timeout did NOT stop the long exhaustive matcher (ran 4h15m
past its ~3h budget, no SIGALRM kill observed). With sequential matcher the
stage is short enough that this matters far less, but do not assume the timeout
reliably kills a long-running COLMAP process — test it against the real tool,
not just `sleep`.
