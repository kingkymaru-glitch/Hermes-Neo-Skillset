#!/usr/bin/env python3
"""
benchmark_harness.py — baseline → change → re-benchmark loop.

Measures wall-clock latency (median + p95 over N iterations) and peak memory
(peak RSS via tracemalloc or resource) for a target callable. Discarded warm-up
round keeps cold-start (import/JIT/cache) out of the reported numbers.

Usage:
    python scripts/benchmark_harness.py --import-path mypkg.module \\
        --target my_func --iterations 100 --warmup 10 [--arg 1 --arg 2]

Or call the helper directly from a test:
    from benchmark_harness import measure
    stats = measure(lambda: do_work(x, y), iterations=100, warmup=10)
    print(stats)  # {'latency_median_ms':..., 'latency_p95_ms':..., 'peak_mb':...}

Exit code is non-zero if --fail-if-slower-than is set and the new run regressed,
so it can gate CI.
"""
from __future__ import annotations

import argparse
import importlib
import statistics
import time
import tracemalloc
from pathlib import Path


def measure(func, iterations: int = 50, warmup: int = 5) -> dict:
    """Return {latency_median_ms, latency_p95_ms, peak_mb} for func().

    Runs `warmup` discarded iterations, then `iterations` measured ones.
    Peak resident memory is sampled via tracemalloc for the median-mapped call.
    """
    # Warm-up (discard)
    for _ in range(max(0, warmup)):
        func()

    latencies: list[float] = []
    peak_mb = 0.0
    for i in range(iterations):
        tracemalloc.start()
        t0 = time.perf_counter()
        func()
        dt = time.perf_counter() - t0
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        latencies.append(dt * 1000.0)
        peak_mb = max(peak_mb, peak / (1024 * 1024))

    latencies.sort()
    n = len(latencies)
    p95 = latencies[min(n - 1, int(0.95 * n))]
    return {
        "latency_median_ms": round(statistics.median(latencies), 3),
        "latency_p95_ms": round(p95, 3),
        "peak_mb": round(peak_mb, 2),
        "iterations": n,
    }


def _load_target(import_path: str, target: str, args):
    mod = importlib.import_module(import_path)
    fn = getattr(mod, target)

    def _coerce(v: str):
        try:
            return int(v)
        except ValueError:
            pass
        try:
            return float(v)
        except ValueError:
            return v

    pos_args = [_coerce(a) for a in (args.arg or [])]
    return lambda: fn(*pos_args)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Baseline/regression benchmark harness")
    ap.add_argument("--import-path", required=True, help="module to import, e.g. mypkg.compute")
    ap.add_argument("--target", required=True, help="callable name inside the module")
    ap.add_argument("--iterations", type=int, default=50)
    ap.add_argument("--warmup", type=int, default=5)
    ap.add_argument("--arg", action="append", default=[], help="positional arg to target (repeatable)")
    ap.add_argument("--fail-if-slower-than-ms", type=float, default=None,
                    help="exit non-zero if median latency exceeds this (CI gate)")
    args = ap.parse_args(argv)

    func = _load_target(args.import_path, args.target, args)
    stats = measure(func, iterations=args.iterations, warmup=args.warmup)
    print(f"[{args.import_path}.{args.target}]")
    print(f"  median={stats['latency_median_ms']} ms  "
          f"p95={stats['latency_p95_ms']} ms  "
          f"peak={stats['peak_mb']} MB  (n={stats['iterations']})")

    if args.fail_if_slower_than_ms is not None:
        if stats["latency_median_ms"] > args.fail_if_slower_than_ms:
            print(f"  REGRESSION: {stats['latency_median_ms']} ms > "
                  f"{args.fail_if_slower_than_ms} ms threshold")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
