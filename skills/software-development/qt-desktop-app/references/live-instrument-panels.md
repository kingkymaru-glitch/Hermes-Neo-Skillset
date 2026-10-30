# Live instrument panels — histograms, meters, scopes

## When to use

Adding a panel that shows a *live reading* of what the app is currently producing: a
histogram, a waveform, a level meter, a stats strip. The rules below are about the reading
staying truthful and staying cheap; they apply whether or not the toolkit is Qt.

## A live readout is a diagnostic, not a score

Say this in the panel's own tooltip, not just in the commit message. Users read a wide
histogram as "better", and a transform that **darkens** a frame *spreads* the distribution
out — so a damaging correction can look healthier than a good one while the picture has lost
information (a dehaze pass crushed 14% of a real frame to near-black and read as higher
contrast).

What keeps it honest:

- **Show the clipping figures** (percent crushed / blown per channel). Those are the part
  that cannot be misread as an improvement.
- **Overlay the input trace behind the output trace** — dimmed. A histogram on its own is
  just a shape; the useful reading is the *difference* between what came in and what the
  transform produced. A control that does nothing leaves the two on top of each other.
- **Normalise each pane to its own peak.** A shared scale flattens the channel with the
  least presence — and on the footage this was built for, the sparse channel was exactly the
  one worth watching.
- **Fold per-channel clipping into one boolean.** A pixel railed in any one channel has lost
  its colour even if its luminance is fine; summing the per-channel flags triple-counts a
  pure-white pixel.

## Measure OUTSIDE the thing being measured

Keep the measurement in the present/display layer, never inside the transform path. A meter
wired inside the transform corrupts both readings: it slows the pipeline it is reporting on,
and its cost lands in the latency figures displayed right beside it.

Gate the measurement on **panel visibility**. A closed panel, or an immersive mode that hides
it, must cost the frame loop nothing.

## A re-render is not a delivered frame

When a setting changes and the on-screen output has to be re-derived, do **not** increment
the frame counter or fold it into the fps average. Throughput figures are a statement about
how much the app is processing; a re-render of a frame already counted makes them a lie.
Give the re-derive path an explicit `count=False` (or equivalent) and pin it with a test.

## The paused-source trap — read this before adding ANY control that changes the output

**A paused source is not being read, so nothing re-runs the transform.** Move a slider while
paused and the picture, the panel and any still taken all keep the settings from the moment
the frame was grabbed. That is exactly backwards for a control whose whole purpose is
watching one frame respond — and it fails *silently*, because everything still looks fine.

Fix shape:

- Keep the source frame behind the on-screen picture, so it can be re-derived without
  re-reading the file.
- Add a `rerender()` that re-runs the **current** settings over that held frame, marked as
  not-a-delivered-frame.
- **The re-measure key must include the parameters, not just the frame identity.** Keying on
  the frame index alone freezes the panel precisely when a control moves — the source has not
  changed, only the settings. Key on `(frame_index, mode, algorithm, strength, params…)`.
- **Any action that displays a frame must also feed the measurement** — step, seek, scrub.
  They are easy to forget because they look like pure navigation.
- **A paused frame KEEPS its reading; it must not blank.** A paused frame is when the panel is
  worth studying. (Pausing before the first frame ever arrived legitimately shows nothing —
  do not invent a frame for that case.)
- **Do not add a convenience that contradicts the feature.** Forcing an "unprocessed" view
  while paused shows the uncorrected image, defeating the point of inspecting a processed one.

## Proving the panel actually responded

The trap above survives every unit test that only checks the numbers were computed. Render
the widget to an image under two different settings and compare the bytes:

```python
img = QImage(panel.width(), panel.height(), QImage.Format.Format_RGB32)
img.fill(0)
panel.render(img)
data = np.frombuffer(img.constBits(), np.uint8).copy()   # .copy() — see the dangling-view trap
assert len(np.unique(data)) > 3                          # it drew something at all
```

Then assert `not np.array_equal(before, after)` across a control change. Two assertions, and
both are needed: **non-blank** catches a renderer that silently draws nothing, **changed**
catches a panel that is drawing a stale reading.

Run this against the **real media**, not a synthetic fixture. Three of the four bugs in the
release that added this panel were invisible on generated test frames and only appeared on a
real recording — a uniform test frame has no distribution to move.
