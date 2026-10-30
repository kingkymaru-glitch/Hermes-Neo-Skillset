---
name: qt-desktop-app
description: Use when building a PySide6/Qt desktop GUI app.
version: 1.0.0
tags: [qt, pyside6, desktop, gui, python, video, qimage, svg]
license: MIT
---

# Building a Qt / PySide6 desktop app

## When to use
A desktop GUI in Python — operator consoles, viewers, tools that show a live feed or
rendered frames. PySide6 (`pip install PySide6`) works on the current Homebrew Python;
`opencv-python-headless` is fine alongside it because the frames are converted to `QImage`
by hand rather than shown through cv2's own highgui.

## Structure that survives contact

**Keep the engine free of Qt.** Put all the real work in a plain-module engine
(load sources, transform frames, write outputs) and let the Qt file only wire widgets to it
and put the resulting image on screen. Two payoffs, both immediate:

- the engine is unit-testable **headless** — no display, no `QApplication` needed;
- widget plumbing changes never touch the logic.

Then the GUI module is thin: build widgets, connect signals to state, run a `QTimer` loop
that pulls one frame per tick and calls `setPixmap`.

**Test headless with `QT_QPA_PLATFORM=offscreen`.** This constructs the whole window, drives
the loop, and exercises state round-trips in CI or a terminal. Run the offscreen test *before*
launching for real — a widget-construction error is instant offscreen and invisible otherwise.

Give long-running work a `QTimer` on the source's frame period rather than a blocking loop,
so the UI stays responsive and a stop is immediate.

## numpy ↔ QImage

```python
rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
h, w = rgb.shape[:2]
qimg = QImage(rgb.data, w, h, rgb.strides[0], QImage.Format.Format_RGB888).copy()
```

- **`.copy()` is mandatory.** `QImage` does not own the numpy buffer; without the copy the
  image points at memory that numpy can free, and you get tearing or garbage.
- **Use scoped enum names** (`QImage.Format.Format_RGB888`, `Qt.AlignmentFlag.AlignCenter`,
  `Qt.AspectRatioMode.KeepAspectRatio`, `Qt.Orientation.Horizontal`). The unscoped spellings
  are unreliable across PySide6 versions; the scoped form works everywhere.
- Read back a Qt buffer the same way, and copy:
  `np.frombuffer(img.constBits(), np.uint8).reshape(h, img.bytesPerLine()//4, 4)[:, :w, :].copy()`.
  `Format_ARGB32` is bytes **B,G,R,A** on little-endian, i.e. already BGRA — do **not** run it
  through an RGBA→BGRA swap.

## Silent-failure traps

These produce a correct-looking API result and a wrong picture.

- **`QPainter` and `QSvgRenderer` need a `QGuiApplication` to exist.** With none, they paint
  *nothing* and raise *nothing* — you get a fully transparent render and a success return.
  For a headless caller, create one lazily: `os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")`
  then `QApplication([])`, and keep a reference alive.
- **`np.frombuffer(qimage.constBits())` is a dangling view the moment the QImage is freed.**
  The caller then reads whatever memory Qt reuses — which presents as a *colour* bug, not a
  crash (e.g. blue stripped out of a purple). `np.ascontiguousarray` does **not** save you: a
  full-width slice is already contiguous, so it copies nothing. Use an explicit `.copy()`.
- **`QSvgRenderer` is SVG Tiny and fails silently.** `isValid()` returns True and
  `defaultSize()` is correct while it draws zero pixels. Known causes:
  - **CSS `color(display-p3 …)` / `color(srgb …)` declarations.** A `style` attribute
    overrides the plain presentation attribute, so an unparseable colour *wins* over a valid
    `fill="#rrggbb"` and the whole mark vanishes. Fix: strip `(?:fill|stroke|stop-color):\s*color\([^)]*\)`
    before handing the text to the renderer, which leaves the hex fill in effect.
  - `filter="url(#…)"` (SVG filters) are unsupported; `mask="url(#…)"` is only partly
    supported. Dropping the references usually renders *more* of the artwork, not less.
  - Brand SVGs exported from Figma/Sketch commonly contain both. **If SVG fidelity matters and
    no system rasteriser is available, ask for a PNG instead** — a blank logo that no error
    flags is far worse than a one-line request.
- **Assert every render produced pixels.** `if (alpha > 8).sum() == 0: raise`. A renderer that
  fails silently is worse than one that fails loudly; this one check would have caught the two
  bugs above immediately.
- **`QShortcut(QKeySequence("R"), self, activated=fn)` is not valid PySide6.** Construct then
  connect: `sc = QShortcut(QKeySequence("R"), self); sc.activated.connect(fn)`.
- **Loading state into widgets destroys that state unless you guard the load.** `setCurrentIndex`
  / `setValue` / `setChecked` / `setText` all fire their changed signals, and those handlers push
  the *widget* values back into the state — so the widgets overwrite the very state they are being
  loaded from. If the load sets some widgets before others, the first signal writes the DEFAULT
  values over the state and the later part of the loop then reads the state it has just erased.
  **A saved session was silently discarded on every launch this way**, with nothing on screen to
  say so. Set a `_loading` flag around the entire load and have the push handler return early
  while it is set. Same family as the checkable-QAction re-entrancy trap above: any two-way
  widget↔state sync needs a guard, and the bug is invisible because each direction looks correct
  on its own. Test it by constructing the window from a non-default state and asserting the state
  survived — not by round-tripping through the widgets.
