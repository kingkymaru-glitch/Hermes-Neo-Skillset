# The per-frame budget — profiling a live processed video feed

An app that displays a *processed* live feed has a hard constraint the rest of a desktop app
does not: every stage runs on every frame, and the display rate is the sum of them. This file
is how to find where that budget goes, and how to answer "is this my hardware?" honestly.

## Answering the hardware question

When the user reports lag and asks whether it is their machine, or whether a GPU would fix
it, **do not answer from the profile alone.** Split the cost into two buckets:

- **Avoidable overhead** — allocation churn, throwaway intermediates, redundant passes,
  recomputing something that did not change. A GPU does **not** fix any of this; per-op
  launch cost grows while the wasted work stays.
- **Genuine per-pixel work** — the only part that is a hardware argument.

State the split *before* endorsing a purchase. Recommending hardware while half the cost is
avoidable overhead is buying a way out of the code's own inefficiency.

Also: **check the user's actual saved configuration before theorising.** A tuned profile, or a
panel left open, can dominate the total, and the number they report comes from their real
session rather than a default one. Reproduce their settings, then measure. For this app family
the live state sits in the user's application-support directory (`console.json` / a presets
file), which is exactly the config that a fresh-process benchmark will not have.

Answer the feasibility half directly too: if the accelerator cannot run on the current machine
at all (no vendor support for that GPU on that OS), say so — someone asking about a GPU needs
to know the box itself is out, not merely that it would be faster.

## Profile the frame, stage by stage, then op by op

Measure each stage on a **real** recording, never on a generated fixture — a synthetic frame
has no distribution and hides the cost of anything data-dependent.

```python
def bench(fn, n=15, warm=3):
    for _ in range(warm):
        fn()
    t0 = time.perf_counter()
    for _ in range(n):
        fn()
    return (time.perf_counter() - t0) / n * 1000.0   # ms per call
```

Warm up first; the first call carries lazy-init and cache-cold cost. Then total the stages and
compare against the app's own on-screen readout — if they disagree, something is running per
frame that you have not accounted for (a panel that redraws, a repaint, a conversion).

**Cost scales linearly with pixel count.** A stage measured 38 / 85 / 332 ms at 720p / 1080p /
4K. Never quote one resolution's figure as if it predicts another — the user's camera
resolution is part of the answer, and it is the cleanest way to show that a CPU-side fix
cannot close the gap at high resolution.

## The allocation-churn pattern (usually the biggest single win)

A helper written as `astype(float32) -> arithmetic -> clip -> astype(uint8)` performs **three
full-frame allocations per call**. One is cheap; a per-channel loop calling it six times is not:

| path | 720p | byte-exact? |
|---|---|---|
| per-channel `astype/clip/astype` loop, 6 ops | ~14 ms | reference |
| one fused pass per channel (`cv2.convertScaleAbs(alpha=, beta=)`) | ~1.3 ms | **NO** — max diff 1 on ~40% of pixels |
| per-channel 256-entry LUT applied with `cv2.LUT` | ~1.5 ms | **yes** |

**The LUT is the one to reach for: it is byte-exact AND it collapses the whole operation.** A
per-*value* operation (gain, offset, threshold, any point transform) is a pure function of the
input value, so the entire stage becomes one lookup per channel instead of a chain of
full-frame passes — six passes became three lookups, 14.5 ms → 3.65 ms at 720p with the picture
unchanged. The same shape is nearly free on a GPU (one texture fetch), so it ports.

**`convertScaleAbs` is faster but NOT a drop-in** — it rounds to nearest where the numpy
`astype` truncated. That is a 1-LSB difference on roughly half of all values, so it is a
behaviour change, not an optimisation. Use it only when the caller accepts changed output.

**Same trap in the scalar helpers:** `cv2.multiply` / `cv2.add` also round to nearest, so they
are **not** drop-in replacements for `np.clip(arr.astype(np.float32) * f, 0, 255).astype(np.uint8)`.
Route those through the LUT too, which reproduces the original arithmetic exactly.

