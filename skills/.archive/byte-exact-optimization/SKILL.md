---
name: byte-exact-optimization
description: Speed up code without changing its output at all.
version: 1.0.0
tags: [performance, optimization, profiling, correctness, numpy, opencv, image-processing]
---

# Byte-exact optimization

Making code faster when **the output is evidence** — inspection imagery, measurements,
generated documents, audit records, anything a human will act on or sign. In these
codebases a faster path that alters one pixel or one digit is not an optimisation; it is
a regression with a speed story. The extra discipline below is what separates the two.

Use this alongside a general profiling workflow (baseline → locate → isolate → verify →
re-benchmark). This skill is the part that general workflow leaves out: **how to prove
the fast path produces the same answer**, and the exact traps that make it not.

## The discipline

1. **Write the naive reference longhand INSIDE the test — never import it from production.**
   A test that imports the helper it is checking compares the new code against itself and
   passes forever. Re-implement the old arithmetic in the test file, deliberately the slow
   way, and assert equality against the new path.
2. **Assert the speed as well as the output.** A byte-identical change that saves nothing
   is extra code and a new place to be wrong. Measure both in the same test; assert a
   ratio, not an absolute time, so it survives a slower machine.
3. **Profile INSIDE the stage, not just the stage.** "This step costs 38 ms" is not
   actionable. "8.45 ms of that is building a throwaway copy" is. Attribute cost to a line
   before rewriting anything.
4. **Measure on the real asset.** Synthetic inputs hide costs real data exposes instantly.
5. **A reported number can be half avoidable overhead.** Before recommending a hardware
   upgrade, check how much of the cost is the code's own allocation churn — otherwise the
   hardware is buying you out of your own inefficiency. Say the split out loud.

## Exactness traps when swapping an operation for a faster equivalent

### OpenCV arithmetic ROUNDS; numpy astype TRUNCATES

`cv2.add` / `cv2.multiply` round to nearest. The numpy expression
`np.clip(v.astype(np.float32) * g, 0, 255).astype(np.uint8)` truncates. That is a 1-LSB
difference on roughly half of all input values, so they are **not** drop-in replacements
for a numpy scalar op.

```
1 * 0.93  ->  truncated 0      rounded 1
3 * 0.93  ->  truncated 2      rounded 3
```

### The right fast path for any per-VALUE operation is a lookup table

A per-channel gain/offset is a pure function of the input value, so the whole operation
collapses into one `cv2.LUT` pass. Two traps make a table *not* exact:

- **Build the table at the same precision as the original.** float64 rounds boundary
  entries differently from float32 — two of the 256 entries shift.
- **Reproduce the QUANTISATION ORDER.** If the original was two chained ops that each
  quantised to uint8 in between, the table must quantise twice too. Collapsing to a single
  rounding is *more accurate arithmetic* and a *different picture*.

```python
# a two-step original needs a two-step table
scaled = np.clip(values * g, 0, 255).astype(np.uint8)          # intermediate quantise
scaled = scaled.astype(np.float32)
table  = np.clip(scaled + o, 0, 255).astype(np.uint8)
```

Measured: six full-frame float32 passes → three lookups took a manual colour grade from
**14.5 ms to 3.65 ms** on a 720p frame, byte-identical.

**Put the table op on the device-abstraction interface, not as a CPU-only helper.** On a
GPU the same operation is one texture fetch, so the win survives the port instead of
needing to be re-found.

### Never build a wider copy to reduce over fewer channels than the copy has

```python
# build (B,G,B), then min over 3 channels, to get min(B,G)  -> 8.45 ms of a 38 ms pipeline
min_channels(merge([b, g, b]))
# direct pairwise reduce, identical result                    -> 0.03 ms
np.minimum(b, g)
```

Make the helper reduce pairwise and pass a 2-D input through unchanged, rather than
assuming 3 channels and forcing a 3-channel copy into existence.

### `cv2.resize(..., INTER_AREA)` is pathologically slow at large downscale ratios

At 720p downscaled to 360 px on the long edge:

| method | cost |
|---|---|
| `INTER_AREA` | **6.17 ms** |
| `INTER_LINEAR` | 0.18 ms |
| `INTER_NEAREST` | 0.07 ms |
| stride view `img[::2, ::2]` | ~0 ms |

INTER_AREA is the textbook choice for downscaling and it was the single most expensive
line in an entire application. When the consumer is a **distribution or a statistic**
(histogram, percentiles, coverage), use a **systematic stride**:

```python
step = int(np.ceil(max(a.shape[:2]) / sample_max))
sample = a[::step, ::step]
```

Stride also beats `INTER_LINEAR` on correctness, not just speed: interpolation **invents
values between the real ones** and can move a clipped pixel off its rail. Every value in a
stride sample is a value that was actually in the data — which matters when the statistic
you are computing is "how much of this is saturated".

## Caching and re-measurement

- **Gate any measurement on visibility.** A diagnostic panel that is closed or hidden must
  cost the loop nothing. Check visibility before measuring.
- **Keep the meter OUT of the path it measures.** A measurement wired inside the thing it
  measures corrupts both readings, and it makes the latency figures measure the meter.
- **Key a cached measurement on the input AND the parameters, never the input alone.**
  Keyed on the input index only, the cache freezes exactly when a user moves a control —
  the input has not changed, only the settings.
- **An idle or paused producer is not being read, so nothing re-runs the pipeline.** If the
  UI lets a user tune a control against a frozen input, you need an explicit re-derive path
  that re-runs the SAME input through the current settings. Give that path a mode which
  does **not** count as a new sample: a re-render is not a capture, and a throughput figure
  that includes re-renders is a lie.

## Reporting the result

State the before/after per stage, not just the total — the interesting finding is usually
which *part* was waste. And state plainly which portion a hardware change would and would
not fix: CPU-side allocation overhead does not become faster on a GPU.

## Pitfalls

- **Shipping the optimisation without the equality test.** The whole value of this skill is
  that the fast path is *proven* identical. An unproven one is a liability that surfaces as
  a subtly wrong output months later.
- **Comparing against production code** (see discipline #1). This is the most common way a
  byte-exactness suite is silently worthless.
- **Assuming a library's "obvious" faster equivalent is numerically equivalent.** Check the
  rounding mode. `cv2.*` and numpy disagree by design.
- **Benchmarking a live GUI session while screen-recording.** The recording inflates every
  stage. Measure in isolation.
- **Chasing a speedup that the profiler did not name.** If you cannot attribute the cost to
  a line, you are guessing.