- Qt cannot express press-and-hold on a shortcut — a shortcut fires on press only. For a real
  hold-to-compare, handle `keyPressEvent`/`keyReleaseEvent` on the window instead of a
  `QShortcut`.

## Verifying a rendered frame — measure, do not look

An image-model reading of a rendered frame is **not** ground truth. It has claimed a logo was
absent when it was present-but-blank, and claimed a truncated trailing character that pixel
measurement disproved. Before acting on a visual claim about rendered output, check pixels:

```python
band = img[0:59, :]                                   # isolate the region of interest
b, g, r = (band[:, :, i].astype(int) for i in range(3))
text = (b > 120) & (g > 120) & (r > 120)              # whitish glyph pixels, exclude accents
cols = text.sum(axis=0)
# walk `cols` for runs of ink -> glyph count and the true right-hand extent
```

Then confirm the element's colour numerically (mean over the alpha>0 or ink mask) against the
value it should be. Numbers settle questions that a description cannot.

## UI conventions for this user

- **Every parameter carries a hover tooltip that states what it does AND how it fails.** Not a
  synonym of the label — the failure mode is the useful half.
- Pickers are **dropdowns**, never a list rendered inline.
- Panels are collapsible and dockable; secondary controls do not start expanded.
- A slider alone cannot express an exact value — pair every slider with a spinbox so a tuned
  setting can be written down and reproduced.
- **A reset control belongs INSIDE the group it resets, and resets only that group.** A
  toolbar entry for a panel's sliders reads as *missing* — the user hunts for it while the
  result is already wrong, which is the worst possible moment to be hunting. And a button in
  one group must not move a control in another: resetting the manual grade must leave the
  auto-correction strength, the overlay and the capture settings untouched. A control moving
  in a group the user did not press is a surprise, and on a paused source it silently changes
  the output being studied. Pin both halves — everything in the group returns to its default,
  and something outside it does not move. Re-derive the output after resetting, or the widgets
  and the picture disagree (see `references/live-instrument-panels.md`).
- Ship a double-click launcher, not a terminal command. See the `macos-desktop-launcher`
  skill (and its `references/app-bundle.md`) for the `.app` bundle + custom icon recipe.
- **A control needed DURING an immersive mode must not live in a closable panel.** Panels
  are the right home for parameters; a control the user reaches for while the panels are
  away (playback transport during a full-screen review) belongs in the central widget
  beside the content. Have the explicit "hide everything" command take it, and leave it
  alone when only the panels are hidden.
- **Enable/disable a control from the ACTIVE capability, not from the widget's own state.**
  A control that is merely greyed must explain itself on hover and on click — a dead button
  with no message reads as a bug. Sync that enablement on connect and on source change as
  well as in the frame loop, or the control stays dead for one tick after connecting and
  the first click does nothing.
- **A user-facing name may change; a STORED key may not.** When you relabel an option for
  legibility, change the label only and leave the persisted identifier alone. Records already
  written carry the old key, and a record that reads "Rebalance" while the file that produced
  it says `a` is an ambiguity an evidence trail must not have. Keep the display text and the
  stored value in separate layers, and pin both halves in one test: the label carries words,
  and selecting the last item still stores the original key.
- **Read the app version from the package; never hardcode it in the bundle script.** A literal
  `VERSION="0.5.0"` in the `.app` builder drifts from `__version__` the first time someone
  bumps one and forgets the other, and the plist then disagrees with the code it contains —
  confidently wrong, which is worse than absent. Derive it
  (`python -c 'import pkg; print(pkg.__version__)'`) and strip the descriptive suffix macOS
  will not accept in `CFBundleShortVersionString`. This is the same rule as the stored-key one
  above: derive the fact, do not keep a second copy of it that can rot.

## Test traps

- **A test that zips a hardcoded list against a growing collection silently stops covering
  the last item.** When a new panel/tab/source is added to a collection that tests iterate,
  every `zip(expected, actual)` quietly drops the new entry and the suite stays green while
  the newest thing is untested. Assert the lengths match in the same test, so adding an item
  fails loudly instead of shrinking coverage.
- Assert a render produced pixels, and that it *changed* when a control moved — see
  `references/live-instrument-panels.md`.

## See also
- `macos-desktop-launcher` — `.command`/`.app` launcher pitfalls and the custom-icon recipe.
- `references/per-frame-budget.md` — profiling a live processed feed: splitting avoidable
  overhead from genuine per-pixel work before answering "is this my hardware?", the
  allocation-churn and throwaway-copy patterns, LUT vs fused-pass vs interpolating-resize.
- `references/byte-exact-optimisation.md` — proving a speedup did not change the output: the
  naive reference implementation in the test, exact compares over the parameter space, proving
  the speed is real, and preserving object identity (timestamps) through a rewritten stage.
- `references/video-transport-and-evidence.md` — frame-accurate pause / step / scrub: the
  capability flag on the source, seeking by frame index, and keeping the evidence record
  honest while paused.
- `references/live-instrument-panels.md` — live histograms/meters: diagnostic-not-score,
  the paused-source re-render trap, and proving the panel actually responded.
- `lunav-sado-dev` — a worked instance: device-agnostic pipeline with a Qt console on top.