**Match the dtype of the code you are replacing.** Building the table at float64 instead of
float32 moved two of the 256 entries across a 0.5 rounding boundary and broke byte-exactness on
its own. Precision is not an interchangeable detail when the goal is identical output.

**Reproduce the quantisation ORDER as well as the arithmetic.** If the original quantised after
each step (`scale → uint8`, then `offset → uint8`), the table must do the same. Quantising once
at the end is more accurate and gives a *different picture* — which is not an optimisation.

Grep the op/backend layer for that shape before optimising anything else.

## A reduction must not be fed by a throwaway copy

The worst single op in one pipeline existed only to squeeze a channel out of a reduction:

```python
# expensive — the merge allocates a full 3-channel frame just to discard it
min_channels(merge([b, g, b]))          # ~8.5 ms at 720p
# byte-identical, ~280x faster
np.minimum(b, g)                        # ~0.03 ms
```

**A throwaway intermediate in front of a reduction is the first thing to look for** — the
reduction itself is nearly free, the copy before it is not. Likewise a broadcast subtract
against a reshaped `(1,1,3)` array cost ~8.3 ms where the equivalent scalar-tuple subtract
cost ~0.46 ms.

## Prove the fast path produces the same picture

Any candidate speedup must be diffed against the current output on real data:

```python
d = np.abs(current.astype(int) - fast.astype(int))
print(d.max(), d.mean(), (d > 0).mean() * 100)   # max / mean / % of pixels differing
```

Report all three. A 1-LSB rounding shift and a broken transform look identical in a single
averaged number — a hand-rolled "equivalent" variant once came back with a mean difference in
the tens and ~99% of pixels differing, i.e. it was a different algorithm. If the result is not
byte-exact, that is a behaviour change, not an optimisation: surface it, quantify it, and let
the user decide. Never swap it in silently.

## A measurement panel costs the frame budget too

A live histogram/meter recomputed every frame is real per-frame cost. Three fixes, in order:

1. **Do not recompute the side that did not change.** An input/RAW histogram is constant while
   the source is constant — cache it keyed on the frame index rather than measuring both sides
   every tick. This was the largest avoidable cost in an idle console.
2. **Gate on panel visibility** — a closed panel, or an immersive mode that hides it, must
   cost the loop nothing.
3. **Sample with a stride, not an interpolating resize.** This one is counter-intuitive and was
   the single most expensive line in the whole console: `cv2.resize(..., INTER_AREA)` is the
   textbook downscale and it cost **6.2 ms of a 7.8 ms measurement** at a large ratio. For
   anything that needs a *distribution* rather than a picture, `arr[::step, ::step]` is far
   cheaper **and more honest**: every sampled value really was in the frame, whereas an
   interpolating resize invents values between them and can soften a clipped pixel off its rail.
   The clipping figures are the part of the panel that must stay truthful, so sampling that
   cannot move them is the right sampling.

```python
def _sample(img, sample_max):
    longest = max(img.shape[:2])
    if longest <= sample_max:
        return img
    step = int(np.ceil(longest / float(sample_max)))
    return img[::step, ::step]          # make contiguous before per-channel flattening
```

Verify the sampling did not distort the reading: compute the clipping fractions at full and
sampled resolution and assert they agree within a small delta.

See `live-instrument-panels.md` for the rest of the panel rules.

## cv2 5.x refuses a bare Python scalar

`cv2.multiply(img, 1.09)` raises *"src2 is not a numpy array, neither a scalar"*. Pass a typed
numpy scalar (`np.float32(v)`) or a scalar tuple, or use `cv2.convertScaleAbs(alpha=, beta=)`.
Non-contiguous inputs and arrays built by `np.frombuffer` on a slice trigger the same overload
failure — make the array contiguous first, then re-measure, since the copy may itself be the
cost you were hunting.

## When the chosen algorithm is both slower and worse, say so

If the user is running the expensive option, the useful answer includes that a cheaper one is
also the better one — with the measured numbers behind that claim, not an opinion. Being fast
is not the only axis: a transform can look *sharper* (unsharp masking raises edge acutance)
while throwing away luminance range and crushing a large fraction of the frame to black.
Perceptual sharpness and retained information are different things, and for an inspection tool
the second one governs.
