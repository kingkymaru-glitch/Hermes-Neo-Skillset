---
name: lunav-sado-dev
description: Use when working on LUNAV SADO (ROV video correction).
version: 1.0.0
tags: [lunav, rov, underwater, video-enhancement, opencv, cuda, rocm, gpu, benchmark]
license: MIT
---

# LUNAV SADO — development

**S**patial **A**wareness **D**evice **O**ptimization. Low-latency real-time underwater video
correction for ROV ops. Parent = LunaV Solutions (`[[SS Rover Cloud]]`). Optical sibling of
LUNASCAN-SONAR (acoustic).

- Repo: `kingkymaru-glitch/LUNAV-SADO` (private, MIT) · local `~/LUNAV-SADO`
- Obsidian: `Projects/LUNAV SADO.md` · releases `V0.1.0-plan` (design) → `V0.2.0-phase1` (harness)

## Architecture — do not break these two rules

Five stages, and the ONLY place that knows their order is `src/lunav_sado/runner.py`:

```
INGEST -> PRE-PROCESS -> ENHANCE -> INSTRUMENT -> SINK
            (+ orthogonal BACKEND layer: cpu | cuda | opencl | hip | metal)
```

1. **No stage imports a vendor/device API.** Stages request operations by name from the
   resolved backend (`backend.clahe(...)`, never `cv2.cuda.*`). This is what makes the
   NVIDIA → Radeon port a build change instead of a rewrite. If adding a backend requires
   touching `stages/enhance/`, the abstraction leaked.
2. **One frame contract.** `Frame(data, ts_ns, seq, source_id, meta)`. Stages return
   `frame.derive(data)` — never construct a Frame directly, because rewriting `ts_ns`
   mid-pipeline corrupts every latency figure downstream.

Duplication rule: to clone into a variant, change only four configs — `FrameSource`,
algorithm set + params, backend, `Sink`. Needing to edit a *stage* means the stage boundary
is wrong; fix it upstream, not in the fork.

## The operator console (`src/lunav_sado/app/`)

`python -m lunav_sado.app` or double-click `launch/LUNAV SADO Console.command`.
The default source is a **synthetic test pattern**, so the console opens and can be
exercised with no camera — keep that property.

```
source -> grade (manual) -> enhance (auto, blended by strength) -> overlay
          +------------------ corrected -------------------+
                                 |-> display (RAW on wipe)
                                 |-> recorder (burn-in per toggle)
                                 |-> screenshot
```

- **Hard boundary: the overlay composes AFTER enhance, in `present/`.** Putting it
  inside the correction path contaminates the corrected artifact and makes the
  latency numbers measure text drawing.
- **`app/session.py` holds no Qt.** All frame work lives there so the engine is
  testable headless (`QT_QPA_PLATFORM=offscreen`); `app/gui.py` only wires widgets.
- **Burn-in toggle:** ON = presented frame with overlay (client deliverable);
  OFF = clean corrected frame (evidence stream). Either way `present/recorder.py`
  writes a **session CSV beside the video** pairing every frame with its wall clock.
  A burned-in timestamp is a claim; the CSV is what makes it checkable. Never drop
  that pairing — it cannot be retrofitted after a dive.
- Presets live in the user app-support dir, **never in the repo**, so a clean
  checkout does not wipe an operator's tuned settings.
- `StreamSource.next()` returns `None` on failure and **never re-emits the last
  frame**. A frozen picture that still looks live is the one fault an operator
  cannot detect.

## Keyboard controls — do not go back to single-letter QShortcuts

**Qt deliberately lets a focused text field consume printable keys.** A plain `QShortcut` for
`R` / `S` / `W` therefore stops firing the moment the cursor sits in the heading, URL or
session-label field — which is exactly what the operator hit: the buttons worked, the keys
did not, with no error anywhere. This is Qt protecting text entry, not a bug to work around.

- The console handles keys with an **application-level `eventFilter` on MainWindow**
  (`app.installEventFilter(self)`), which acts only when a `QLineEdit` / `QAbstractSpinBox` /
  `QComboBox` does NOT have focus. Typing can never trigger a control.
- **`Cmd+R` / `Cmd+S` menu accelerators are the reliable path** — a modified key is never
  consumed as text, so they always work. Keep both.
- `W` is a **press-and-hold** (press → RAW, release → corrected). A toggle is not what "hold to
  see RAW" means. Also expose a hold-able toolbar button and a lock checkbox for hands-free use.
- Do not persist a "locked RAW" flag into presets — reopening locked to RAW looks like the
  correction failed.
- Anything that syncs a checkable action from code must use `blockSignals` (see the
  re-entrancy trap above).

## Copy discipline

The console is shown to clients. **No first or second person in the UI** — no "my", "your",
"you". Tooltips state what a control does and how it fails, without addressing the reader.
This is enforced by `tests/test_gui.py::TestProfessionalCopy`, which scans every label, button,
combo item and tooltip and fails the suite if those words reappear. Untested copy discipline
rots. When adding a control, write the tooltip in the neutral register from the start.

## Qt / rendering traps hit in this project

- **A checkable QAction can re-enter its own handler.** `setChecked()` emits `toggled`, so a
  handler that calls `setChecked` at the end re-runs itself. In the focus-view case the
  re-entry re-recorded the "pre-focus layout" *after* the panels were hidden, so pressing the
  shortcut twice left the panels gone permanently. Sync programmatic state with
  `blockSignals(True) … setChecked(x) … blockSignals(False)`. Make every toggle idempotent
  and test it by toggling twice.
- **QDockWidget visibility cannot be set before the window is shown.** Qt defers it, so a saved
  layout applied pre-`show()` silently does nothing. Call `show()` first, then apply state,
  then `QApplication.processEvents()` to flush. Tests must also `show()` the window —
  `dock.isVisible()` is False on an unshown window, so assertions pass or fail for the wrong
  reason.
