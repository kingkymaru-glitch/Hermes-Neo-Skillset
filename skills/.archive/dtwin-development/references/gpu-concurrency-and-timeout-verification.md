# GPU concurrency crash + portable timeout — verified transcript (2026-08-15)

Session-specific evidence behind the two production-hardening bullets in SKILL.md.
The founder asked to "optimize code/pipeline/memory, test for production-ready".

## Metal GPU concurrency crash (real, reproduced)
Two MLX splat-training jobs on ONE Apple-Silicon Mac, launched concurrently
(dji_test training running, then a pontoon test training started). The second
job's training died at ~118/600 iters:

```
libc++abi: terminating due to uncaught exception of type std::runtime_error:
[METAL] Command buffer execution failed: Impacting Interactivity
(0000000e:kIOGPUCommandBufferCallbackErrorImpactingInteractivity)
tools/pipeline.sh: line 29: 85613 Abort trap: 6  perl -e 'alarm shift; exec @ARGV' ...
multiprocessing.resource_tracker: ... 1 leaked semaphore objects ...
ERROR: training failed/timed out (>1800s)
```

Observations:
- The FIRST job (dji_test) was completely unaffected — isolation held.
- The hardened script detected the abort and exited cleanly (no hang), but the
  crashed job had wasted a full ffmpeg + COLMAP pass. Hence: guard, don't retry.
- The failure is not a timeout — it's an uncaught Metal exception. A timeout
  wrapper reports it as a generic failure, which is why the GPU guard (explicit
  `pgrep -f train_mlx.py`) is the right fix rather than relying on the timeout.

## Portable timeout verification (macOS has no GNU `timeout`)
macOS ships neither `timeout` (coreutils) nor `gtimeout` unless coreutils is
installed (`brew list coreutils` empty here). `timeout: command not found`
aborts a hardened pipeline. The perl alarm-kill fallback:

```bash
perl -e 'alarm shift; exec @ARGV' <secs> <cmd...>
```

Verified live:
- `perl -e 'alarm 2; exec "sleep", "30"'` → died in 2.007s, exit 142 (= SIGALRM). GOOD.
- `perl -e 'alarm 3; exec "sleep", "1"'` → completed (under cap). GOOD.

In the pipeline, pick `gtimeout` → `timeout` → perl fallback, and wrap every
COLMAP stage + training so a hang can't stall the server. Budgets used:
- feature extract: `N*2 + 120` s
- exhaustive match: `N*N*0.12 + 120` s
- mapper: `N*1.5 + 300` s
- training: `iters*2.5 + 300` s

## Also verified this session
- Server pipe-drain ring buffer: `GET /api/pipeline/log` + SSE both read a
  `deque(maxlen=8000)`; a background thread always drains the child stdout so a
  closed tab can't hang the build. Confirm: `curl /api/pipeline/log` returns
  `{"lines":[...],"running":bool}`.
- `RESULT_BASE="results"` (train_mlx writes cwd-relative), images in
  `frames/<d>/images/`, sfm in `frames/<d>/sfm/`, cleanup `rm -rf frames/<d> train/<d>`.
- A successful 300-frame/2000-iter DJI build published a 10.6MB / 156,681-vertex
  `.ply` served HTTP 200; transient frames(1.4G)+train(282M) auto-cleaned.
