# Frame-accurate transport, and keeping the evidence record honest

## When to use

Adding pause / frame-step / scrub to a viewer, or any tool where a still taken from the
playback is later used as a record of *when* something happened. Applies to a desktop
console, a headless harness, or a web player — the rules are about the source and the
record, not the toolkit.

## Transport belongs on the source, behind a capability flag

Give the source a class-level `transport = False` and set it True **only** for a source
whose frames still exist after they have been shown (a recorded file). A live stream has no
past to seek back into, so it must not claim the flag.

The UI reads the flag and greys the strip. This is the same shape as a device/backend
abstraction: **the component that knows the truth answers the question.** Never offer a
control the active source cannot honour — a scrub bar over a live feed is a control that
lies. Grey it, and make the disabled control explain itself on hover *and* on click; a dead
button with no message reads as a bug.

## Pause must stop delivery, not replay the held frame

A paused source returns `None`. It does **not** re-emit the last frame. A frozen picture
that still looks live is the one fault a viewer cannot detect by looking, and a source that
keeps returning the same frame also silently fills any recording with duplicates.

Corollary: the frame loop must treat "nothing arrived" as *expected* while paused — do not
count it as a dropped frame, or the health figures on a review session become meaningless.

## Seek and step by frame index, never by counting reads

```python
cap.set(cv2.CAP_PROP_POS_FRAMES, index)
ok, data = cap.read()
```

Counting reads drifts on any container whose frame count the decoder only estimates, and an
off-by-one step **still looks plausible on screen** — so a still taken from it gets labelled
with the wrong position. An index you asked for is not the same as a frame you got.

Contract worth keeping:

- track `current` = index of the frame last shown, `-1` before the first one, so `step(+1)`
  from a fresh source lands on frame 0;
- **clamp `step`** at both ends — running off the end during a review is an easy accident,
  and silently wrapping to the start of a long recording is worse than going nowhere;
- **do not clamp `seek`** — an unclamped seek past the end returns `None` rather than
  inventing a frame;
- route a transport frame through the **same** correction/overlay path as playback (one
  shared `process(frame)`), so a paused frame is what playback produces, not a preview.

## Pausing must not corrupt the evidence record

If a recording keeps writing while the picture is frozen, the file fills with duplicates of
one frame **each stamped with a different wall-clock time** — the record then claims a
capture at an instant when nothing was captured. Hold the recorder while paused.

Then write the gap in explicitly: a `PAUSE` / `RESUME` row of the **same shape** as a frame
row, with the frame-derived columns empty. Same shape keeps the file one table so every
reader does not have to special-case it; the marker makes the gap documented rather than
silent. An unexplained gap in an evidence record is worse than a documented one.

Screenshot must still work while paused — that is the main point of pausing.

## Testing anything that reads frames

- **Write a clip whose every frame is a DIFFERENT flat grey** (`10 + i*10`). The pixel mean
  of the returned frame then proves which frame the decoder landed on; an index counter
  alone only records the *request*. A clip of identical frames can never show an off-by-one.
- **Assert pixel values with a tolerance, never equality.** `mp4v` is lossy — a flat grey
  comes back a few levels off. Space the frames ~10 grey levels apart and use a tolerance
  well under that step: it still proves frame identity while surviving the codec.
- **Drive the whole app headless for the end-to-end pass** (`QT_QPA_PLATFORM=offscreen`):
  open → play → pause → step → scrub → record across a pause → screenshot, then read the
  CSV back and assert the frame-row count against the marker count.
- Unit tests and the end-to-end run catch *different* bugs. Both are worth the minutes.

## Slider plumbing trap

A scrub handle must not be fought by the frame loop re-positioning it while the mouse is
still down. Track a `scrubbing` flag on press/release: block the loop's `setValue` while it
is set, and only seek on release. Update the position readout live during the drag.
