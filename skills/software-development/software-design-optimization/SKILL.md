---
name: software-design-optimization
description: Profile then refactor for low latency and memory efficiency.
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Performance, Profiling, Refactoring, Memory, Latency]
---

# Software Design & Performance Optimization

A systematic framework for making code fast and memory-light without guessing: measure
first, isolate one change at a time, verify correctness with the test suite, then
re-benchmark to quantify the gain. It covers low-latency service design, memory-layout
optimization, and algorithmic refactoring. It does NOT cover GPU/CUDA tuning or
distributed-systems capacity planning — those need skills of their own.

## When to Use

- "this is too slow" / "the service has high p99 latency"
- "memory blows up" / "OOM" / "we should reduce allocations"
- "can we make this O(N²) go away" / "algorithm is too slow at scale"
- "profile this function" / "find the bottleneck" / "why is this hot loop slow"
- "add a benchmark" / "prove the refactor didn't regress" / "make a perf test"
- after identifying a hotspot and before rewriting it

## Prerequisites

No mandatory installs — the framework is mostly a discipline. Optional tools (install only
if you need them, none are required to follow the procedure):

- Python stdlib: `time.perf_counter`, `cProfile`, `tracemalloc`, `timeit`, `mmap`, `memoryview`. No install.
- `line_profiler` — per-line CPU profiling: `pip install line_profiler` (use `kernprof -l -v script.py`).
- `memory_profiler` — per-line memory: `pip install memory-profiler` (use `@profile` + `mprof run`).
- `pytest-benchmark` — automated regression benchmarks in CI: `pip install pytest-benchmark`.
- `hyperfine` — shell/CLI benchmarking: `brew install hyperfine` (macOS) / `apt install hyperfine`.
- Linux `perf`: `perf stat -e cache-misses ./bin` (cache-miss identification).
- `valgrind --tool=cachegrind`: `valgrind --tool=cachegrind ./bin` then `cg_annotate cachegrind.out.*`.

## How to Run

Invoke the profiling and benchmark tools through the `terminal` tool. Read suspect source
with `read_file`/`search_files`; apply isolated changes with `patch`. Run the project's
test suite (`terminal`: `pytest`) after every change to guarantee zero regression. Use the
benchmark harness in `scripts/benchmark_harness.py` for the baseline → change → re-benchmark
loop; invoke it through the `terminal` tool.

## Quick Reference

- Baseline: `python -m cProfile -s cumtime script.py`
- Per-line CPU: `kernprof -l -v script.py`
- Memory growth: `python -m memory_profiler script.py`
- Latency measure: `time.perf_counter()` around the unit of work
- Cache misses (Linux): `perf stat -e cache-misses,cache-references ./bin`
- Cachegrind: `valgrind --tool=cachegrind ./bin` → `cg_annotate cachegrind.out.*`
- Automated bench (Python): `pytest --benchmark-only`
- CLI bench: `hyperfine 'cmd old' 'cmd new'`
- Zero-copy: `mmap`, `os.sendfile`, `memoryview`, `bytearray` slicing

## Procedure

1. **Establish a baseline.** Benchmark current time + peak memory BEFORE touching code.
   Use the harness (`scripts/benchmark_harness.py`) or `cProfile`:
   `python -m cProfile -s cumtime script.py`. Record the numbers — you cannot claim a win
   you did not measure.
2. **Locate the bottleneck precisely.** Identify the hot path with data, not intuition:
   - CPU-bound loop → `line_profiler` shows the exact expensive line.
   - Memory growth → `tracemalloc` / `memory_profiler` shows the allocating line.
   - Suspected cache misses → `perf stat -e cache-misses` (Linux) or `cachegrind`.
   - Lock contention / stalls → profile wall-clock vs CPU time; if wall ≫ CPU, you are
     blocking (I/O, locks, GC), not computing.
3. **Compute complexity.** State the Big-O of the hot path. Flag O(N²) / O(2^N) steps that
   become O(N log N) or O(N) with a better structure or algorithm (e.g. replace nested
   scan with a hash map, sort+merge instead of pairwise compare).
4. **Isolate ONE change.** Apply a single refactoring at a time so the measured delta is
   attributable:
   - Algorithm swap (dict/set for O(1) lookup, radix/trie for prefix, ring buffer for
     rolling windows).
   - Memory layout: structure-of-arrays over array-of-structures for tight loops; pack
     contiguous arrays (numpy/`array`/`memoryview`) to improve spatial locality and cut
     cache misses.
   - Allocation reduction: object pooling for high-frequency objects, flyweight for shared
     state, reuse buffers instead of per-iteration `allocate+copy`.
   - I/O: zero-copy paths — `mmap` for file access, `os.sendfile` for file copy,
     `memoryview`/`bytearray` slicing to avoid duplicate copies in stream processing.
   - Concurrency: worker/thread pools, non-blocking async I/O, or lock-free / actor-model
     structures where a mutex is the contention point. (Only if step 2 showed wall ≫ CPU.)
5. **Verify correctness.** Run the full test suite (`terminal`: `pytest`). A faster wrong
   answer is a regression. Do NOT skip this step.
6. **Re-benchmark.** Re-run the harness from step 1 on the same inputs. Report the delta
   (latency ↓ X%, memory ↓ Y%, cache-misses ↓ Z%). If no improvement, revert — the data
   said it wouldn't help.

## Pitfalls

- **Optimizing before measuring.** Intuition about "the slow part" is wrong most of the
  time; always profile first.
- **Micro-optimizing cold paths.** A 10x speedup on a function that takes 0.1% of runtime
  is invisible. Spend effort on the hot 1%.
- **Premature structure-of-arrays.** SoA helps tight numeric loops; it hurts readability
  and hurts when access is random. Match layout to access pattern.
- **Tuning GC / allocations blindly.** Pooling adds lifetime complexity and leaks if
  objects are stateful — only pool truly ephemeral, stateless, high-churn objects.
- **Cachegrind counts are simulated.** `cachegrind` models an idealized cache; absolute
  miss numbers are relative, not real hardware figures. Use it for before/after delta, not
  absolute truth.
- **`perf` cache-miss events need Linux + perf_events.** macOS has no `perf`; use
  `cachegrind` or `xcrun xctrace` instead.
- **Benchmarking a warmed-up only run.** First calls include import/JIT/cold-cache cost;
  the harness discards a warm-up round and reports median/p95 over many iterations.
- **Regression in tests while "faster".** Never ship a perf win that breaks `pytest`.

## Verification

Run the project test suite and the benchmark harness on the same input before and after:

```
pytest -q
python scripts/benchmark_harness.py
```

A valid optimization shows: (a) `pytest` green, and (b) harness output where latency and/or
peak memory decreased with no correctness change. If either fails, the change is not done.
