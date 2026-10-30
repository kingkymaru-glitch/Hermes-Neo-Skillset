# Proving an optimisation did not change the output

For an app whose output someone acts on — an inspection image, a measurement, an evidence
record — "a small rounding difference" is still a difference. A faster build that changes one
pixel produces a *different artifact*, and nobody can tell you which one is correct. The
optimisation is only safe once you have proven, mechanically, that the output is identical.

This applies to any point transform, colour conversion, resample or filter — not only image
work. The shape is: keep a naive reference, compare exactly, and prove the speed too.

## Write the reference implementation INTO the test

Re-implement the old slow code longhand inside the test file and assert the fast path equals it.

```python
def _naive_grade(image, p):
    """The pre-optimisation implementation, written out longhand.

    This is the reference: float32 cast, clip, cast back - once per operation.
    Intentionally the slow way, because that is what the fast path must reproduce.
    """
    b, g, r = (image[:, :, i] for i in range(3))
    channels = []
    for chan, gain, offset in ((b, p["b_gain"], p["b_offset"]), ...):
        if gain != 1.0:
            chan = np.clip(chan.astype(np.float32) * gain, 0, 255).astype(np.uint8)
        if offset:
            chan = np.clip(chan.astype(np.float32) + offset, 0, 255).astype(np.uint8)
        channels.append(chan)
    return np.dstack(channels)

assert np.array_equal(_naive_grade(img, p), fast_grade(img, p))
```

Two rules about the reference:

- **Never compare the new code against itself**, and never import the production helper as its
  own oracle. That passes for any implementation, including a broken one.
- **Re-implement it rather than importing the old version**, so that a later change to the
  production code fails the test loudly instead of silently comparing new-against-new.

## Assert exactly, not approximately

Use `np.array_equal` (or an exact byte compare). `assertAlmostEqual` / `np.allclose` will pass a
1-LSB shift, which is precisely the failure mode this is guarding against — library arithmetic
that rounds differently from the numpy expression it replaced.

On failure, print the *shape* of the difference, not just a boolean:

```python
d = np.abs(want.astype(int) - got.astype(int))
print(d.max(), d.mean(), (d > 0).mean() * 100)   # max / mean / % of values differing
```

A 1-LSB shift and a broken transform look identical in one averaged number. A hand-rolled
"equivalent" variant once came back with mean difference in the tens and ~99% of pixels
differing — that is a different algorithm wearing the same name, and the three-number report is
what makes the difference obvious.

## Cover the parameter space, not just today's values

Byte-exact on the one configuration in front of you is not byte-exact. Test the extremes and the
neutral case in one table-driven test:

- all-neutral / identity settings — must be a **true** no-op (`array_equal`), not merely close;
- every parameter at its minimum and maximum, and at zero;
- the specific tuned configuration the user actually runs (it is the one that will be used).

Also assert the identity path is *detected* and skipped: an untouched configuration should cost
nothing, which is both a correctness and a performance property.

## Prove the speed is real, in the same test file

An optimisation that is byte-identical but saves nothing is just extra code and extra risk.
Pair every correctness assertion with a timing one, and assert a *ratio* rather than an absolute
number so the test survives a slower or busier machine:

```python
def _bench(fn, n=12, warm=3):
    for _ in range(warm):
        fn()
    t0 = time.perf_counter()
    for _ in range(n):
        fn()
    return (time.perf_counter() - t0) / n * 1000.0

assert fast_ms * 3 < naive_ms, "no longer meaningfully faster - the fast path regressed"
```

Keep the margin loose (2-3x). A tight bound turns a busy CI box into a flaky failure, and the
claim being defended is "meaningfully faster", not a specific number.

## Preserve object identity, not just the values

If stages pass a frame/record object along, an "optimisation" that constructs a fresh output
object instead of deriving from the input silently resets timestamps and sequence numbers. The
pixels match and every latency figure downstream is wrong. Assert the identity fields survive:

```python
out = grade(frame, params, backend)
assert out.seq == frame.seq
assert out.ts_ns == frame.ts_ns          # a rebuilt object resets the clock
assert out.source_id == frame.source_id
```

## Report the change honestly

State which ops are byte-exact and which are not. If a candidate speedup could not be made
exact, say so explicitly and quantify it — do not quietly take the faster one. The user decides
whether a 1-LSB shift is acceptable; for an evidence-producing tool the default answer is no.