- **Cache the scaled sprite, not just the loaded image.** Re-scaling a 490x512 logo to banner
  height every frame was the overlay's single biggest cost (1.4 ms at 720p, more than the band
  blend, timestamp and subtext combined). Key the cache on (path, mtime, target height).
- **Never benchmark a live GUI session while a screen recording is running.** A founder-reported
  `overlay 7.1 ms` was really 2.5 ms; the recording inflates every stage. Measure in isolation.
- **`QPainter` and `QSvgRenderer` need a QGuiApplication.** Without one they paint nothing and
  raise nothing — the render is silently fully transparent. `overlay.py` lazily creates one with
  `QT_QPA_PLATFORM=offscreen` for headless callers.
- **Qt cannot parse CSS `color(display-p3 …)`.** A `style` attribute overrides the plain hex
  `fill`, so an unparseable P3 colour *wins* and the whole SVG renders as nothing — while
  `isValid()` returns True and `defaultSize` is correct. The LunaV brand mark has 16 such
  declarations. `_sanitise_svg()` strips them; a render is then asserted non-blank. **Always
  assert a render produced pixels** — a renderer that fails silently is worse than one that fails.
- **`np.frombuffer(image.constBits())` is a dangling view.** Qt frees the QImage when the
  function returns, so the caller reads freed memory that *looks* like a colour bug (blue stripped
  out of a purple logo). `np.ascontiguousarray` does NOT copy when the slice is already
  contiguous — use an explicit `.copy()`.
- `QShortcut(..., activated=...)` is not valid PySide6; construct then `.connect()`.
- Verify overlay output with **pixel measurement**, not a visual read: the vision tool claimed a
  missing logo and a truncated last character, both disproved by counting glyph runs and checking
  the background beyond the text.

## Backend resolution traps (both were real bugs)

- **Honour an explicit request exactly.** An explicit `backend: cpu` was silently resolving
  to **OpenCL**, because macOS ships an OpenCL runtime and resolution fell through to
  "first available". Every Phase 1 CSV would have carried a GPU label on CPU numbers.
  Pinned by `test_explicit_cpu_returns_cpu_not_the_first_available_gpu`. When building any
  device-abstraction layer: explicit config wins; probe/auto is a separate code path.
- **A stub must RAISE, not substitute.** `cuda`/`hip`/`opencl`/`metal` probe the machine and
  raise `NotImplementedError` on ops. Silently running the CPU path while reporting a GPU
  backend is worse than no benchmark.
- `auto` must never select `metal` (Apple, dev-only). Guard it by name, not by "not darwin".
- **A benchmark without its backend recorded is not evidence** — `backend` is a CSV column.
- cv2 traps hit here: `cv2.divide` will not broadcast a 1-channel denominator against a
  3-channel image (use numpy broadcasting); `cv2.putText` asserts on non-uint8 depth.

## Running Phase 1

```bash
cd ~/LUNAV-SADO
.venv/bin/python -m lunav_sado probe                  # classify the machine
.venv/bin/python scripts/make_test_clip.py --all --seconds 5 --size 1280x720
.venv/bin/python -m lunav_sado compare --input data/raw/01-green-turbid/clip-a.mp4 --scale 960x540
.venv/bin/python -m unittest discover -s tests -v
```

`compare` always prepends the `none` no-op floor. Outputs land in
`data/out/<class>/<clip>/<pipeline>.{csv,mp4}` — CSV = speed, side-by-side mp4 = the eye.
`data/` is gitignored; clips are bulky and the repo is not a media store.

## Honesty rules specific to this project

- **The generated clips are SYNTHETIC smoke-test data.** They must never be used to choose a
  pipeline. Real water does things no procedural model does.
- **Never quote a Mac latency as a deployment number.** M1 has no CUDA; Docker Desktop on
  macOS has no GPU passthrough. Phase 1 on the Mac buys correctness + a CPU baseline only.
- The roadmap's `<10 ms @ 1080p` is a property of the TARGET CARD. It is a **Phase 2**
  criterion; the founder chose correctness-only for Phase 1 on the Mac.
- At 60 FPS the frame period is ~16.7 ms and encode + transport dominate. **Benchmark the
  stream path with enhancement disabled BEFORE optimising pixels.**
- Pipeline A's known failure mode is over-correction (grey/sepia water); C's is AWB
  neutralising a genuine colour the operator is inspecting. Both are captured in the
  pipelines' own docstrings — cite them rather than rediscovering.

## Hardware facts that shape the port

- Three office PCs: **one NVIDIA, two Radeon** — which is which was unconfirmed last check;
  `python -m lunav_sado probe` on the box settles it.
- **"9070 Nvidia" does not exist** — it is an AMD Radeon RX 9070 (RDNA4, `gfx1201`, 16 GB).
  No CUDA/cuDNN/TensorRT; ROCm (Linux) or DirectML (Windows). OpenCV `WITH_CUDA` will not build.
- Owned Jetson Nano B01 (Maxwell, CUDA 10.2, ~0.47 TFLOPS) cannot meet the budget — learning
  only. An Orin board would be the real edge target.
- Access gap: the GPU PC is key-only SSH with no key on the Mac. Phase 2 is blocked on a
  one-time key install or `tailscale up --ssh` on the box. Phase 1 needs none of it.

## References

- `docs/PIPELINE.md` — stage contracts and the CSV schema (build against this)
- `docs/BACKENDS.md` — CUDA image/flags, ROCm vs DirectML, Jetson limits
- `docs/DATASET.md` — the four environmental classes and the operator acceptance criteria
